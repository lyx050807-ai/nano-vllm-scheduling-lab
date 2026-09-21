# CURRENT_TASK.md

## Task ID

BENCH-004

## Title

Execute the frozen 45-run formal scheduling benchmark.

## Goal

Execute the complete frozen formal benchmark using the BENCH-003 manifest.

This task produces the formal measured data for:

- baseline
- short_prompt
- aged_short_prompt

Do not change policies, traces, metrics, run order, or benchmark configuration.

## Required Reads

Read:

- AGENTS.md
- PROJECT_STATE.md
- docs/benchmark-protocol.md
- docs/scheduling-policy-design.md
- docs/aging-policy-design.md
- scripts/formal_benchmark.py
- scripts/aggregate_formal.py
- scripts/run_replay.py
- the frozen formal benchmark manifest

Verify the working tree is clean before formal execution.

## Frozen Matrix

Execute exactly the frozen matrix:

Policies:
- baseline
- short_prompt
- aged_short_prompt

Seeds:
- 101
- 202
- 303

Measured repetitions:
- 5

Total measured runs:
45

Use the exact frozen manifest and its precomputed run order.

Do not regenerate or reorder the manifest.

## Environment Check

Before the first measured run, record the existing project/environment metadata.

Confirm:

- correct Git commit
- correct upstream commit
- correct model revision
- correct formal trace SHA256 values
- correct aging rate
- CUDA/GPU availability
- no existing unexpected formal run artifacts

Do not change dependency versions.

## Execution

Run the formal benchmark through the BENCH-003 orchestrator.

For every run:

- use the frozen trace
- use the frozen policy
- use the frozen engine configuration
- use the frozen warm-up
- exclude warm-up data
- preserve the unique run ID
- preserve raw artifacts
- preserve progress and logs
- record final status

Do not manually reorder policies.

## Failure Semantics

Use the frozen BENCH-003 failure rules.

Do not silently convert a failed measured run into a successful observation.

Preserve:

- timeout
- OOM
- infrastructure failure
- lifecycle invariant failure
- partial artifacts

If execution stops because the manifest contains a running/interrupted item,
report the state before taking any retry action.

Do not delete failed attempts.

## Resume

If the benchmark process itself is interrupted:

- preserve the manifest
- preserve completed runs
- use the existing resume semantics
- do not rerun successful runs
- do not overwrite artifacts

## Monitoring

During execution, verify periodically:

- completed run count
- failed run count
- pending run count
- current policy/seed/repetition
- no artifact overwrite
- no unexpected trace/hash changes

Do not inspect intermediate performance numbers in order to change the
experiment.

## Post-Run Validation

After execution, verify:

- all 45 manifest entries have terminal states
- successful runs have 60/60 request completion
- formal trace hashes match
- lifecycle invariants pass
- no duplicate run IDs
- no missing artifacts
- policy metadata is correct
- aging rate metadata is correct where applicable

Report any failures separately.

## Aggregation

Run the frozen aggregation utility only after execution is complete.

Create summaries for:

Primary:
- TTFT
- queue_wait
- E2E latency

Secondary:
- engine TTFT
- admission overhead
- ITL where available
- completion rate
- throughput

Summarize:

- overall
- short
- medium
- long

Preserve per-run results.

Prepare paired comparison keys using:

- trace_seed
- repeat_index

Do not discard raw data.

## Statistical Restraint

Do not declare a policy superior merely from a single average.

Report descriptive results first.

Do not change the workload or aging parameter after seeing results.

Any later statistical analysis must use the already frozen formal data.

## Restrictions

Do not:

- modify scheduling policies
- modify formal traces
- modify the aging rate
- modify metric definitions
- modify run order
- change dependencies
- silently rerun failed measured runs
- delete unfavorable results

If an implementation bug is discovered that could invalidate measurements,
stop and report it rather than patching code mid-benchmark.

## Validation

After the benchmark:

git diff --check
git status --short

Formal execution artifacts may be new, but source code should remain unchanged.

## PROJECT_STATE

Update PROJECT_STATE.md only after the run set is complete or formally stopped.

Record:

- BENCH-004 status
- 45-run completion summary
- success/failure counts
- artifact locations
- aggregation status
- recommended next analysis task

## Acceptance Criteria

- frozen manifest is used unchanged
- frozen run order is followed
- all 45 runs are attempted according to protocol
- artifacts are non-overwriting
- completed runs have valid request data
- failures remain explicitly recorded
- aggregation preserves paired structure
- no scheduling policy is changed
- no formal trace is changed

Do not create a Git commit.

## Completion Report

Report:

- total runs
- successful runs
- failed runs by reason
- elapsed benchmark time
- run-order/manifest integrity
- request completion validation
- trace-hash validation
- aggregate overall metrics
- short/medium/long metrics
- paired comparison artifact
- warnings or anomalies
- files/artifacts created
- recommended next step
