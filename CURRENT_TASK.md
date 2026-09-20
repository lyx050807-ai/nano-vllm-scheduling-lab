# CURRENT_TASK.md

## Task ID

REPLAY-001

## Title

Implement and validate the trace arrival replay driver.

## Goal

Implement a CPU-only replay driver that releases requests according to the
absolute arrival_s timestamps in a validated trace.

This task validates arrival timing only.

Do not connect replay to nano-vLLM GPU inference yet.

## Required Work

1. Read:
   - AGENTS.md
   - PROJECT_STATE.md
   - docs/trace-spec.md
   - scripts/make_trace.py
   - workloads/dev_trace.jsonl

2. Implement:

   scripts/replay_trace.py

3. Load and validate the trace before replay begins.

4. Define one monotonic experiment start time t0.

5. For every request compute:

   target_arrival = t0 + arrival_s

6. Wait until the absolute target time.

Do not implement replay as cumulative sleep intervals.

7. At release time record:

   - request_id
   - planned arrival_s
   - actual release time relative to t0
   - release error in milliseconds

8. Provide a CPU-only dry-run / callback interface so replay timing can be
   tested without nano-vLLM or GPU inference.

9. Preserve stable ordering for requests with identical arrival_s according to
   their order in the trace file.

10. Use a monotonic high-resolution clock such as time.perf_counter().

## Timing Semantics

Clearly distinguish:

- planned arrival time
- actual replay release time
- future engine admission time
- future scheduling time
- future first-token time
- future completion time

Do not redefine TTFT in this task.

## Tests

Add CPU tests covering at least:

- trace order preservation
- identical-arrival stable ordering
- absolute-time replay behavior
- no cumulative timing drift by design
- invalid trace rejection
- callback receives every request exactly once

Keep timing tolerances reasonable for a non-real-time operating system.

Tests must not require GPU inference.

## Output

Create:

artifacts/replay/dev_replay_timing.jsonl

or an equivalent small replay timing record.

Report basic timing error statistics:

- mean absolute release error
- max absolute release error

These are infrastructure diagnostics, not model performance metrics.

## Restrictions

Do not:

- modify nanovllm/
- connect to real model inference
- implement telemetry hooks
- implement scheduling policies
- run performance benchmarks
- change dependencies

## Validation

Run CPU tests.

Run:

git diff --check
git status --short

Confirm nanovllm/ is unchanged.

## PROJECT_STATE

Update PROJECT_STATE.md with REPLAY-001 completion and next recommended task.

## Acceptance Criteria

- replay uses absolute monotonic target times
- requests are released in trace order
- equal-arrival ordering is stable
- every request is released exactly once
- release timing is measured
- CPU tests pass
- no nano-vLLM source is modified
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- replay interface
- clock used
- timing algorithm
- test count/results
- mean release error
- max release error
- files created/modified
- recommended next step
