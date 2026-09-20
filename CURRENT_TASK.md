# CURRENT_TASK.md

## Task ID

TELEMETRY-002

## Title

Implement low-overhead request lifecycle telemetry.

## Goal

Instrument the pinned nano-vLLM request lifecycle so experiments can measure
admission, first scheduling, token production, and completion timestamps.

Telemetry must not change scheduling semantics.

## Required Reads

Read:

- AGENTS.md
- PROJECT_STATE.md
- docs/architecture.md
- docs/telemetry-spec.md
- scripts/replay_trace.py

Inspect the exact pinned source before editing.

## Required Runtime Events

Implement engine-side capture for:

- admitted time
- first scheduled time
- first output token time
- per-output-token timestamps
- finished time

Use the clock semantics defined in docs/telemetry-spec.md.

## Design Requirements

1. Use one compatible monotonic clock domain.

2. Record first_scheduled only once.

3. Record first_token only once.

4. Preserve per-token timestamps for future ITL calculation.

5. Record finished when the request actually transitions to completion.

6. Associate all engine telemetry with request_id.

7. Keep replay-layer planned_arrival and release timestamps outside the engine
   unless an existing clean interface already supports carrying them.

8. Prefer in-memory timestamp capture on hot paths.

9. Avoid per-token disk I/O.

10. Provide a clean way for the experiment/replay layer to retrieve completed
    request telemetry.

## Scheduling Invariants

Telemetry must not change:

- waiting queue ordering
- running queue ordering
- request selection
- prefill/decode scheduling policy
- KV-cache allocation decisions
- preemption behavior
- sampling behavior

## Testing

Add CPU-focused tests wherever possible for:

- timestamps start unset
- admitted recorded once
- first_scheduled recorded once
- first_token corresponds to the first generated output token
- token timestamps preserve generation order
- finished recorded once
- incomplete requests retain null/missing future timestamps
- metric record serialization works

Also rerun relevant existing tests.

## GPU Regression Smoke Test

After CPU tests pass, rerun the existing conservative single-request smoke test.

Confirm:

- inference still succeeds
- generated output is non-empty
- telemetry record is produced
- lifecycle ordering is valid:

  admitted <= first_scheduled <= first_token <= finished

- token timestamps are nondecreasing
- no scheduling-policy behavior was intentionally changed

Do not treat the smoke-test latency as benchmark data.

## Output

Create or update a small experiment-facing telemetry utility if needed.

Save one example completed telemetry record under:

artifacts/telemetry/

Do not store large logs.

## Validation

Run:

git diff --check
git status --short

Review the nano-vLLM source diff carefully.

## PROJECT_STATE

Update PROJECT_STATE.md with:

- TELEMETRY-002 completion
- source files instrumented
- tests run
- smoke-test result
- next recommended task

## Acceptance Criteria

- lifecycle timestamps are captured
- first-event semantics are correct
- per-token timestamps are available
- telemetry can be exported by request_id
- CPU tests pass
- single-request GPU regression passes
- scheduling semantics remain unchanged
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- source files modified
- fields/events added
- instrumentation points
- test count/results
- GPU smoke result
- example event ordering
- any observed overhead/warnings
- recommended next step
