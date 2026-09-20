# Formal benchmark protocol: formal-mixed-v1

BENCH-001, frozen 2026-09-20. This document fixes the workload recipe and
comparison rules before either experimental scheduling policy is implemented.
The 12-request `dev-mixed-v1` trace and BASELINE-001 runs are development
validation only. They are not members of this benchmark or evidence of a policy
speedup. This protocol freezes the recipe; the three formal trace byte hashes
must be registered after trace generation and before any policy run. A change
to a parameter below requires a new protocol/profile version and preserved old
artifacts, never an edit to already measured results.

## 1. Fixed workload and trace construction

Profile ID: `formal-mixed-v1`. Generate **three separate, immutable 60-request
trace packages** with construction seeds **101, 202, 303**. Each package has
exactly 20 short, 20 medium and 20 long requests. For each seed, start with
`[short]*20 + [medium]*20 + [long]*20`, shuffle once with Python
`random.Random(seed).shuffle`, and assign shuffled classes to ordinal requests
1 through 60. Preserve that order in the JSONL. IDs are
`formal-{seed}-{ordinal:06d}`; they do not encode the class. A seed changes the
class ordering, not the fixed arrival schedule. A given policy/repetition pair
uses the exact same trace bytes, IDs, prompts and limits.

The prompt recipe uses the current `scripts/make_trace.py` `TEMPLATE` and
`DETAIL` constants, with `TEMPLATE.format(number=ordinal) + DETAIL*12` as
the source. Use the pinned `Qwen2TokenizerFast` with
`add_special_tokens=False`, `truncation=False`. For each request, encode that
source, decode its first target tokens with `skip_special_tokens=False` and
`clean_up_tokenization_spaces=False`, and re-encode the resulting final text.
Reject the package unless the verified count equals the target exactly.
Store that final text, not an estimated count or a runtime-generated prompt.
The targets are 32/96/192 tokens for short/medium/long; the existing disjoint
validation intervals remain 24–40, 88–104, 184–200, but each generated record
must hit its target. Shared source text and possible shared prefixes are part
of this workload. No chat template, padding or normalization is applied.

Each request has `max_new_tokens=16`. The arrival for zero-based ordinal `i`
is `floor(i/3) * 0.250000` seconds from the common replay origin: three
requests per group at 0, 0.25, ... , 4.75 s (20 groups). Ties retain JSONL
order. This is one fixed offered-load level, not an adaptive rate chosen after
policy outcomes. The context bound is 256 tokens; the largest prompt plus cap
is 208. The trace uses `request-trace-v1` canonical JSONL and a sidecar with
`profile_id=formal-mixed-v1`, seed, exact recipe, model/tokenizer assets and
versions, generation settings, generator source hash and provenance, trace
SHA256 and count/class validation. The generator must use exclusive output
creation and the validator must reject any mismatch. The existing
`scripts/make_trace.py` CLI/metadata validator is hard-coded to 12
`dev-mixed-v1` requests, so a separately scoped formal generator/validator is
required; the development package must not be edited or promoted. Record the
SHA256 of both formal JSONL and sidecar bytes in every future run manifest.

The model and tokenizer are `Qwen/Qwen3-0.6B` revision
`c1899de289a04d12100db370d81485cdf75e47ca` from the existing local
snapshot. Freeze its verified file hashes from `scripts/make_trace.py`
`PINNED_HASHES`, including weight, config and tokenizer assets. Sampling is
temperature 0.6, `ignore_eos=False`, inference seed 42 reset after warm-up;
the per-request output cap remains 16. The engine uses `enforce_eager=True`,
`tensor_parallel_size=1`, `max_model_len=256`,
`max_num_batched_tokens=256`, `max_num_seqs=1`, and
`gpu_memory_utilization=0.6`. Baseline means the pinned upstream waiting and
running queue order; policy work may only change the explicitly scoped waiting
selection logic after its own task authorizes it. No output length or future
arrival/result may enter a scheduling decision.

## 2. Capacity and load gate before formal measurement

BASELINE-001 completed 12/12 in three runs with the above engine/generation
settings and the first four arrival groups. Its mean initial queue wait was
25.155–27.865 ms and the maximum was 54.046–62.202 ms. This supports using
the configuration as a conservative starting point but does **not** establish
60-request completion, memory safety or meaningful contention. No 60-request
GPU calibration was performed in BENCH-001; no policy result has been inspected.

Before any formal policy measurement, generate and validate all three packages,
then run baseline-only capacity checks for **each seed** with the frozen
configuration and arrival pattern. Record GPU memory observations, completion
counts, lifecycle validation, cutoff/exit status and initial queue-wait
distribution. The gate passes only if each check finishes 60/60 before the
90 s experiment cutoff, has no OOM or engine error, preserves lifecycle/token
invariants, and has nontrivial contention: at least 15/60 requests have
`queue_wait_ms >= 20` and at least one has `queue_wait_ms >= 100`. These
thresholds are operational load checks, not performance targets or reasons to
choose one policy. No formal comparison begins if this gate fails. Keep failed
calibration artifacts and report the blocker; any revised arrivals, engine
configuration, output cap or timeout require `formal-mixed-v2` and a new
baseline capacity gate before policy measurements. Do not tune this profile
against `short_prompt` or `aged_short_prompt` outcomes.

## 3. Paired trial schedule and common setup

After the capacity gate passes, collect **five measured repetitions for each
policy and each trace seed**: 3 seeds × 5 repetitions × 3 policies = 45 runs.
Use a fresh process/engine and unique, exclusive run directory for every run.
Every run validates and pretokenizes the trace before its clock starts, uses the
same four-token `Say hello.` warm-up with telemetry disabled, checks the engine
is idle, resets the inference seed to 42, then establishes one shared
`perf_counter_ns` origin and enables telemetry. Warm-up output never joins a
formal record. Use the same producer-thread/admission-queue and coordinator
behavior for all policies. Wait a fixed 30 s after each process exit before
starting the next process; record the actual gap and GPU temperature/power
when available, without altering metrics or silently skipping runs.

For each repetition `r=0..4` and seed index `s=0..2` (101, 202, 303), run one
three-policy block on that seed. Execute blocks in repetition-major, then seed
order. Rotate policy order by `(r+s) mod 3`:

| Rotation | First | Second | Third |
| --- | --- | --- | --- |
| 0 | baseline | short_prompt | aged_short_prompt |
| 1 | short_prompt | aged_short_prompt | baseline |
| 2 | aged_short_prompt | baseline | short_prompt |

Across 15 blocks every policy occupies each position five times. The paired
unit is `(trace_seed, repetition)`; do not compare unmatched seeds as if they
were paired. Run IDs encode profile, seed, repetition, policy and a unique
timestamp/random suffix; directories are never overwritten. A failed block
retains its slot and artifacts. Do not selectively replace only a slow or
failed policy run; diagnose it and, if a valid infrastructure retry is needed,
rerun the entire three-policy block with a new attempt ID and a documented
reason, keeping both attempts. Changed experimental parameters require a new
protocol version rather than an in-place retry.

## 4. Outcomes, metrics and comparison units

The fixed denominator is 60 trace requests per run, including unreleased and
failed requests. The primary performance cohort is completed requests from
runs that pass all 60/60 and lifecycle checks; display incomplete-run metrics
only as labelled diagnostics. Primary metrics are release-origin `ttft_ms` and
`e2e_latency_ms`, plus first-selection `queue_wait_ms`. Their formulas and
null rules are exactly those in `docs/telemetry-spec.md`:
`1000*(first_token_s-release_s)`, `1000*(finished_s-release_s)`, and
`1000*(first_scheduled_s-admitted_s)`. Planned arrival is workload intent;
`replay_error_ms` remains separate. Never substitute a cutoff for a missing
first token or finish.

Secondary metrics: `engine_ttft_ms`, `admission_overhead_ms`,
`replay_error_ms`, completion rate (`completed/60`), and throughput
(`completed_count / (last_finished_s - first_release_s)` for a fully completed
run; report the exact denominator and both boundaries). ITL is each valid
consecutive token-time difference in ms, excluding token 1; report per-request
mean ITL with pair counts, then the median of eligible per-request means.
Also report pooled-token-pair mean separately with its pair count. Requests
with fewer than two observed tokens have null ITL, never zero.

For each run, show counts, mean, median, p95 and maximum of each applicable
latency overall and separately for short, medium and long. Use nearest-rank
p95 (`sorted_values[ceil(0.95*n)-1]`) and label its denominator; at n=20 it
is nearly a maximum, so avoid a strong tail claim from one run. Aggregate
across repeated runs by reporting the distribution of **run-level** summaries
and the paired run-level differences by `(seed,repetition)`. For each policy
against baseline, compute candidate minus baseline for run-level mean and
median TTFT, queue wait and E2E, overall and by class. Negative differences
mean lower latency. Report the median, range and all 15 paired differences,
plus per-seed breakdown; do not treat 60 requests within a run as independent
experimental replications. Descriptive plots may show request-level values,
but no p-value or significance claim is part of this protocol. Show complete
counts and output-token distributions because the same sampling seed does not
guarantee identical outputs under changed execution order.

Long-request fairness is a prespecified diagnostic: report long-class
completion rate, mean/median/p95/max initial queue wait, TTFT and E2E, their
paired changes against baseline, and each long request's first-selection and
finish order. Count long requests with `queue_wait_ms > 10,000` and those
without first selection or completion by cutoff as near-starvation and
starvation indicators. The 10 s threshold is a fixed operational flag, not a
claim that shorter waits are fair. Report the long/short ratio of run-level
median queue wait and TTFT only when both denominators are positive; otherwise
mark the ratio undefined. A short-request gain must be shown alongside these
long-request outcomes, including any failed/incomplete long requests.

## 5. Timeout, failure and artifact rules

The coordinator observation cutoff is **90 s after t0** for every run. Use a
**150 s process watchdog** from process spawn to catch initialization or a GPU
step that does not return; terminate the process group after the watchdog,
with a 5 s graceful wait before forced kill. The coordinator deadline is the
measurement cutoff. A hard kill leaves only the last durable checkpoint; do
not backdate later work or invent an unobserved terminal timestamp.

Write one final `request-telemetry-v1` row per trace ID. Completed means
observed normal engine finish by cutoff. Failure, timeout, crash, OOM or
unreleased requests retain observed timestamps and null missing events with
specific reasons. Use `timed_out` only where the coordinator observed its
cutoff; a process killed without such observation is an aborted/incomplete
capture. Preserve stdout/stderr, traceback, exit code, progress checkpoints,
partial JSONL, manifest, GPU memory/error diagnostics and all prior attempts.
Count completed, failed, timed out, cancelled and incomplete-capture records
separately. No incomplete run enters the successful-run performance summary;
report it in an outcome table with `completed/60` and causes. An OOM is a
capacity-gate or formal-run failure, never a reason to reduce the workload
mid-comparison. If a failure blocks the required five valid repetitions, stop
the comparison and report the missing pairs rather than silently omitting
them. Repeated successful runs are not retrospectively replaced.

The existing runner is a development baseline entry point. A later task must
implement formal package validation, policy selection and formal manifests
before measured comparison. Its current timeout/checkpoint mechanism is the
starting behavior; this document does not claim that unimplemented policies
or a 60-request formal execution already exist.

## 6. Per-run provenance and audit

Each formal run manifest records protocol/profile version; full project Git
commit and dirty patch/source hashes; pinned upstream commit; model and
tokenizer repository, revision and asset hashes; exact trace and sidecar
SHA256, trace seed, profile and request IDs; policy name and version/parameters;
engine and generation configuration including inference seed; warm-up/cache
procedure; producer/coordinator implementation and clock origin/resolution;
run ID, attempt, UTC start/end, host/OS/Python/Torch/Triton/FlashAttention,
CUDA/driver/GPU identity, memory observations, clocked timeout and watchdog;
run-order block/position, cooldown; request/completion/outcome counts; and
paths/hashes of result and log files. Report observed release error and
admission overhead beside latency so replay/host jitter remains visible.

Before considering a run valid, verify the exact trace package, prompt token
counts, ID/class/limit sets, shared t0, output/token-time count, monotone
lifecycle and token times, release-based metric formulas, no duplicate/lost
requests, and matching model/config/provenance across a paired block.
Compare input hashes and configuration **before** examining policy latency.
The formal trace hash registry should be appended to this protocol only after
all three packages are generated and validated, before the capacity gate; it
is a registration of frozen recipe outputs, not permission to change the
recipe. Preserve the original registry and create a new profile version if
regeneration changes any bytes.
