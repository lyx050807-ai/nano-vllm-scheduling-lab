# CURRENT_TASK.md

## Task ID

TELEMETRY-001

## Title

Define request lifecycle telemetry and metric semantics.

## Goal

Define the timestamp events and derived latency metrics required to compare
baseline, short_prompt, and aged_short_prompt scheduling policies.

This is a design/documentation task only.

Do not instrument nano-vLLM source yet.

## Required Work

1. Read:
   - AGENTS.md
   - PROJECT_STATE.md
   - docs/architecture.md
   - docs/trace-spec.md
   - scripts/replay_trace.py

2. Define one common monotonic clock domain for runtime timestamps.

3. Define request lifecycle timestamps including at least:

   - planned_arrival_s
   - release_s
   - admitted_s
   - first_scheduled_s
   - first_token_s
   - finished_s

4. Define per-token timing representation sufficient for future ITL analysis.

5. Define the exact semantic meaning and capture point for every timestamp.

6. Distinguish clearly between:

   - replay timing
   - engine admission
   - waiting-queue delay
   - first scheduling / prefill start
   - first output token
   - request completion

7. Define derived metrics including at least:

   replay_error_ms
   admission_overhead_ms
   queue_wait_ms
   ttft_ms
   engine_ttft_ms
   e2e_latency_ms

8. Define future ITL calculation from token timestamps.

9. Define units and formulas explicitly.

10. Define missing-value behavior for:
    - failed requests
    - cancelled requests
    - requests that never receive a first token
    - unfinished requests at experiment timeout

11. Define an event/record schema suitable for JSONL output.

12. Identify candidate source locations from docs/architecture.md where future
    telemetry hooks should be inserted.

Do not implement those hooks yet.

## Metric Semantics

Primary user-facing TTFT must include waiting time.

Do not define TTFT as first_token_s - first_scheduled_s.

The design should preserve both:

- user-facing latency
- internal scheduler/engine latency components

## Output

Create:

docs/telemetry-spec.md

Include:

1. clock definition
2. lifecycle event definitions
3. event/record schema
4. exact formulas
5. timeline example
6. per-token timing design
7. failure/missing-value semantics
8. candidate instrumentation points
9. invariants
10. relationship to scheduler experiments

Include an ASCII request timeline.

## Restrictions

Do not:

- modify nanovllm/
- implement telemetry hooks
- implement policies
- run GPU benchmarks
- change dependencies

## Validation

Run:

git diff --check
git status --short

Confirm nanovllm/ is unchanged.

## PROJECT_STATE

Update PROJECT_STATE.md with TELEMETRY-001 completion and next recommended task.

## Acceptance Criteria

- lifecycle timestamps are unambiguously defined
- all timestamps use a compatible monotonic clock
- TTFT includes waiting time
- queue wait is separately measurable
- E2E latency is defined
- future ITL can be computed
- failure semantics are documented
- future hook locations are identified
- no nano-vLLM source is modified
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- lifecycle events
- clock choice
- metric formulas
- event schema
- failure semantics
- candidate instrumentation locations
- files modified
- recommended next step
