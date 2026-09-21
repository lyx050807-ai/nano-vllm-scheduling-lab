# CURRENT_TASK.md

## Task ID

FINAL-001

## Title

Package scheduling-lab v1 as a complete reproducible project.

## Goal

Finalize the existing v1 scheduling study for presentation and reproducibility.

Do not modify scheduling behavior, benchmark data, formal traces, aging
parameters, dependencies, or raw artifacts.

This task is documentation and project packaging only.

## Required Reads

Read:

- AGENTS.md
- PROJECT_STATE.md
- README.md
- docs/architecture.md
- docs/scheduling-policy-design.md
- docs/aging-policy-design.md
- docs/benchmark-protocol.md
- artifacts/analysis/formal-v1/report.md
- artifacts/analysis/formal-v1/anomaly-analysis.md
- artifacts/analysis/formal-v1/class-summary.csv
- artifacts/analysis/formal-v1/paired-results.csv
- artifacts/formal-benchmark/summary.json

Use only frozen v1 results.

## V1 Scope

Clearly define v1 as a scheduling experiment comparing:

- baseline
- short_prompt
- aged_short_prompt

The v1 workload is the frozen formal-mixed-v1 workload.

Do not introduce or discuss new experimental results from a v2 workload.

## Root README

Update README.md carefully.

Preserve useful upstream nano-vLLM information rather than deleting it.

Add a clear scheduling-lab section near the top explaining:

- project objective
- what was changed
- three scheduling policies
- experimental setup
- headline findings
- repository structure
- reproduction entry point
- link to detailed v1 report

Clearly distinguish this project work from upstream nano-vLLM.

Do not claim ownership of upstream nano-vLLM.

## Headline Results

Use the frozen ANALYSIS-001 results.

Present the main findings accurately:

- short requests receive substantially lower TTFT under short-oriented policies
- medium requests also improve
- long requests experience materially higher waiting/TTFT
- throughput remains approximately unchanged
- overall E2E effects are small and not robust in sensitivity analysis
- aged_short_prompt did not materially alter observed first-selection order
  relative to short_prompt in this frozen workload

Do not say one policy is universally better.

Do not claim aging is generally ineffective.

State that aging was not strongly activated by the frozen workload.

## Core Algorithm Explanation

Explain the policies concisely.

baseline:

candidate = waiting head

short_prompt:

argmin(prompt_tokens)

aged_short_prompt:

argmin(prompt_tokens - 320 * age_seconds)

where age is time since first scheduler enqueue and is preserved across
preemption/requeue.

Explain:

- O(n) candidate selection
- stable tie-breaking
- existing KV-cache/resource checks remain unchanged
- running/decode scheduling remains unchanged

## Results Table

Include a concise table using frozen v1 class-level means for at least:

- TTFT
- queue wait
- E2E

for:

- baseline
- short_prompt
- aged_short_prompt

Include short, medium, and long classes.

Also summarize paired effects in prose.

Do not manually invent or approximate values when exact frozen values exist.

## Figures

Embed or link the existing frozen analysis figures where appropriate:

- TTFT by class
- queue wait by class
- long-request fairness
- paired TTFT change

Do not regenerate results unless needed only for file-format presentation.

Do not alter the underlying analysis data.

## Detailed V1 Report

Create:

docs/v1-report.md

Structure it approximately as:

1. Motivation
2. System architecture
3. Baseline scheduler
4. short_prompt design
5. aged_short_prompt design
6. Experimental protocol
7. Reproducibility controls
8. Formal results
9. Paired analysis
10. Long-request fairness
11. Aging interpretation
12. Throughput
13. Timing anomaly and sensitivity analysis
14. Limitations
15. Main conclusions
16. Future work

Separate:

- measured facts
- mathematical interpretation
- limitations
- future hypotheses

## Reproduction Guide

Create:

docs/reproduce-v1.md

Document the existing workflow required to reproduce v1, including:

- environment assumptions
- WSL/Linux setup at a high level
- Python environment
- validated model
- formal trace locations
- benchmark manifest
- dry-run validation
- formal benchmark command
- aggregation command
- offline analysis command
- expected artifact locations

Use commands that actually exist in the repository.

Do not invent commands.

Do not require users to regenerate frozen raw artifacts merely to inspect the
existing results.

## Repository Map

Provide a concise map for:

- nanovllm/
- scripts/
- workloads/
- tests/
- docs/
- artifacts/formal-benchmark/
- artifacts/analysis/formal-v1/

Explain what is source, input, raw measurement, and derived analysis.

## Experimental Integrity

Document that v1 used:

- 3 policies
- 3 frozen trace seeds
- 5 repetitions
- 45 formal runs
- 60 requests per run
- 2700 measured requests total
- paired (seed, repetition) comparisons
- precomputed rotated policy order
- frozen trace hashes
- immutable raw formal artifacts

Mention that all 45 formal runs completed successfully.

## Timing Anomaly

Document the preserved anomalous baseline run:

- large UTC-wall vs monotonic-observation discrepancy
- cause was not established by artifacts
- primary analysis retains it
- sensitivity analysis excludes its paired block
- core short-vs-long trade-off remains
- small overall E2E direction is not robust

Do not speculate about the cause.

## Limitations

Explicitly include:

- single laptop RTX 4050 environment
- one model size/model configuration
- synthetic frozen workload
- limited concurrency/load regime
- no sustained-arrival starvation workload in v1
- aged policy was not strongly activated by observed first-selection order
- findings should not be generalized to all LLM serving workloads

## Resume / Interview Summary

Add a concise section to docs/v1-report.md describing the project in
engineering terms, suitable as source material for a resume or interview.

It should emphasize:

- scheduler architecture analysis
- policy/mechanism separation
- reproducible workload/replay infrastructure
- telemetry
- paired benchmark design
- latency/fairness trade-off analysis

Do not exaggerate performance claims.

## No V2 Work

Do not:

- create a new workload
- retune aging
- implement a new scheduler
- rerun formal measurements
- modify frozen raw data
- modify scheduling source
- modify dependencies

Future sustained-arrival aging experiments may be mentioned only as future
work.

## Validation

Run:

git diff --check
git status --short

Check all relative README/report links.

Confirm no scheduling source, formal trace, or raw benchmark artifact changed.

## PROJECT_STATE

Update PROJECT_STATE.md with:

- FINAL-001 completion
- v1 documentation paths
- v1 status as complete pending final repository audit/tag
- recommended next task: FINAL-002 release audit

## Acceptance Criteria

- README explains the project clearly
- upstream nano-vLLM attribution is preserved
- exact frozen findings are presented accurately
- detailed v1 report exists
- reproduction guide exists
- limitations are explicit
- anomaly handling is documented
- figures/results are linked correctly
- raw data is unchanged
- scheduler code is unchanged
- formal traces are unchanged
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- README changes
- v1 report path
- reproduction guide path
- headline results included
- figures linked
- limitations documented
- anomaly documentation
- files modified
- validation results
- recommended final release step
