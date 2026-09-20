# Waiting-request policy design

POLICY-001, 2026-09-20. This is a design contract, not an implementation.
The pinned scheduler remains unchanged. The future policy boundary is the
choice of the next candidate from `Scheduler.waiting` during prefill. It does
not own admission, feasibility, running/decode order, KV blocks, model calls,
sampling, stopping, or preemption.

## Current behavior and exact baseline

`nanovllm/engine/scheduler.py` keeps `waiting` and `running` as deques.
`add()` appends fresh requests to the waiting tail. `schedule()` attempts
prefill before decode. While there is a waiting request and sequence budget,
it reads `waiting[0]`, computes remaining token budget, checks
`BlockManager.can_allocate()` for a request without blocks, and **breaks** if
allocation fails. It also breaks when a non-first candidate would require a
chunked prefill. Only the first selected request in a batch may be chunked.
It allocates blocks when necessary, sets `num_scheduled_tokens`, and, after a
final prefill chunk, removes the waiting **head** with `popleft()` and appends
the same `Sequence` to the running tail. An incomplete chunk stays in waiting
with its block table. If any prefill work was selected, it returns that batch
without decode. Otherwise the existing running/decode loop executes.

`preempt()` deallocates a running request and prepends that same sequence to
waiting. Thus baseline is head-of-deque selection, including upstream
`appendleft` preemption and partial-prefill continuation, not unconditional
original-arrival FIFO. The future `baseline` option must use the same head
read, feasibility checks, `popleft()`, prefill-first return and decode path.
Default configuration must cause no change to existing callers or results.

## Proposed interface and placement

Add a small CPU-only selector, conceptually:

```python
def choose_waiting_index(waiting, policy, *, now_ns=None, aging_state=None) -> int:
    """Return one current deque index; inspect only causal scheduler data.

    Preconditions: waiting is nonempty; policy is a validated name.
    No queue mutation, block-manager calls, telemetry reads, or GPU work.
    """
```

The selector returns an index, not a reordered deque or a `Sequence` copy.
The scheduler remains the sole owner of queue mutation and all resource
checks. `Scheduler.schedule()` calls it at the current `seq = waiting[0]`
site, after confirming there is a token budget; it then applies the existing
prefill logic to `waiting[index]`. A selected candidate is removed **only
after** its final prefill chunk is successfully scheduled. Use `popleft()`
for index zero and `del waiting[index]` for a non-head candidate. An incomplete
chunk stays at its current position with its existing blocks. No item is
removed for a failed allocation or budget check. The selector must not be
invoked to find an alternative after either failure. The single coordinator
thread owns this deque, so the returned index remains valid until the
scheduler's own removal; an implementation should assert this ownership.

Pseudocode for the intended insertion is:

```python
while waiting and len(scheduled) < max_num_seqs:
    remaining = max_num_batched_tokens - num_batched_tokens
    if remaining == 0:
        break
    index = 0 if policy == "baseline" else choose_waiting_index(waiting, policy, ...)
    seq = waiting[index]
    # Existing can_allocate / cached-token / chunk-budget checks, unchanged.
    if selected_candidate_fails_existing_check:
        break                         # no scan for a feasible alternative
    # Existing allocate and num_scheduled_tokens calculation, unchanged.
    if prefill_chunk_is_final:
        seq.status = RUNNING
        if index == 0: waiting.popleft()
        else: del waiting[index]
        running.append(seq)
    scheduled.append(seq)             # partial chunk remains in waiting
# Existing prefill return and running/decode loop, unchanged.
```

The pseudo-condition above stands for the two existing break conditions;
it is not a proposed new feasibility predicate. Preserve their exact order
and behavior when implementing. In particular, do not use prefix-cache
hits, free blocks or predicted service time to pick a different candidate.
Selecting a different request can indirectly change when it enters running,
but no policy may reorder requests already in `running`, edit the decode
loop, or change `preempt()`'s `appendleft` rule.

## Policy rules and ties

The conceptual configuration field is `scheduling_policy`, accepted values
exactly `baseline`, `short_prompt`, `aged_short_prompt`, default `baseline`.
Validate it during `Config` construction and fail clearly on any other value.
No configuration field or runtime branch is added in POLICY-001. In a future
implementation, `LLMEngine.__init__` already passes recognized `Config`
fields into `Config`, and `Scheduler.__init__` can read the validated name.
Keep the baseline fast path as index zero with no priority scan or clock read.

For `short_prompt`, scan **all currently waiting** entries and choose the
smallest immutable `seq.num_prompt_tokens` (defined on `Sequence` creation).
Do not use `seq.num_tokens`, `len(seq)`, `num_cached_tokens`, output count,
output cap, sampled tokens, trace class label, future arrivals or completion
times as a priority key. This rule also applies to a waiting partial-prefill
or preempted sequence: its **original prompt length** remains the key, even
though it may own blocks or contain generated tokens. This explicit choice
keeps the rule unambiguous; tests must check that finite workloads progress
when such requests coexist with fresh arrivals. A later aging policy may
address excessive waiting, but this task chooses no aging formula.

Resolve equal priority by the **current deque order**, scanning left to
right and updating the best candidate only on a strictly smaller key. For
fresh requests this preserves producer release/admission order, including
same-arrival trace ties. A preempted request is at the front because upstream
put it there; a partial-prefill request retains its position. Do not sort by
request ID, engine sequence ID, planned arrival, or an unstable sort key.
Successful non-head removal leaves every other deque element in its previous
relative order. A repeated decision can choose the same incomplete-prefill
sequence in a later step, never twice within a single batch beyond the
existing first-only chunking/budget rule.

## Resource checks and complexity

Candidate choice expresses priority, not feasibility. After selection,
`can_allocate`, cached-block accounting, the remaining-token check, block
allocation and first-only chunking remain authoritative. If the selected
candidate cannot allocate, the prefill loop breaks exactly as it does for
baseline's head. If it cannot fit as a non-first chunk, the loop breaks.
Neither case triggers a scan for another feasible request. Such backfilling
would be a separate scheduling algorithm and is excluded from this design.
The existing prefill-before-decode boundary and preemption behavior remain.

With `n` waiting requests, baseline selection and head removal are O(1).
`short_prompt` needs one O(n) scan and, for a successful non-head final
chunk, O(n) deque deletion; auxiliary memory is O(1). Repeating selection
for up to `b` batch candidates costs O(bn) in the worst case, acceptable for
the frozen 60-request workload and current `max_num_seqs=1`. Globally sorting
the deque would cost O(n log n), mutate all relative positions, complicate
partial/preempted identities, and still need reordering on arrivals; it is
unnecessary for choosing one candidate. Future `aged_short_prompt` can also
scan O(n) using a causal score, with O(n) scheduler-owned timing metadata.
Its exact score and tie rule require their own specification before coding.

## State needed by a later aging policy

`Sequence` has original prompt length but no arrival/wait timestamps. The
future scheduler should own per-sequence timing state keyed by `seq_id`,
created at admission regardless of whether telemetry is enabled. At minimum
it needs a monotonic admission timestamp and a waiting-episode start, plus
an explicit choice of whether to accumulate waiting across partial prefill
and preemption. Sample the same monotonic clock domain for all scheduler
decisions; pass an injectable clock into CPU tests. Clear state on successful
completion. Define whether preemption retains age, how partial-prefill service
pauses waiting age, the score/threshold and stable ties in that later task.
Do not infer these from telemetry events: telemetry is optional measurement
infrastructure and may be disabled. Keeping timing in `Scheduler` also avoids
changing `Sequence.__getstate__/__setstate__`, the model-runner IPC contract.

## Invariants and implementation test plan

- Exactly one current waiting `Sequence` is selected per candidate decision;
  no copy, duplicate admission or lost request. A selected final-prefill
  request leaves waiting once and enters running once; a partial request stays
  waiting until its final chunk. Preserve `seq_id` and external request ID.
- Baseline with default/explicit `baseline` matches the current scheduler's
  selected sequence IDs, queue contents/order, prefill/decode flag, token
  counts, block ownership, preemption outcomes and generated results. No
  policy clock or priority scan runs on this path.
- Equal-length fresh arrivals retain waiting/arrival order. Preemption's
  front insertion and partial-prefill position remain observable in ties.
  Non-head deletion preserves the relative order of all other entries.
- Running queue operations, decode, allocation, cache, model calls, sampling,
  stopping, telemetry hooks and preemption are unchanged. Failure of the
  chosen candidate does not skip to another waiting request.
- Policy decisions use only state known by that decision. Never read future
  output length, future arrival contents, final telemetry or other policies'
  results. Changing output cap or observed/generated history without changing
  original prompt length must not change `short_prompt` priority.

For the implementation task, put the pure selector in a small module such as
`nanovllm/engine/waiting_policy.py`, add the validated default field in
`nanovllm/config.py`, and make only the selection/removal insertion in
`nanovllm/engine/scheduler.py`. `nanovllm/engine/llm_engine.py` should need no
change because it already filters/passes `Config` fields. Do not edit
`Sequence` or `BlockManager` to implement `short_prompt`.

CPU tests should first compare the default and explicit baseline against the
current scheduler over fresh admission, prefix-cache hits, partial chunks,
allocation failure, decode and forced preemption, with telemetry both on and
off. Test three-way prompt lengths and equal-length arrivals, non-head final
removal, partial retention, preempted original prompt length, failed selected
allocation with no fallback, non-first chunk budget stop, invalid config and
no-future-information priority. Assert selected IDs, deque membership/order,
block references and exactly-once completion, not merely a sorted key list.
Then run the existing CPU suite and conservative baseline GPU regression
before any policy GPU validation; keep all formal calibration artifacts and
their trace hashes unchanged. POLICY-001 itself runs no such experiment.
