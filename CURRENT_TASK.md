# CURRENT_TASK.md

## Task ID

BENCH-003

## Title

Freeze and implement the formal benchmark orchestrator.

## Goal

Implement a deterministic, non-overwriting runner for the frozen 45-run formal
benchmark without executing the full benchmark yet.

Do not modify any scheduling policy.

## Required Reads

Read:

- AGENTS.md
- PROJECT_STATE.md
- docs/benchmark-protocol.md
- docs/scheduling-policy-design.md
- docs/aging-policy-design.md
- scripts/run_replay.py
- workloads/formal_trace_seed101.meta.json
- workloads/formal_trace_seed202.meta.json
- workloads/formal_trace_seed303.meta.json

## Formal Matrix

The frozen comparison matrix is:

Policies:
- baseline
- short_prompt
- aged_short_prompt

Trace seeds:
- 101
- 202
- 303

Measured repetitions:
- 5 per policy/trace combination

Total:
45 measured runs

Do not change this matrix.

## Run Identity

Every run must have explicit:

- policy
- trace_seed
- repeat_index
- run_id

Run identity must not depend only on timestamps.

No run may overwrite another run.

## Precomputed Run Order

Generate and persist the complete 45-run order before formal measurements.

Use a deterministic balanced/rotated ordering so policy execution time is not
systematically confounded with GPU thermal or power drift.

Do not adapt run order based on observed performance.

Save the frozen order as a manifest before execution.

## Run Isolation

Each measured run must:

1. start from a fresh engine/process state
2. load the frozen model
3. perform the frozen warm-up
4. exclude warm-up from measured results
5. execute exactly one formal trace
6. write to a unique output directory
7. preserve raw artifacts and metadata

## Formal Metadata

Each run record must include:

- policy
- trace seed
- repetition
- run order index
- trace path
- trace SHA256
- project Git commit
- upstream commit
- model revision
- engine configuration
- generation configuration
- aging rate where applicable
- completion count
- run status
- artifact directory

## Failure Rules

Do not silently replace failed runs.

Distinguish at least:

- success
- timeout
- OOM
- runner/infrastructure failure
- lifecycle invariant failure

Preserve partial diagnostics for failed runs.

A timeout, OOM, or policy/runtime failure remains part of the formal experiment
record and must not be silently rerun into a successful observation.

If an explicitly external infrastructure failure is retried, preserve the
original attempt and record the retry relationship.

## Resume Behavior

The orchestrator must be safely resumable.

Already successful runs must not be rerun or overwritten by default.

A resumed benchmark should continue only missing/pending work according to the
manifest.

## Output Structure

Use a structure such as:

artifacts/formal-benchmark/
    manifest.json
    runs/
        <run_id>/
            requests.jsonl
            requests.meta.json
            progress.jsonl
            runner.log

Exact naming may differ, but it must be deterministic and non-overwriting.

## Aggregation

Implement an aggregation utility that reads completed formal run artifacts
without modifying them.

Prepare summaries for:

Primary:
- TTFT
- queue_wait
- E2E

Secondary:
- engine TTFT
- admission overhead
- ITL where available
- completion rate
- throughput

Summarize overall and by:
- short
- medium
- long

Preserve per-run values; do not collapse everything into one number.

## Paired Comparison

Prepare future aggregation by matching policies on:

- trace_seed
- repeat_index

Do not compute or claim final policy superiority in this task.

## Dry Run

Provide a dry-run/list mode that prints the full 45-run plan without loading
the model or using the GPU.

Use it to verify:
- exactly 45 runs
- each policy/seed has exactly 5 repetitions
- no duplicate run IDs
- all trace hashes match the frozen registry
- run order is deterministic

## Tests

Add CPU tests for:

- 45-run matrix construction
- run-ID uniqueness
- deterministic run order
- correct policy/seed/repetition counts
- output-path uniqueness
- manifest serialization
- resume behavior
- failure-state recording
- paired-key construction
- no artifact overwrite

Do not require GPU for these tests.

## Restrictions

Do not:

- run the complete 45-run formal benchmark
- modify scheduling algorithms
- modify formal traces
- change aging rate
- change dependencies
- change benchmark metric definitions

## Validation

Run CPU tests.

Run:

git diff --check
git status --short

Confirm nanovllm/ policy behavior is unchanged.

## PROJECT_STATE

Update PROJECT_STATE.md with:

- BENCH-003 completion
- frozen run matrix
- manifest/orchestrator paths
- dry-run validation result
- next recommended task

## Acceptance Criteria

- exactly 45 formal runs are planned
- run order is frozen before measurement
- run IDs are unique
- output directories cannot overwrite each other
- metadata is reproducible
- resume behavior works
- failure handling is explicit
- aggregation supports paired comparison
- dry run validates the full matrix
- CPU tests pass
- no scheduling behavior changes
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- orchestrator files
- aggregation files
- total planned runs
- run-order rule
- run-ID format
- artifact layout
- resume semantics
- failure semantics
- CPU test count/results
- dry-run validation
- files modified
- recommended next step
