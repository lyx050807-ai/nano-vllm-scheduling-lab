# Aging-aware short-prompt policy design

AGING-001, 2026-09-21. This is a design contract for `aged_short_prompt`;
it changes no scheduler behavior. The frozen `formal-mixed-v1` workload and
comparison protocol remain unchanged.

## Starvation problem and scope

`short_prompt` always selects the currently waiting request with the smallest
original prompt length. If shorter requests continue to arrive, an older long
request can repeatedly lose selection even when it is runnable. This is
**priority starvation**: feasible work loses to higher-priority work at
successive candidate decisions. Aging addresses that selection risk.

Priority starvation differs from **resource infeasibility**. The selected
request may fail `BlockManager.can_allocate`, the remaining token budget, or
the existing first-only chunked-prefill rule. The scheduler then breaks; an
aging score does not make the request feasible and must not trigger backfill.
It also differs from **preemption/requeue**: the decode loop can deallocate a
running sequence and `appendleft` that same sequence to `waiting`. Preemption
may repeat independently of waiting priority. Aging does not change that
mechanism or guarantee completion under unlimited preemption.

## Score, units and parameter

For waiting request `i`, at a candidate decision made at monotonic time
`now_ns`, use:

```text
age_seconds_i = max(0, now_ns - first_enqueue_ns_i) / 1_000_000_000
aging_rate = 320 tokens/second
score_i = num_prompt_tokens_i - aging_rate * age_seconds_i
choose the waiting entry with the smallest score_i
```

`num_prompt_tokens` is the immutable original prompt count, in tokens;
`age_seconds` is request age since its first entry into the scheduler waiting
deque, in seconds; `aging_rate = 320` tokens/second; and `score` is
token-equivalent priority.
If a request later runs and is preempted, `age_seconds` includes the time it
spent running. It is not pure accumulated queue-wait time and is **not** the
telemetry `queue_wait_ms` metric. No generated/output length, predicted service
time, future arrival, future token, or trace class label enters the score.

The frozen classes are 32, 96 and 192 prompt tokens. A long request must
erase a 192 - 32 = 160-token gap to tie a *newly enqueued* short request
after 0.5 seconds. Therefore `aging_rate = 160 / 0.5 = 320` tokens/second.
For otherwise newly enqueued competitors, the parity gaps are:

| Older request vs new request | Prompt gap | Age difference at parity |
| --- | ---: | ---: |
| Medium 96 vs short 32 | 64 tokens | 0.2 s |
| Long 192 vs medium 96 | 96 tokens | 0.3 s |
| Long 192 vs short 32 | 160 tokens | 0.5 s |

At exact parity, current deque order decides; strict priority reversal occurs
after the listed age difference. More generally, the pairwise score difference
depends on their **first-enqueue-time difference**, not on absolute wall time:
both scores fall at the same rate while both requests exist. Aging therefore
does not reverse the order of two requests already waiting together. It
limits the priority of *later arrivals* relative to an older request.

This rate is a predeclared, interpretable candidate, not an estimate of an
optimal rate. The baseline-only calibration completed all 60 requests for
each of three frozen seeds. Each seed had 40/60 initial queue waits at least
20 ms; the maximum initial waits were 226, 442 and 459 ms (rounded). The
frozen trace has groups every 0.25 s. Thus a 0.5 s crossover spans two arrival
groups and is much longer than ordinary baseline waits, while remaining near
the observed baseline tail. Calibration only establishes capacity/contention;
it provides no `short_prompt` or aged-policy performance evidence and is not
used to tune this constant after observing policy outcomes. Any later change
to the rate is a new policy version and must be recorded separately from the
frozen comparison.

## Age origin and requeue behavior

Two plausible clocks have different meanings:

1. **Since first entry into `Scheduler.waiting` (chosen).** Capture one
   timestamp at the first `Scheduler.add()` enqueue. Keep it through partial
   prefill, running/decode, and any `preempt()` / `appendleft` requeue. A
   preempted request retains its age; no new first-enqueue timestamp is
   recorded. This prevents repeated preemptions from resetting priority, but
   running time also improves its later score.
2. **Since the current entry into waiting (rejected for this policy).** Reset
   the timestamp on every requeue. This measures the latest waiting episode
   more literally, but a repeatedly preempted request repeatedly loses its
   age and can be passed by new short requests. Preserving only cumulative
   queue time would be a third, more stateful policy, not this contract.

During partial prefill, the existing sequence remains in the waiting deque
with its block table; its first-enqueue timestamp stays intact. The
current baseline and short-prompt paths must never read this timing state.
The age clock starts at first scheduler enqueue, not planned trace arrival or
replay release. It is captured at the first `Scheduler.add()` queue insertion,
which is near engine admission but is defined by the queue lifecycle. These
are distinct boundaries; the existing release-origin latency and
admission-origin initial queue-wait telemetry metrics remain unchanged.

## Scheduler-owned state and selection

The aged policy needs only a `seq_id -> first_enqueue_ns` map owned by `Scheduler`
and a monotonic nanosecond clock such as `time.perf_counter_ns`, injectable in
CPU tests. Record an entry once when `Scheduler.add()` first appends to `waiting`;
retain it on partial prefill and preemption; remove it after normal completion
in `postprocess()`. If a future engine removal/cancellation path is added,
that path must remove the entry too. Lookups for a waiting sequence with no
entry are an invariant violation, never a reason to silently reset its age.
Do not add timing fields to `Sequence` or change its IPC serialization.
Telemetry may record or explain decisions but is optional and must never
provide scheduler age or influence candidate choice.

Sample one `now_ns` per aged-policy candidate decision and scan the current
waiting deque left to right. For the fixed integer rate, compare exact scaled
integer scores `num_prompt_tokens * 1_000_000_000 - 320 * age_ns`; this avoids
floating-point equality artifacts. Use a strict `<` update, so equal scores
retain existing deque order. The clamp on negative age protects an injected
test clock; a production monotonic clock should never precede admission. A
fresh zero-age set ranks exactly like `short_prompt`, including equal-length
ties. Baseline remains index zero with `popleft()` and no clock/scan; the
existing `short_prompt` selector remains original-length-only.

`nanovllm/engine/waiting_policy.py` can hold the pure score/index selector;
`nanovllm/engine/scheduler.py` can own the timestamps, clock and lifecycle;
`nanovllm/config.py` can validate `aged_short_prompt` and the fixed policy
parameter; `scripts/run_replay.py` can expose and record that policy identity
and rate for later GPU/formal runs. The existing final-prefill removal logic
remains the only deque mutation for successful selection: `popleft()` at index
zero, `del waiting[index]` otherwise. Do not sort the deque globally. After
selection, preserve the current allocation, cache, budget and first-only
chunked-prefill checks in their existing order. If the selected candidate
fails a check, break without trying another. Running/decode, KV-cache,
preemption, model execution and sampling remain outside policy scope.

One full scan costs O(n) time and O(1) selector space for `n` waiting
requests. The scheduler's timestamp map costs O(a) space for `a` enqueued,
not-yet-finished requests. Successful non-head deque deletion is O(n), so
one candidate decision/removal is O(n); up to `b` selections per batch cost
O(bn) in the worst case. The frozen configuration has `max_num_seqs=1`.

## What aging can and cannot guarantee

For a waiting 192-token request first enqueued at time `a`, any 32-token request
first enqueued at or after `a + 0.5 s` cannot have a strictly better score at a
later common decision. New 96-token requests lose strict priority after
`a + 0.3 s`. Once the old request reaches those age gaps, later arrivals of
those finite-length classes cannot indefinitely displace it **by priority**.
Under a locally finite arrival process, only finitely many earlier arrivals
can still rank ahead. If each selected request makes finite progress and the
old candidate remains feasible, it will eventually be chosen. Exact-score
ties follow deque order, including the front insertion of a preempted request.

There is no unconditional starvation-freedom claim: an unbounded burst before
the crossover, resource failure, a stuck GPU step, a selected partial prefill
that never finishes, or unlimited decode preemption can prevent selection or
completion. First-enqueue-origin aging may also give a recently preempted request
priority because it spent time running. The fixed 0.5 s threshold is a
priority crossover, not a latency service-level objective or a guarantee of
long-request TTFT/E2E improvement.

## Later validation plan

CPU tests for an implementation should use a fake monotonic clock and real
deque/sequence fixtures where useful:

- At zero age, assert the same 32/96/192 ranking and leftmost equal-length
  ties as `short_prompt`; verify strictly increasing elapsed time never raises
  an individual request's score.
- Assert 96-vs-32 parity at 0.2 s, 192-vs-96 at 0.3 s and 192-vs-32 at 0.5 s;
  test just before, exactly at and just after each threshold with stable
  current-deque-order ties. An old long must outrank a newly enqueued short
  after the last threshold.
- Verify the first-enqueue timestamp is created once, persists through a
  partial prefill and forced preemption/requeue, and is cleared on finish;
  preemption must retain age and the `appendleft` tie behavior.
- Compare default and explicit baseline traces and `short_prompt` traces to
  their existing CPU regressions, including resource failure/no backfill,
  chunking, decode order, KV ownership and exactly-once completion. Toggle
  telemetry on/off and assert identical aged selections and queue states.
- Change output cap, generated token history and future arrivals while
  holding all decision-time prompt lengths/first-enqueue times fixed; decisions
  must not change. Run the full CPU suite before GPU tests.

GPU validation should use the existing pinned model and unchanged 12-request
development trace/configuration for baseline, short_prompt and aged policy in
fresh processes. Require complete/lifecycle-valid runs, no OOM/timeout, and
record selection order, policy/rate/source metadata and logs. This is a
functional regression, not evidence of latency benefit. Only a later,
separately scoped task may run the frozen 45-run formal comparison. That
comparison should report the protocol's long-request initial queue wait,
release-origin TTFT/E2E, and maximum queue wait, plus near-starvation counts
(`queue_wait_ms > 10,000` and requests unselected or unfinished by cutoff).
Show short-request outcomes alongside long-request diagnostics and preserve
failed runs; no tuning from aged-policy results is allowed within this policy
version.
