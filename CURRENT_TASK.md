# CURRENT_TASK.md

## Task ID

BENCH-002

## Title

Generate and validate the frozen formal benchmark traces.

## Goal

Materialize the formal benchmark traces defined by docs/benchmark-protocol.md
and verify that the unchanged baseline engine can safely execute the formal
60-request workload before any scheduling policy is implemented.

Do not implement short_prompt or aging.

## Required Reads

Read:

- AGENTS.md
- PROJECT_STATE.md
- docs/benchmark-protocol.md
- docs/trace-spec.md
- docs/telemetry-spec.md
- scripts/make_trace.py
- scripts/run_replay.py

## Formal Traces

Generate one formal trace for each frozen seed:

- 101
- 202
- 303

Each trace must contain exactly:

- 20 short requests
- 20 medium requests
- 20 long requests
- 60 total requests

Use the frozen prompt lengths, generation limits, and arrival design from
docs/benchmark-protocol.md.

Do not change the protocol to improve scheduler performance.

## Trace Artifacts

Store formal traces under workloads/ using clear names such as:

- formal_trace_seed101.jsonl
- formal_trace_seed202.jsonl
- formal_trace_seed303.jsonl

Store matching metadata sidecars.

For every trace record:

- seed
- request count
- class counts
- tokenizer/model revision
- trace version
- SHA256

## Determinism Validation

For every seed:

1. regenerate the trace independently
2. verify byte-for-byte equality
3. verify identical SHA256
4. run the existing trace validator

Confirm different seeds produce different intended stochastic ordering.

## CPU Validation

Run all existing trace/replay/telemetry CPU tests.

Confirm formal traces satisfy:

- unique request IDs
- nondecreasing arrivals
- stable same-arrival ordering
- exact tokenizer-derived prompt lengths
- context safety
- valid generation limits

## Baseline Capacity Check

Using the unchanged baseline scheduler, run one development/calibration GPU
execution for each formal trace.

This is capacity validation only, not a formal measured benchmark.

For each seed verify:

- 60/60 requests accounted for
- 60/60 requests complete
- no OOM
- no experiment timeout
- no lifecycle invariant violation
- no duplicate or missing request IDs
- trace SHA256 matches the formal trace

## Queue-Contention Check

Confirm the workload creates meaningful waiting-queue contention.

Report diagnostics such as:

- requests with queue_wait_ms > 0
- mean/median/max queue_wait_ms
- maximum observed backlog if available
- short/medium/long queue-wait summaries

Do not tune the workload based on future policy performance.

If the frozen load fails capacity or creates effectively no scheduling
contention, stop and report the evidence before changing the protocol.

## Artifact Separation

Clearly mark these GPU runs as:

capacity/calibration only

Do not mix them with future formal benchmark measurements.

Store them under a separate calibration directory.

## Restrictions

Do not:

- implement short_prompt
- implement aging
- change waiting queue ordering
- change running queue ordering
- modify KV-cache policy
- modify model execution
- change dependencies
- silently change the frozen benchmark protocol

Avoid modifying nanovllm/.

If a core bug is found, stop and report before changing core source.

## Validation

Run:

git diff --check
git status --short

## PROJECT_STATE

Update PROJECT_STATE.md with:

- BENCH-002 completion
- formal trace paths and SHA256 hashes
- baseline capacity results
- queue-contention result
- next recommended task

## Acceptance Criteria

- all 3 formal traces exist
- every trace has exactly 60 requests
- class counts are 20/20/20
- same-seed regeneration is byte-identical
- trace hashes are recorded
- all traces validate
- baseline completes 60/60 for all three seeds
- no OOM or timeout occurs
- workload exhibits meaningful queue contention
- scheduler semantics remain unchanged
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- formal trace filenames
- seeds and SHA256 hashes
- request/class counts
- determinism results
- CPU test results
- per-seed baseline completion
- per-seed runtime
- queue-contention diagnostics
- errors/warnings
- files created/modified
- recommended next step
