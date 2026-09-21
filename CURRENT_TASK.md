# CURRENT_TASK.md

## Task ID

FINAL-002

## Title

Perform the final scheduling-lab v1 release audit.

## Goal

Audit the completed scheduling-lab v1 repository before freezing the release.

Do not modify scheduling algorithms, benchmark data, traces, dependencies,
aging parameters, or experimental results.

Only make a documentation correction if a real release-blocking problem is
found.

## Required Reads

Read:

- AGENTS.md
- PROJECT_STATE.md
- README.md
- docs/v1-report.md
- docs/reproduce-v1.md
- docs/architecture.md
- docs/scheduling-policy-design.md
- docs/aging-policy-design.md
- docs/benchmark-protocol.md
- artifacts/analysis/formal-v1/report.md
- artifacts/analysis/formal-v1/analysis-summary.json
- artifacts/analysis/formal-v1/class-summary.csv
- artifacts/analysis/formal-v1/paired-results.csv
- artifacts/formal-benchmark/manifest.json
- artifacts/formal-benchmark/summary.json
- artifacts/formal-benchmark/validation.json

## Repository Audit

Verify the repository contains the expected v1 components:

- scheduling policy implementation
- telemetry
- reproducible traces
- replay infrastructure
- benchmark orchestrator
- formal benchmark artifacts
- offline analysis
- README
- v1 report
- reproduction guide

## Git Audit

Record:

- current branch
- current HEAD
- upstream commit
- git status
- recent commit history

The final repository should have no unintended working-tree changes.

Check that no generated virtual environment, model weights, caches, or other
large local-only files are accidentally tracked.

## Scheduler Audit

Verify the released scheduler still supports exactly:

- baseline
- short_prompt
- aged_short_prompt

Confirm:

- baseline remains the default
- short_prompt uses prompt length
- aged_short_prompt uses the frozen 320 tokens/second aging rate
- stable tie behavior remains documented
- resource checks are unchanged
- running/decode behavior is unchanged

Do not modify the implementation.

## Frozen Experiment Audit

Verify the documented formal experiment still matches the archived artifacts:

- 3 policies
- 3 trace seeds
- 5 repetitions
- 45 runs
- 60 requests per run
- 2700 measured requests
- 45/45 successful runs
- 2700/2700 completed requests
- paired comparison by seed and repetition

Verify formal trace hashes and manifest integrity.

## Result Audit

Cross-check README.md and docs/v1-report.md against frozen analysis outputs.

Verify all reported numerical results come from existing analysis artifacts.

Specifically confirm that the documentation does not overclaim:

- short/medium TTFT improvement
- long-request fairness cost
- approximately unchanged throughput
- small/non-robust overall E2E differences
- aged_short_prompt did not materially change observed first-selection order
  under formal-mixed-v1

Do not describe aged_short_prompt as generally ineffective.

## Anomaly Audit

Verify the timing anomaly is documented consistently:

- anomalous baseline run is preserved
- cause remains unestablished
- primary analysis retains it
- sensitivity analysis excludes its paired block
- core short-vs-long trade-off remains
- small overall E2E result is sensitive

Do not speculate about the cause.

## Link Audit

Verify all local links in:

- README.md
- docs/v1-report.md
- docs/reproduce-v1.md

Resolve correctly.

Verify referenced figures exist.

## Reproduction Audit

Check every command in docs/reproduce-v1.md against actual repository scripts.

Confirm:

- script names exist
- command-line options exist
- referenced workload paths exist
- referenced manifest paths exist
- output paths are accurate

Do not run the full 45-run benchmark again.

Dry-run or CPU-only checks are allowed.

## Test Audit

Run the complete CPU test suite.

Run any lightweight existing validation that does not create new formal
measurements.

Do not rerun the formal GPU benchmark.

Record exact pass counts.

## Raw Artifact Integrity

Verify analysis and documentation work did not modify frozen raw benchmark
records.

Do not rewrite raw benchmark artifacts.

## Release Summary

Create:

docs/v1-release-summary.md

Keep it concise.

Include:

- release scope
- implementation summary
- experiment size
- headline findings
- main fairness trade-off
- important limitation
- timing anomaly note
- reproduction entry point
- frozen commit information

Do not introduce new experimental claims.

## Version Recommendation

Recommend a Git tag for this frozen project version.

Preferred tag:

scheduling-lab-v1

Do not create the tag in this task.

## Validation

Run:

git diff --check
git status --short

## PROJECT_STATE

Update PROJECT_STATE.md with:

- FINAL-002 completion
- release audit result
- test result
- proposed release tag
- v1 status

## Acceptance Criteria

- repository structure is complete
- source and frozen artifacts are internally consistent
- reported results match frozen analysis
- reproduction commands are valid
- documentation links work
- CPU tests pass
- raw formal artifacts remain unchanged
- no experimental parameters changed
- release summary exists
- no scheduling behavior changed
- git diff --check passes

Do not create a Git commit.
Do not create a Git tag.

## Completion Report

Report:

- current HEAD
- repository audit result
- scheduler audit result
- frozen experiment validation
- result/documentation validation
- anomaly validation
- reproduction validation
- CPU test results
- raw-artifact integrity result
- files modified
- proposed Git tag
- release blockers, if any
