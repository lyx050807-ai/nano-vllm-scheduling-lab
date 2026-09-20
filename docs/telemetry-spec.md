# Request lifecycle telemetry and metric semantics

TELEMETRY-001, 2026-09-20. Record schema: `request-telemetry-v1`.
This is a specification only. No telemetry hooks, policies or GPU experiments
are implemented by this task. Source context is `docs/architecture.md`,
`docs/trace-spec.md` and the current CPU replay driver.

## 1. Clock definition

Use one coordinator-owned `time.perf_counter_ns()` clock and a single `t0_ns`
per run. Establish t0 after trace/tokenizer validation, pretokenization and any
future engine initialization/warmup, immediately before replay begins. All
future engine hooks in this single-GPU experiment use that same origin; never
reset it per request, engine step, preemption or retry.

Capture integer `event_ns = perf_counter_ns() - t0_ns`. Compute differences in
integer nanoseconds, then convert: seconds = ns / 1,000,000,000; milliseconds =
ns / 1,000,000. Planned arrival comes from the exact trace decimal, converted
to integer microseconds then nanoseconds; it is a target, not a clock reading.
Serialize seconds with up to nine fractional decimal digits and parse them as
decimals during analysis to preserve nanosecond offsets. Finite nonnegative
values only; zero is a valid observed timestamp, distinct from null.

Replay and engine observation must share the same coordinator clock domain.
Do not mix wall time, separate origins, worker clocks or CUDA event durations
into these timestamps. Host observations measure request progress observable
to the coordinator, not exact GPU kernel start/end times. This definition does
not require extra CUDA synchronization at each hook. Wall-clock run dates can
be metadata only. Record clock implementation, resolution, origin convention
and `t0_ns` in the run manifest; monotonic epochs are not comparable across runs.

The existing `scripts/replay_trace.py:81-94` uses exactly one local t0 and
absolute targets. Its current callback receives only the request, not t0 or
the captured release timestamp. A future integration must explicitly share
that context; an independently created engine t0 would be incorrect. Historical
CPU dry-run records cannot supply missing engine timestamps.

## 2. Lifecycle event definitions

| Timestamp | Exact meaning and future capture point |
| --- | --- |
| `planned_arrival_s` | Trace `arrival_s`, unchanged. Eligibility target relative to the common origin, available before runtime starts. |
| `release_s` | Final successful clock check before the replay callback is dispatched; preserve the existing replay driver's captured `now`, not callback return time. Maps from REPLAY-001 `actual_release_s`. |
| `admitted_s` | Sample immediately after the new request is appended to `Scheduler.waiting` in `Scheduler.add`. The request is now owned by the engine and eligible for selection. Admission is not entry into `add_request`, tokenization start or callback start. |
| `first_scheduled_s` | On the first successful `Scheduler.schedule()` return containing the sequence, sample once at the call site before any runner dispatch. Share that batch-selection timestamp among newly selected requests. Record only once, including when the selected work is a partial prefill chunk. A candidate inspected but not returned is not scheduled. |
| `first_prefill_dispatch_s` | Additional internal boundary: sample immediately before the first `ModelRunner.call("run", ..., True)` for this request, after selection. It marks host prefill dispatch, not actual GPU execution start. Never label `first_scheduled_s` as a measured kernel start. |
| `first_token_s` | Timestamp immediately after the first valid `seq.append_token(token_id)` returns in scheduler postprocessing. The generated token has been accepted into this request's completion history and is host-visible. This is token index 1 in `token_times_s`. |
| `finished_s` | Successful request completion after the stopping condition has marked FINISHED, logical KV deallocation has completed and the sequence has been removed from running. Sample immediately after that cleanup. This is before batch-wide result decoding/printing or engine shutdown. |
| `terminal_s` | Normal finish: exactly `finished_s`. Failure: coordinator detection/recording of the failure. Cancellation: coordinator acknowledgement that this request is cancelled (not the initial cancellation signal). Timeout: the declared observation cutoff for unresolved requests. This separate field must not masquerade as successful completion. |
| `observation_end_s` | Run-wide measurement cutoff, shared by all request records. A normal run ends after all traced requests are terminal; a timeout uses the configured cutoff. No event after this boundary contributes to the run's metrics. |

For a completed request, the causal order is planned arrival, release, admission,
first scheduling, first prefill dispatch, first valid token, possible later
tokens, and completion. Timestamps may be equal at clock resolution.

A final-prefill selection sets Sequence status RUNNING before the model call;
that transition is not first-token time. An incomplete prefill chunk stays in
waiting even while selected/executing, and its sampled token is discarded.
Therefore first scheduling can precede both RUNNING status and the first valid
output. Prefill itself can emit the only output token and finish the request;
a decode step is not required. See `scheduler.py:48-55,81-92` via the source
paths in section 8.

The first-token boundary is the lab's host-visible output boundary. It excludes
subsequent detokenization, console formatting, network transport and client
rendering. There is no network service in this project. User-facing metrics
below include all waiting from actual replay release to this defined boundary; they
must not be advertised as measured remote-client latency.

## 3. Event/record schema

Use a request-summary JSONL artifact, one final record per original trace
request, including requests never released before cutoff. This record-oriented
schema stores event timestamps and a per-token time series; a separate generic
event bus is not required. Its location is a new run-specific artifact, separate
from input trace files and REPLAY-001 timing records. UTF-8, LF, one JSON object
per line; reject duplicate keys, NaN/infinity and unsupported versions.

All fields below are required unless explicitly optional. Nullable fields must
remain present as JSON `null`; never omit them or emit sentinel -1/zero.

| Field | Type and contract |
| --- | --- |
| `schema_version` | String, exactly `request-telemetry-v1`. |
| `run_id` | Nonempty unique run identifier; joins immutable run metadata. |
| `request_id` | Original trace ID; unique per run. Never replace it with engine sequence ID. |
| `engine_seq_id` | Nonnegative integer or null before successful admission/mapping. Mapping is stable over preemption. |
| `trace_sha256`, `metadata_sha256` | Lowercase 64-hex hashes of the exact input trace and trace sidecar. |
| `policy` | `baseline`, `short_prompt` or `aged_short_prompt`; run metadata holds parameters. |
| `num_prompt_tokens`, `max_new_tokens` | Positive integers copied from the validated input. |
| `prompt_class` | Trace class, used for analysis grouping only. |
| `status` | `completed`, `failed`, `cancelled` or `timed_out` at finalization. These are observation outcomes, not SequenceStatus enum values. |
| `reason` | `eos`, `max_new_tokens`, `eos_and_max_new_tokens` for completed requests; nonempty error/cancellation/timeout reason otherwise. |
| `planned_arrival_s` | Nonnegative seconds copied exactly from the trace. Always known. |
| `release_s`, `admitted_s`, `first_scheduled_s`, `first_prefill_dispatch_s`, `first_token_s`, `finished_s` | Nonnegative decimal seconds or null, with section 2 capture semantics. |
| `terminal_s` | Nonnegative seconds or null if a crash left termination unobserved. |
| `observation_end_s` | Nonnegative run cutoff in the same domain. |
| `token_times_s` | Ordered array of nonnegative decimal seconds or null entries, one slot per known appended completion token, indexed from 1 conceptually. Empty when none were appended. |
| `observed_output_tokens` | Nonnegative integer, equal to array length; a lower bound on the actual output count if observations were lost. |
| `capture_complete` | Boolean; false for any lost timestamp/token event or interrupted capture whose completeness cannot be established. |
| `missing_reasons` | Object mapping each null timestamp field (and each `token_times_s[i]` null slot, using zero-based JSON array indices) to a reason string. Empty when none are missing. |

Metrics are derived offline using section 4; they are not extra required fields
in this raw record. If exported in a derived table, use exactly those names and
retain their null status. Optional token IDs, if recorded later, must match
array length/order; they are not needed for ITL and are not required by v1.

The run manifest must identify the schema/clock, project and upstream commits,
source/dirty provenance, model/tokenizer identities and revisions, both trace
hashes, policy/parameters, engine and sampling configuration/seeds, warmup/cache
procedure, configured timeout, actual observation cutoff and capture outcome.
It must distinguish completed runs from aborted/incomplete captures. No future
writer may overwrite existing trace, telemetry or formal experiment artifacts.

An illustrative complete record follows. The run ID and times are synthetic;
the hashes identify the existing development trace package, not a real
instrumented inference run. This example uses its fourth request (192 tokens).

```jsonl
{"schema_version":"request-telemetry-v1","run_id":"example-only","request_id":"dev-000004","engine_seq_id":20,"trace_sha256":"28f070031f63d3e0fc4d79accc25cd5df75c5b2e370e62e78da0c6822718d041","metadata_sha256":"ff239cf2ef5fab30652fd385ebbd0b3f945e6e3a4ad05f5c8cd7943cc6917131","policy":"baseline","num_prompt_tokens":192,"max_new_tokens":16,"prompt_class":"long","status":"completed","reason":"eos","planned_arrival_s":0.250,"release_s":0.252,"admitted_s":0.255,"first_scheduled_s":0.280,"first_prefill_dispatch_s":0.282,"first_token_s":0.330,"finished_s":0.361,"terminal_s":0.361,"observation_end_s":1.000,"token_times_s":[0.330,0.345,0.360],"observed_output_tokens":3,"capture_complete":true,"missing_reasons":{}}
```

## 4. Exact metric formulas

Let P, R, A, S, D, T and F denote planned arrival, release, admission, first
scheduling, first prefill dispatch, first token and successful finish in seconds.
Every subtraction below is converted to milliseconds by multiplying by 1000
(or equivalently subtract raw ns first and divide by 1,000,000).

| Metric | Exact formula | Interpretation |
| --- | --- | --- |
| `replay_error_ms` | `1000 * (R - P)` | Signed release lateness; equals REPLAY-001 `release_error_ms`. Absolute-value mean/max are separate replay diagnostics. |
| `admission_overhead_ms` | `1000 * (A - R)` | Release-to-enqueue delay, including callback/adapter delay and any remaining admission processing; not necessarily CPU computation alone. |
| `queue_wait_ms` | `1000 * (S - A)` | Initial admitted wait until first successful selection, including scheduler selection overhead. It is not total lifetime queue residency. |
| `ttft_ms` | `1000 * (T - R)` | Primary user-visible TTFT from actual replay release, including admission overhead and initial queue wait; replay error is reported separately. |
| `engine_ttft_ms` | `1000 * (T - A)` | Engine-visible TTFT, including admitted queue wait. |
| `e2e_latency_ms` | `1000 * (F - R)` | Successful end-to-end request latency from actual replay release to the defined engine completion boundary. |
| `selection_to_first_token_ms` | `1000 * (T - S)` | Internal post-selection latency; may include chunk gaps, recomputation and waits. This is not TTFT or pure GPU prefill time. |
| `prefill_dispatch_delay_ms` | `1000 * (D - S)` | Host delay from first selection to first prefill dispatch, not device execution time. |

Consistency identities when operands exist:

- `ttft_ms = admission_overhead_ms + engine_ttft_ms`.
- `engine_ttft_ms = queue_wait_ms + selection_to_first_token_ms`.
- `e2e_latency_ms = ttft_ms + 1000 * (F - T)`.

Never define TTFT as T minus S. Actual release R is the primary user-visible
request arrival boundary for both TTFT and E2E. Planned arrival P remains
workload intent, not the primary measured latency origin. Keep replay error
separate from these latencies and report it alongside the internal components.
Do not substitute planned arrival or admission for a missing release timestamp.

A metric is null whenever a required operand is missing or its capture is
invalid. Completed-request E2E is also null for every non-completed status.
Observed TTFT and queue wait can still exist for a request that later fails;
report them under that outcome rather than silently combining them with the
successful cohort. Do not clamp negative intervals to zero: flag clock/order
violations and invalidate affected metrics. Equal timestamps yield valid zero
intervals. Aggregate only explicitly defined cohorts and report denominators.

## 5. Timeline example

Synthetic values in seconds, matching the example record:

```text
common t0 = 0

P .250 --> R .252 --> A .255 --------> S .280 -> D .282 -----> T1 .330
 planned    release    admitted        selected  host         first output
                                              prefill
                                              dispatch

T1 .330 ----------> T2 .345 ----------> T3 .360 -> F .361
        15 ms ITL           15 ms ITL               finished after cleanup

R -------------------------> T1       primary TTFT = 78 ms
A -------------------------> T1       engine TTFT  = 75 ms
A ------------> S                     initial wait = 25 ms
R ------------------------------------------------> F   E2E = 109 ms
```

Replay error = 2 ms; admission overhead = 3 ms; initial queue wait = 25 ms;
selection-to-first-token = 50 ms; dispatch delay = 2 ms.
Thus TTFT = 3 + 25 + 50 = 78 ms; E2E = 361 - 252 = 109 ms. The 2 ms
replay error is reported separately. Token 3 is the final appended token (EOS
in this example); completion adds 1 ms after its observation. These are
arithmetic examples, not measurements or expected performance.

## 6. Per-token timing design

Append a timestamp only after a valid generated token is appended to the
sequence. Slot k corresponds to completion token k, not prompt token k,
GPU invocation k or prefill chunk k. Include EOS and other special tokens if
they were appended, even when a later text decoder hides them.

For consecutive output indices k-1 and k, k >= 2:

`itl_ms[k] = 1000 * (token_times_s[k] - token_times_s[k-1])`

Indices in that formula are one-based. The JSON array uses zero-based indices.
There is no ITL for token 1; its latency is TTFT. Zero/one-token requests have
no ITL samples, so their mean ITL is null, not zero. Per-request mean ITL uses
all valid consecutive pairs, with its pair count reported. Pooling pairs across
requests is a different weighting from averaging per-request means; name the
aggregation and report sample counts. Equal observations permit zero ITL.

If a timestamp is lost but token index/count is known, keep a null slot. Do not
bridge a missing slot to form a longer interval labeled as one ITL. If token
identity/count itself is lost, flag `capture_complete=false`; do not assert a
complete per-token series. Preserve reliable observed pairs as diagnostics,
separate from complete-capture ITL comparisons.

Partial-prefill sampled tokens discarded by `Scheduler.postprocess` produce
no token event. Resumed prefill after preemption recomputes previous history
without re-emitting its old token events; new output continues at the next
completion index. The original first-token time never resets. Multiple
requests in one batch may have close/equal host timestamps; sequential
postprocessing overhead is part of this observation boundary. These ITLs
include between-step waiting, preemption/recomputation and host processing;
they are not isolated GPU decode durations.

## 7. Failure and missing-value semantics

Use null plus a specific reason such as `not_released`, `not_admitted`,
`not_scheduled`, `no_output_before_failure`, `no_output_before_cancel`,
`no_output_before_cutoff`, `not_successfully_finished` or `capture_lost`.
Terminal status/reason supplies the context; actual unobserved events must not
be fabricated from expected control flow.

| Outcome | Treatment |
| --- | --- |
| Failure before admission | Preserve planned/release times if observed; admission and downstream events are null. Record detected failure in terminal_s; finished_s is null. |
| Failure after admission/partial output | Preserve all valid observed times and tokens. Missing future events stay null; successful E2E remains null even if the output cap was nearly reached. |
| Acknowledged cancellation | Preserve preceding events; terminal_s is cancellation acknowledgement. Unobserved token/finish times are null, and no successful E2E is reported. A cancellation signal after an already completed request does not change that outcome. |
| No first output token | first_token_s is null and token_times_s is empty when no token was appended; both TTFTs are null, while replay/admission/queue metrics may exist. No zero or timeout substitution. |
| Unresolved at timeout | status=timed_out, terminal_s=observation_end_s, finished_s=null. Preserve partial tokens and observed TTFT. Requests with planned arrival after cutoff remain represented with release/admission null and reason `arrival_after_cutoff`. |
| Collector/process crash | Preserve durable evidence and mark incomplete capture. If failure time is unobserved, terminal_s is null with capture_lost; never substitute the later restart clock. Whole-run completeness cannot be claimed. |

At a configured timeout, events whose sampled offsets are at or before the
cutoff count; later events belong to teardown diagnostics, not this observation
window. An in-flight GPU step may return after the deadline. Do not backdate
its tokens to the deadline or claim that it completed within the window.
The coordinator may finalize records later using the declared cutoff. If a
crash prevents observing that cutoff, use the last durably observed coordinator
offset as observation_end_s, mark capture_complete=false, and identify this as
an aborted run (failed records with reason `run_aborted` unless an earlier
terminal outcome was already observed). The configured deadline stays in run
metadata; it is not evidence of complete observation through that time.

Optional censored bounds are separate fields in an analysis table, never
latency substitutes. If T is missing, A exists and cutoff C >= A, then
`engine_ttft_lower_bound_ms = 1000 * (C - A)` is meaningful only if capture is
complete through C and the request remains active without a token at C.
Similarly, a primary TTFT lower bound is `1000 * (C - R)` only when release
R was observed, C >= R, capture is complete through C and the request remains
active awaiting its first token. Failed/cancelled requests are competing
outcomes, not automatically such active censored observations. An unreleased
request has no measured primary latency origin or TTFT lower bound, even if
its planned arrival is already due at cutoff.

Finalize one record per trace ID, including nonreleased requests; publish
counts for completed, failed, cancelled, timed_out and incomplete-capture
records, plus released/admitted/first-token counts. Primary completion rate
is completed requests divided by all requests in the fixed trace; also report
how many were due by cutoff so a too-short observation window is visible.
Request-level failure handling and cancellation mechanisms remain future work;
this specification does not add them to nano-vLLM.

## 8. Candidate instrumentation points

These are future hook locations verified against the current pinned source,
not changes made by TELEMETRY-001. Paths and line ranges are repository-relative.

| Boundary | Source and candidate placement |
| --- | --- |
| Shared origin / release | `scripts/replay_trace.py:81-94`, `replay_requests`: use existing t0 and the final `now` before callback. Future context handoff must carry these exact values to engine-side recording. |
| External ID mapping | `nanovllm/engine/llm_engine.py:43-47`, `LLMEngine.add_request`: associate trace request_id with the newly constructed Sequence before enqueue. Current add_request returns no seq_id; future adapter/hook design must expose a reliable mapping rather than guess from the global counter. |
| Admission | `nanovllm/engine/scheduler.py:22-23`, `Scheduler.add`: sample just after waiting.append for initial admission only. |
| First scheduling | `nanovllm/engine/llm_engine.py:49-52`, `LLMEngine.step`: immediately after schedule returns, capture one selection time and assign it once to previously unscheduled returned sequences. |
| First prefill dispatch | `nanovllm/engine/llm_engine.py:52`: immediately before runner.call, only for is_prefill=True and only the first such call per request. |
| Valid token append | `nanovllm/engine/scheduler.py:81-88`, `Scheduler.postprocess`: after append_token at line 88, below the incomplete-prefill continue. `nanovllm/engine/sequence.py:67-70` updates the token list/count; scheduling context determines whether the output is valid. |
| Host sampling evidence | `nanovllm/engine/model_runner.py:214-220`, `ModelRunner.run`: sampled IDs become host values before postprocessing. Do not count every returned ID as an output token; partial prefill IDs can be discarded. |
| Successful finish | `nanovllm/engine/scheduler.py:89-92`: after the stop condition's status change, deallocation and running.remove have all succeeded. |
| Preemption context | `nanovllm/engine/scheduler.py:75-79`, `Scheduler.preempt`: a future extension may record requeue episodes; it must not create a new admission or reset first-event timestamps. |
| Failure/cancel/cutoff | Future coordinator around admission and `LLMEngine.step` plus experiment shutdown; no existing cancellation/timeout telemetry hook is claimed. |

`LLMEngine.step` returns only finished outputs (`llm_engine.py:54-55`), and
`generate` assembles final strings later (`llm_engine.py:84-90`). Neither return
boundary is sufficient to reconstruct first-token timing or ITLs.

## 9. Invariants

- For a complete successful capture: P <= R <= A <= S <= D <= T1 <= ... <=
  Tn <= F <= observation_end_s. Check relations only where observations exist;
  never repair violations by reordering, clamping or replacing timestamps.
- First-event fields are write-once. first_token_s equals the first array slot
  when that event is captured; if its capture is lost, both are null with
  matching missing reasons. observed_output_tokens equals array length.
- Every known appended output has one token slot; duplicate events, gaps
  without null markers, and old tokens replayed after preemption are invalid.
  A complete successful capture contains at least one output token and no
  missing lifecycle/token observations for this pinned generation path.
- A normal finish requires a real stop condition and successful per-request
  cleanup. Engine shutdown or callback return alone never establishes finish.
- Warmup/dummy sequences are excluded using the external-ID mapping, not an
  assumption that engine sequence IDs begin at zero for user requests.
- `queue_wait_ms` measures only first admission to first selection. A waiting
  deque can contain an executing partial prefill; raw membership duration
  would mix service and waiting. Lifetime wait, chunk gaps, running-but-not-
  selected delays and preemption waits need separate phase/episode events in
  a later extension. They cannot be reconstructed by summing this one metric.
- Telemetry observes existing order; it must not reorder waiting/running,
  change preemption, token append, sampling, stopping, cache ownership or
  baseline behavior. Buffer observations and serialize outside the critical
  path where feasible; use the same capture method across compared policies.
- Capture timestamps at events, not at later file writes. Exceptions and
  partial capture must remain visible. A missing event is not proof of a fast
  request. No instrumentation overhead or timing accuracy claim is made here.

## 10. Relationship to scheduler experiments

All three policies consume the same validated trace and metadata hashes, with
fixed model/tokenizer, seeds, engine configuration, workload and observation
window. Compare primary TTFT alongside engine TTFT, initial queue wait, replay
error and admission overhead. Report per-prompt-class distributions and counts,
including long-request failures/timeouts; do not claim fairness improvements
from completed-only latency averages while hiding requests that never finished.
Aging's priority formula, eligible waiting subset and reset rules are not
specified or implemented by this telemetry task.

Telemetry outcome fields (future tokens, final output count, observed service
latency or another policy's results) must never feed priority decisions.
Arrival, original prompt length and current causal waiting information remain
the only relevant categories under the existing trace specification. Shared
clock semantics do not authorize access to unarrived trace contents.

Define comparison cohorts, percentile/ITL weighting, timeout handling and
capture-overhead validation before formal experiments. The 12-request
32/96/192-token trace is still development-only; no formal benchmark values
are frozen by this document. Recommended next task: implement CPU-only record
collection/validation and metric derivation against synthetic lifecycle cases,
including nulls, partial prefill and preemption identities, before separately
scoping engine hooks or GPU integration.
