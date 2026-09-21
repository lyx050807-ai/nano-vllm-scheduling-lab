# CURRENT_TASK.md

## Task ID

AGING-002

## Title

Implement aged_short_prompt scheduling.

## Goal

Implement the aged_short_prompt policy exactly as defined in
docs/aging-policy-design.md while preserving baseline, short_prompt, resource
checks, decode behavior, KV-cache behavior, and telemetry independence.

## Required Reads

Read:

- AGENTS.md
- PROJECT_STATE.md
- docs/scheduling-policy-design.md
- docs/aging-policy-design.md
- docs/benchmark-protocol.md
- nanovllm/config.py
- nanovllm/engine/scheduler.py
- nanovllm/engine/sequence.py
- nanovllm/engine/waiting_policy.py

Inspect current source before editing.

## Configuration

Support:

- baseline
- short_prompt
- aged_short_prompt

Default remains:

baseline

Use the frozen aging rate defined by AGING-001:

320 tokens/second

Do not tune this parameter using policy performance.

Invalid policies or invalid aging parameters must fail clearly.

## Aging Score

For aged_short_prompt:

score =
num_prompt_tokens
-
aging_rate_tokens_per_second * age_seconds

where:

age_seconds =
(now_ns - first_enqueue_ns) / 1_000_000_000

Select the request with the smallest score.

Do not use output length or any future information.

## Scheduler-Owned Age State

The scheduler must own the timing state used for aging.

Use a monotonic clock.

Record a request's first enqueue time the first time it enters the scheduler
waiting queue.

Do not reset that origin during preemption/requeue.

Do not depend on telemetry timestamps.

Clean up scheduler-owned age state when a request permanently finishes so
state does not leak indefinitely.

## Preemption Semantics

If a request:

- first enters waiting
- later runs
- is later preempted back into waiting

its original first_enqueue timestamp must be preserved.

Its age therefore reflects time since original scheduler admission, as
documented in AGING-001.

Do not silently redefine this as current-waiting-episode time.

## Selector

Preserve O(n) selection.

Do not globally sort the waiting deque.

For equal effective scores, preserve current waiting deque order.

Use strict comparison rather than replacing an existing winner on equal score.

## Existing Policies

baseline must remain exactly equivalent to current baseline behavior.

short_prompt must remain exactly equivalent to POLICY-002 behavior.

Do not add clock/aging behavior that changes their selection results.

Avoid unnecessary aging-clock work when policy is not aged_short_prompt where
practical.

## Resource Checks

After candidate selection, execute the existing scheduler checks unchanged.

If the selected aged candidate fails a resource/allocation condition that
currently stops the scheduling pass, preserve that behavior.

Do not fall through to another candidate.

## Waiting Removal / Lifecycle

Preserve:

- chunked-prefill semantics
- waiting-to-running transitions
- remaining deque relative order
- preemption behavior
- running/decode order

No request may be lost or duplicated.

## Deterministic CPU Tests

Use an injectable/fake monotonic clock where practical.

Test at least:

1. default policy remains baseline
2. short_prompt behavior remains unchanged
3. aged_short_prompt at zero age ranks requests like short_prompt
4. aging score improves monotonically as age increases
5. medium vs new short crossover is approximately 0.2 s
6. long vs new medium crossover is approximately 0.3 s
7. long vs new short crossover is approximately 0.5 s
8. an old long request eventually outranks a newly arrived short request
9. equal-score ties preserve deque order
10. first enqueue timestamp is recorded once
11. preemption/requeue does not reset first enqueue timestamp
12. completed request age state is cleaned up
13. candidate failure does not fall through
14. no request loss or duplication
15. telemetry on/off does not affect decisions
16. baseline and short_prompt regression tests still pass

Do not use real sleeps for policy unit tests.

## GPU Functional Smoke

After CPU tests pass, run the existing 12-request development workload with:

- baseline
- short_prompt
- aged_short_prompt

This is functional validation only.

All policies must:

- complete 12/12
- have no OOM
- have no timeout
- satisfy lifecycle invariants
- produce valid policy metadata

It is acceptable if aged_short_prompt behaves similarly to short_prompt on a
development workload where request age never reaches meaningful crossover
thresholds.

Do not claim performance superiority.

## Targeted Aging Validation

Add a deterministic CPU scenario that clearly causes aging to change the
winner.

For example, demonstrate that a sufficiently old 192-token request can outrank
a newly arrived 32-token request according to the frozen crossover rule.

This validation must not depend on GPU timing.

## Restrictions

Do not:

- change formal benchmark traces
- run the final 45-run benchmark
- change KV-cache policy
- add resource-aware bypass selection
- change running/decode ordering
- change model execution
- change sampling
- change dependencies

## Validation

Run:

git diff --check
git status --short

Review all nanovllm/ source changes carefully.

## PROJECT_STATE

Update PROJECT_STATE.md with:

- AGING-002 status
- implementation files
- aging-state semantics
- CPU tests
- GPU smoke results
- next recommended task

## Acceptance Criteria

- aged_short_prompt is implemented
- frozen 320 tokens/s rate is used
- first enqueue age survives preemption
- telemetry is not required
- O(n) stable selection is preserved
- baseline is unchanged
- short_prompt is unchanged
- existing resource checks are unchanged
- CPU tests pass
- all three GPU smoke runs complete 12/12
- lifecycle invariants pass
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- files modified
- age state representation
- clock design
- score implementation
- aging rate
- tie behavior
- preemption behavior
- cleanup behavior
- CPU test count/results
- baseline smoke result
- short_prompt smoke result
- aged_short_prompt smoke result
- targeted crossover validation
- warnings/errors
- recommended next step
