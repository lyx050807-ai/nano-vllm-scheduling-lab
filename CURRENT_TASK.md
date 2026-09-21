# CURRENT_TASK.md

## Task ID

ANALYSIS-001

## Title

Analyze the frozen formal scheduling benchmark.

## Goal

Perform offline analysis of the completed frozen 45-run benchmark.

Do not modify scheduling policies, traces, benchmark measurements, or raw run
artifacts.

The analysis must preserve the paired structure of the experiment.

## Required Reads

Read:

- AGENTS.md
- PROJECT_STATE.md
- docs/benchmark-protocol.md
- docs/scheduling-policy-design.md
- docs/aging-policy-design.md
- scripts/aggregate_formal.py
- artifacts/formal-benchmark/manifest.json
- all frozen formal benchmark run metadata and request records

## Data Integrity

Treat the completed BENCH-004 artifacts as immutable raw data.

Verify:

- 45/45 run records exist
- 15 seed/repetition paired blocks exist
- each block contains baseline, short_prompt, aged_short_prompt
- all successful runs contain 60/60 requests
- request IDs and trace hashes match within each paired block

Do not rewrite raw artifacts.

## Primary Analysis

For each policy compute descriptive statistics for:

- TTFT
- queue_wait
- E2E latency

Analyze:

- overall
- short
- medium
- long

Report at least:

- mean
- median
- standard deviation
- minimum
- maximum
- p90/p95 where supported by the pooled request-level data

Keep run-level and request-level summaries distinct.

## Paired Policy Comparison

For every (trace_seed, repeat_index) block compute paired deltas:

short_prompt - baseline

aged_short_prompt - baseline

aged_short_prompt - short_prompt

For TTFT, queue_wait, and E2E.

Report:

- absolute paired differences
- percentage paired differences
- mean and median paired differences
- direction consistency across the 15 pairs

Do not infer superiority from aggregate means alone.

## Prompt-Class Analysis

Perform paired analysis separately for:

- short
- medium
- long

Quantify the latency/fairness trade-off.

Explicitly examine whether improvements for short/medium correspond to
degradation for long requests.

## Fairness Analysis

For long requests analyze:

- mean queue wait
- median queue wait
- p90/p95 queue wait
- maximum queue wait
- TTFT
- E2E
- worst observed requests

Define a transparent near-starvation diagnostic using the frozen data.

Do not choose a threshold to make one policy look favorable.

If possible, report the count/fraction of long requests exceeding fixed
queue-wait thresholds such as:

- 100 ms
- 250 ms
- 500 ms

These thresholds are descriptive only.

## Aging Effectiveness

Directly compare short_prompt and aged_short_prompt.

Determine:

- how often their request service/order behavior differs
- in which traces/runs differences occur
- whether aging materially changes long-request queue wait
- whether requests cross the intended 0.2 / 0.3 / 0.5 second priority
  crossover conditions

Where available, reconstruct candidate/order evidence from recorded artifacts.

If exact scheduler-decision traces are unavailable, state that limitation and
use observable service-order/timestamp differences without inventing decisions.

Explain mathematically that for:

score_i = L_i - alpha * (now - first_enqueue_i)

the common -alpha*now term cancels during a single selection, so relative
ranking depends on prompt length and first-enqueue time.

Discuss what this implies for the frozen workload.

Do not change the aging rate based on these results.

## Throughput Analysis

Compare run throughput across policies.

Determine whether the policies mainly redistribute latency or materially
change throughput.

## Timing Anomaly Investigation

Investigate the baseline run reported with approximately:

- 615.544 s UTC wall duration
- 21.875 s monotonic observation duration

Identify the run_id.

Inspect:

- request timestamps
- progress records
- runner log
- run metadata
- latency distribution relative to other baseline runs

Do not delete or replace this run.

Produce:

1. primary analysis including the run
2. sensitivity analysis excluding the anomalous run

Only exclude it from a sensitivity view; the frozen primary dataset remains
unchanged.

Do not assert a cause unless supported by artifacts.

## Statistical Analysis

Because the design is paired, use paired analysis where appropriate.

Provide confidence intervals for important paired effects if practical.

If formal significance tests are used, state:

- unit of analysis
- assumptions
- exact test
- sample size

Prefer transparent effect sizes and confidence intervals over relying only on
p-values.

Do not treat individual requests as independent replicates when the comparison
unit should be the 15 paired runs.

## Figures

Create offline figures for at least:

1. TTFT by prompt class and policy
2. queue wait by prompt class and policy
3. E2E by prompt class and policy
4. paired TTFT change vs baseline
5. long-request fairness / queue-wait comparison

Use clear labels and units.

Do not modify raw benchmark artifacts.

## Outputs

Create a dedicated directory such as:

artifacts/analysis/formal-v1/

Create:

- analysis-summary.json
- paired-results.csv
- class-summary.csv
- anomaly-analysis.md
- figures
- concise markdown analysis report

The report must distinguish:

- measured facts
- mathematical interpretation
- limitations
- exploratory implications

## Restrictions

Do not:

- modify scheduling code
- modify formal traces
- modify raw benchmark runs
- retune aging
- rerun failed or unfavorable results
- run a new policy benchmark
- overwrite formal artifacts

## Validation

Run:

git diff --check
git status --short

Source scheduling behavior must remain unchanged.

## PROJECT_STATE

Update PROJECT_STATE.md with:

- ANALYSIS-001 status
- main descriptive findings
- anomaly status
- artifact paths
- recommended next task

## Acceptance Criteria

- all 15 paired blocks are analyzed
- overall and class-specific results are reported
- paired deltas are computed
- long-request fairness is analyzed
- aging effectiveness is directly examined
- throughput is analyzed
- timing anomaly is investigated
- sensitivity analysis is provided
- figures are produced
- raw formal artifacts remain unchanged
- no scheduling code changes
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- dataset validation
- main overall findings
- short/medium/long findings
- paired effect sizes
- long-request fairness findings
- aging effectiveness
- throughput findings
- anomaly investigation
- sensitivity-analysis result
- output files
- limitations
- recommended next step
