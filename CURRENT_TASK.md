# CURRENT_TASK.md

## Task ID

BASELINE-001

## Title

Characterize the reproducibility of the development baseline.

## Goal

Run repeated development experiments using the unchanged nano-vLLM baseline
scheduler and establish a reproducible baseline result format.

This is not the final formal benchmark.

Do not implement or change any scheduling policy.

## Required Reads

Read:

- AGENTS.md
- PROJECT_STATE.md
- docs/trace-spec.md
- docs/telemetry-spec.md
- scripts/run_replay.py
- workloads/dev_trace.jsonl

## Baseline Invariants

All measured runs must use the same:

- Qwen3-0.6B model and revision
- dev trace
- trace SHA256
- engine configuration
- generation configuration
- baseline scheduler behavior

Do not reorder the waiting queue.

## Failure / Timeout Handling

Before repeated runs, ensure the experiment runner has explicit handling for:

- completed requests
- failed requests
- experiment timeout
- partial results

A failed or timed-out run must:

- preserve available diagnostic output
- clearly report incomplete requests
- not silently count incomplete requests as successful

Do not modify nano-vLLM scheduler semantics to implement this.

## Repeated Runs

Execute 3 independent development baseline runs.

Each run must:

1. initialize the engine
2. perform the existing warm-up
3. exclude warm-up data
4. replay the exact same dev trace
5. complete all 12 requests
6. preserve the trace SHA256
7. produce a unique run_id
8. avoid overwriting previous run artifacts

Use fresh run output locations.

## Run Metadata

Record for every run:

- run_id
- policy = baseline
- project Git commit
- pinned upstream commit
- model identity/revision
- trace SHA256
- engine configuration
- request count
- completion count
- timestamp
- environment identifiers already available from project metadata

## Metrics

For each run compute overall diagnostics for:

- replay_error_ms
- admission_overhead_ms
- queue_wait_ms
- ttft_ms
- engine_ttft_ms
- e2e_latency_ms

Also summarize by:

- short
- medium
- long

Because this is a small 12-request development workload, emphasize:

- mean
- median
- max

Do not make statistical performance claims from four requests per prompt class.

## Cross-Run Reproducibility

Compare the three runs.

Verify:

- identical trace SHA256
- identical request IDs
- identical request metadata
- 12/12 completions in each run
- all lifecycle invariants hold

Summarize run-to-run variation in the key latency metrics.

## Output

Store raw development run artifacts under a non-overwriting structure such as:

artifacts/baseline/<run_id>/

Create:

artifacts/baseline/dev-baseline-summary.json

The summary must clearly state:

development baseline only; not final benchmark data.

## Restrictions

Do not:

- implement short_prompt
- implement aging
- change scheduler ordering
- change KV-cache behavior
- change model execution
- change dependencies
- change the development trace

Avoid modifying nanovllm/ unless required to fix a demonstrated telemetry bug.
If such a bug is found, stop and report it before changing core source.

## Validation

Run relevant CPU tests.

Run:

git diff --check
git status --short

## PROJECT_STATE

Update PROJECT_STATE.md with:

- BASELINE-001 completion
- baseline run count
- reproducibility result
- next recommended task

## Acceptance Criteria

- 3 independent baseline runs complete
- each run completes 12/12 requests
- trace SHA256 is identical across runs
- scheduler semantics remain unchanged
- run artifacts are not overwritten
- failure/timeout handling is explicit
- per-class summaries exist
- cross-run variation is reported
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- run IDs
- completion counts
- trace SHA256
- engine configuration
- overall metrics by run
- per-class diagnostics
- cross-run variation
- failure/timeout behavior
- files modified
- recommended next step
