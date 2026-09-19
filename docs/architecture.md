# nano-vLLM architecture: request lifecycle and scheduling

ARCH-001, inspected 2026-09-19. This document describes local source at project
HEAD `bb3785a312ee2adfdd9227fd0fbef1bf02690c9f`, based on upstream
`bb823b3e06983d71485a8e1f23715ebd87d98ef8` (recorded in
`artifacts/environment/upstream-commit.txt`). Source references below use
repository-relative paths and one-based line regions at this revision.
This is source analysis, not a benchmark or a policy implementation.

## 1. Component overview

| Component | Implementation and source region | Responsibility |
| --- | --- | --- |
| Public API | `nanovllm/llm.py:1-5`, `LLM` | Inherits `LLMEngine` without overriding behavior. |
| Engine | `nanovllm/engine/llm_engine.py:15-90`, `LLMEngine` | Initializes execution/tokenizer/scheduler; admits prompts; drives schedule, GPU execution and postprocessing; returns completed results. |
| Request | `nanovllm/engine/sequence.py:8-70`, `SequenceStatus`, `Sequence` | Holds identity, tokens, fixed prompt length, status, cache counters, block table and sampling parameters. |
| Queues and scheduler | `nanovllm/engine/scheduler.py:8-92`, `Scheduler` | Owns waiting/running deques, selects prefill or decode, preempts, updates tokens and completes requests. |
| Logical KV blocks | `nanovllm/engine/block_manager.py:8-120`, `Block`, `BlockManager` | Tracks free/used blocks, reference counts, prefix hashes and per-request block tables. |
| GPU execution | `nanovllm/engine/model_runner.py:17-39,103-220`, `ModelRunner` | Loads the model, allocates physical KV storage, prepares GPU inputs, runs forward/sampling and returns token IDs. |
| Attention/cache writes | `nanovllm/layers/attention.py:10-75`, `store_kvcache`, `Attention.forward` | Writes K/V by slot mapping; selects prefill or cached-decode FlashAttention. |
| Execution metadata | `nanovllm/utils/context.py:5-27`, `Context`, `set_context`, `reset_context` | Carries batch phase, lengths, slots and block tables into model layers. |
| Logits | `nanovllm/layers/embed_head.py:45-66`, `ParallelLMHead.forward` | Uses the last query position of each prefill chunk, or the decode position, for output logits. |

Engine initialization constructs `ModelRunner` before `Scheduler`; runner warmup
and physical KV allocation therefore precede user admission
(`llm_engine.py:17-35`; `model_runner.py:91-121`). Warmup creates its own
`Sequence` objects; sequence IDs are not a user-request count.

## 2. Request lifecycle

```text
prompt string / token IDs
        |
LLM.generate -> LLMEngine.add_request -> Sequence(WAITING)
        |                                  |
        +--------------------------> waiting.append
                                           |
                                   Scheduler.schedule
                                           |
                              choose waiting head / KV blocks
                                           |
                  +------------------------+--------------------+
                  | partial prefill chunk                       | final chunk
                  | keep WAITING                                | set RUNNING;
                  |                                             | move to running
                  +------------------------+--------------------+
                                           |
                              ModelRunner.run(..., prefill=True)
                                           |
                                  Scheduler.postprocess
                         +-----------------+--------------------+
                         | incomplete prefix                    | full prefix
                         | update cached count only              | append first
                         | retain waiting head                   | generated token
                         +--> later prefill step                 v
                                                     finish? -- yes --> FINISHED
                                                        |               free blocks
                                                        no              remove running
                                                        |
                     (only when no prefill batch was selected)
                                                        |
                                     schedule decode from running front
                                      +------+------------------+
                                      |                         |
                               insufficient blocks              can append
                               preempt -> WAITING               one input token
                               free blocks; prepend             GPU decode
                               recompute on prefill             append output
                                                               finish or repeat
```

1. `generate` submits all prompts before its step loop; it is not timed arrival
   replay (`llm_engine.py:60-75`). `add_request` tokenizes a string with
   `tokenizer.encode`; a supplied token-ID list bypasses encoding (43-47).
2. `Sequence.__init__` copies token IDs, creates `seq_id`, sets WAITING, and
   stores both `num_tokens` and **`num_prompt_tokens = len(token_ids)`**
   (`sequence.py:18-31`). Prompt count is known before `Scheduler.add` appends
   the sequence to waiting. It measures the actual supplied/encoded prompt,
   including any chat formatting already applied by the caller.
3. `LLMEngine.step` obtains `(seqs, is_prefill)`, calls
   `ModelRunner.run`, then `Scheduler.postprocess` (`llm_engine.py:49-55`).
   Partial prefill remains waiting. Selection of the final prefill chunk moves
   the request to running **before GPU execution**, not after execution
   (`scheduler.py:48-51`).
4. Postprocessing hashes completed KV blocks, increments `num_cached_tokens`
   by `num_scheduled_tokens`, then resets the scheduled count. An incomplete
   prefill chunk stops here and discards its sampled token. A complete prefill
   appends the first generated token (`scheduler.py:81-88`).
5. Subsequent decode steps consume the last token and append one newly sampled
   token per selected sequence. `Sequence.append_token` updates `token_ids`,
   `last_token` and `num_tokens`; `num_prompt_tokens` stays fixed
   (`sequence.py:43-53,67-70`). Completion length is their difference.
6. After an append, EOS (unless `ignore_eos`) or equality with `max_tokens`
   marks FINISHED, deallocates logical KV blocks and removes the sequence from
   running (`scheduler.py:89-92`). A request can finish after prefill without
   any decode step. `step` returns only finished requests; `generate` collects
   them by ID, sorts IDs and decodes their completion tokens
   (`llm_engine.py:54-55,84-90`). Return order is submission-ID order rather
   than completion order. There is no token-streaming return here.
7. Scheduler completion means both queues are empty (`scheduler.py:19-20`).
   Engine shutdown is separate from per-request cleanup:
   `LLMEngine.exit` calls runner shutdown and joins workers (37-41);
   `ModelRunner.exit` handles shared-memory/graph cleanup when applicable,
   synchronizes CUDA and destroys the process group (50-59).

## 3. Scheduler lifecycle

`Scheduler.schedule` (`scheduler.py:25-73`) first attempts prefill:

- Inspect `waiting[0]`, bounded by the selected batch's `max_num_seqs` and
  remaining `max_num_batched_tokens` (30-34).
- For a request without a block table, call `can_allocate`; failure breaks the
  waiting loop rather than skipping to another request (35-39).
- Determine remaining prefix work from prefix-cache hits, or from the current
  `num_cached_tokens` if blocks are already assigned (39-41).
- Only the first sequence in a batch may have a truncated prefill chunk.
  If another candidate cannot fit, stop (42-43). Allocate blocks when needed,
  set the scheduled token count, and move a final-chunk candidate to running
  (44-52).
- Return `(scheduled_seqs, True)` as soon as the prefill selection loop has
  produced any work (54-55). No decode is added to that batch.

Only if no prefill work was selected does it attempt decode (58-73). It pops
running requests from the front and checks `can_append`. Under pressure it
preempts requests from the running tail; if none remain, it preempts the
candidate itself (59-65). Each successful decode candidate schedules one input
token, sets `seq.is_prefill=False`, and obtains an additional block if needed
(67-70). Selected requests are restored to the front in the same order with
`extendleft(reversed(scheduled_seqs))` (72). There is no round-robin rotation
of this selected prefix. The function asserts that a decode batch is nonempty
(71); source inspection does not establish progress for arbitrary invalid or
infeasible configurations.

## 4. Waiting/running queue behavior

Both queues are `collections.deque[Sequence]` (`scheduler.py:1,16-17`).
Fresh arrivals use `waiting.append` (22-23), so fresh requests enter in FIFO
order. Selection reads the head, partial prefill retains its position, and
preemption uses `waiting.appendleft` (75-79). The complete behavior is therefore
FIFO admission with continuation/preemption effects, not unconditional FIFO.

A waiting request may already own blocks after a partial prefill. A preempted
request may already contain generated tokens. `preempt` resets its status and
phase, deallocates its blocks and prepends it, but retains identity, token
history and sampling settings. On rescheduling, prefill covers the current
history (original prompt plus generated tokens), potentially reusing cached
prefix blocks (`scheduler.py:35-46,75-79`; `block_manager.py:94-101`).

Running receives final-prefill selections at its tail (48-51); completion
removes the exact sequence (92). The per-batch `max_num_seqs` check does not
subtract the number of resident running requests: it is not a total-resident
running-queue cap (30,58).

**Can waiting be reordered independently?** Structurally yes: waiting and
running are separate containers, so a waiting-only order change need not
mutate running order or its entries. It still changes when decode gets GPU
time, block availability, cache reuse and potentially subsequent preemption.
It is not performance-independent, and treating every waiting entry as a
fresh request would ignore partially served and preempted requests.

## 5. Prefill vs decode behavior

The Boolean returned by `schedule` chooses the batch execution path in
`ModelRunner.run` (`scheduler.py:54-55,73`; `model_runner.py:214-220`). This is
distinct from `Sequence.status` and its `is_prefill` field: a final-prefill
selection is already RUNNING while this batch is still prefill, and the
sequence flag is set false only on decode selection (48-51,68).

| Phase | Prepared inputs | Attention and output |
| --- | --- | --- |
| Prefill | Token slice `[num_cached_tokens : num_cached_tokens + num_scheduled_tokens]`, positions, cumulative query/key lengths, slot mappings and optional prefix block table (`model_runner.py:129-170`). | `flash_attn_varlen_func`; cached K/V are used when a prefix block table exists (`attention.py:64-70`). Last query position per sequence provides logits (`embed_head.py:56-61`). An intermediate chunk's sampled token is discarded by postprocessing. |
| Decode | One `last_token` per request, position `len(seq)-1`, full context length, last-token slot and block table (`model_runner.py:172-188`). | `flash_attn_with_kvcache` (`attention.py:71-75`); sampling returns the next token. The last appended token is the input whose KV is computed on this step. |

Both paths write new K/V through `store_kvcache` when the cache exists
(`attention.py:10-40,59-63`). `run_model` executes directly for prefill, eager
mode or more than 512 input tokens; other decode batches use captured CUDA
graphs (`model_runner.py:195-212`). `run` prepares temperatures, executes the
model, samples token IDs and resets context (190-193,214-220). Waiting-order
policies do not need to change these paths.

## 6. KV-cache interaction

There are two allocation levels:

- **Physical GPU pool:** `ModelRunner.allocate_kv_cache`
  (`model_runner.py:103-121`) derives block count from CUDA memory statistics,
  memory-utilization configuration, layer/head geometry and dtype. It creates
  a tensor shaped `(2, layers, blocks, block_size, kv_heads, head_dim)` and
  assigns layer cache views. The scheduler subsequently creates a logical
  `BlockManager` for that count (`llm_engine.py:31-34`; `scheduler.py:15`).
- **Logical request ownership:** `BlockManager` keeps a free-ID deque, used-ID
  set, hash map and reference-counted blocks (`block_manager.py:8-33`).
  `can_allocate` checks a hash-and-token-matched prefix, excluding the last
  logical block, and verifies free capacity (58-73). `allocate` shares live
  prefix blocks by incrementing references, reclaims free cached blocks, then
  allocates remaining blocks and sets the cached-token count (75-92).

Initial allocation reserves blocks for the sequence's entire current token
history (`Sequence.num_blocks`, `sequence.py:55-57`), even if the scheduled
prefill chunk is smaller. It is not allocation for only that chunk.
`can_append`/`may_append` require and allocate one new block when
`len(seq) % block_size == 1` (`block_manager.py:103-108`): the newly appended
last token has crossed into the next block and will be consumed by decode.

`hash_blocks` publishes newly completed full blocks using chained prefix
hashes (110-120); postprocessing calls it before advancing the cached count
(`scheduler.py:83-85`). `deallocate` decrements references, returns zero-ref
blocks to the free deque, resets cached count and clears the sequence's block
table (`block_manager.py:94-101`). Both preemption and completion invoke it.
This releases logical ownership, not the physical GPU tensor. Free blocks
retain cache metadata/data for possible reuse until reassignment;
`_allocate_block` removes the prior matching hash entry and resets metadata
(43-56). Shared blocks remain used while another request holds a reference.

## 7. Candidate policy insertion point

The smallest conceptual insertion point is waiting-order selection in
`Scheduler.schedule`, immediately before the prefill loop consumes
`waiting[0]` (`scheduler.py:29-31`). A future policy could determine eligible
waiting order before this loop, leaving allocation checks, chunk accounting,
running/decode handling, postprocessing and GPU execution in their existing
locations. This is a proposed design boundary, not an implemented policy.

For `short_prompt`, the available length is `seq.num_prompt_tokens`
(`sequence.py:24`), known on admission. `len(seq)`/`num_tokens` include generated
tokens after service, and remaining prefill work can include recomputation;
neither is the original prompt length. Future output length must not enter
priority decisions. A configured output cap is not an observed output length
and is not a proposed priority input either.

A later policy specification must define stable ties and eligibility for
partially prefilling and preempted requests. One conservative candidate is to
rank only fresh, never-served waiting requests while preserving continuation
and preemption positions; eligibility metadata and exact behavior need their
own task. Blindly sorting the entire deque at every step is not justified by
this analysis. The `baseline` path must retain the existing order exactly,
including `appendleft` preemption and head-of-line allocation failure.

The current `Sequence` and `Scheduler.add` have no arrival-time or wait-time
fields (`sequence.py:18-31`; `scheduler.py:22-23`). `aged_short_prompt` therefore
needs explicitly defined timing metadata and aging semantics in a later task.
Keep pure priority decisions separate from CUDA execution where practical.

## 8. Risks/invariants that future scheduler changes must preserve

- **Baseline equivalence:** preserve queue operations, prefill-first batch
  selection, head-of-line allocation failure and the running-prefix decode
  order (`scheduler.py:22-79`). Skipping an infeasible head would introduce
  backfilling, a separate behavior change.
- **Chunk continuation and progress:** a partially prefilling waiting request
  already reserves blocks. Reordering it behind blocked requests can change
  progress; preserve or explicitly specify its treatment. Keep the first-only
  chunking rule and token/sequence batch limits (30-52).
- **State transitions:** final-prefill selection sets RUNNING before execution;
  incomplete chunks do not append outputs. Keep phase/status distinctions and
  exactly one valid completion-token append per completed prefill/decode step
  (48-51,67-68,81-92).
- **Cache integrity:** preserve reference counts, prefix validation, block-table
  ownership, slot mapping, full-block hashing order and append boundaries
  (`block_manager.py:43-120`; `model_runner.py:129-188`). Queue changes must not
  duplicate requests, lose references or release another request's blocks.
- **Preemption identity:** retain accumulated tokens, original prompt length
  and request identity on resumption. A preempted request is not a new arrival
  (`scheduler.py:75-79`; `sequence.py:18-31,67-70`).
- **Stopping and cleanup:** preserve EOS/ignore-EOS and output-cap semantics,
  removal from running and block release (`scheduler.py:88-92`). Do not infer
  general input validation: sequence construction indexes the last input token
  (`sequence.py:22`), so an empty token list is not supported by that path.
- **Causal policy inputs:** use known prompt/admission/wait information only.
  Define ties, starvation protection and the handling of recomputation before
  claiming a policy is fully specified. Scheduling changes may alter sampling
  order and thus stochastic outputs; identity and length metadata must remain
  attributable to the correct request.
- **Telemetry boundaries:** existing `generate` admits everything before its
  loop and returns finished outputs; it does not supply arrival replay or
  per-token timestamps (`llm_engine.py:69-90`). `step` exposes a signed work
  count (prefill input tokens versus negative decode sequence count), not TTFT
  or ITL (49-55). Future telemetry must distinguish admission, selection, GPU
  execution and host-visible sampled tokens; sequence IDs include warmup
  sequences (`model_runner.py:91-101`).

Recommended next task: specify trace/admission replay and request/token
telemetry contracts, including stable external request IDs, timing boundaries,
waiting eligibility and baseline-preservation checks. Define CPU-testable
interfaces before implementing policies or conducting formal GPU experiments.
