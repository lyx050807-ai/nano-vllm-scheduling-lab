# ANALYSIS-001: frozen formal-mixed-v1 benchmark

## Measured facts and comparison method

All 45 planned runs succeeded. Each of the 15 `(trace_seed, repeat_index)` blocks contains baseline, short_prompt and aged_short_prompt on the same trace IDs and hashes. Every run completed 60/60 requests, giving 2,700 completed measured requests. The analysis re-read all request records and run metadata, verified release-origin metric formulas, and cross-checked each run/class mean and median against the frozen aggregation output. Input SHA256 values are in `input-hashes.json`; the analysis script verified those bytes again after writing its outputs.

The paired unit is one seed/repetition block, **not one request**. Negative candidate-minus-reference latency differences mean lower latency. The table below gives the mean of 15 paired differences in run-level **means**, in milliseconds. `paired-results.csv` also retains every paired absolute and percentage difference for run-level means and medians, plus long-class p90/p95/max. `class-summary.csv` separates the 15-run distribution of run means/medians from pooled request-level mean, median, sample SD, min, max, and nearest-rank p90/p95. Pooled requests are descriptive and are not used as independent policy replications.

| Class | Comparison | Δ TTFT | Δ queue wait | Δ E2E |
| --- | --- | ---: | ---: | ---: |
| Overall | short_prompt − baseline | −1.656 | −2.096 | +14.165 |
| Overall | aged_short_prompt − baseline | −3.166 | −3.263 | +67.512 |
| Short | short_prompt − baseline | −22.848 | −23.475 | −183.180 |
| Short | aged_short_prompt − baseline | −25.959 | −26.603 | −133.399 |
| Medium | short_prompt − baseline | −13.489 | −14.750 | −7.475 |
| Medium | aged_short_prompt − baseline | −15.597 | −16.111 | +51.062 |
| Long | short_prompt − baseline | +31.370 | +31.937 | +233.150 |
| Long | aged_short_prompt − baseline | +32.058 | +32.924 | +284.873 |

For short requests, TTFT decreased in 14/15 blocks for each candidate; mean paired percentage changes were −21.2% for short_prompt and −25.9% for aged_short_prompt. Medium TTFT decreased in 13/15 and 11/15 blocks respectively. Long TTFT increased in 13/15 and 14/15 blocks, with mean paired percentage changes of +43.3% and +41.5%. Long queue wait similarly increased in 13/15 and 14/15 blocks. Thus the short/medium first-token gains coincide with a long-request waiting penalty in this workload. E2E differences are less consistent across blocks; they should not be read as a stable throughput or completion advantage.

The exploratory 95% percentile bootstrap intervals for mean paired short TTFT change were [−37.0, −8.4] ms (short_prompt) and [−41.4, −12.9] ms (aged_short_prompt). For long TTFT they were [+13.9, +45.9] and [+21.2, +41.5] ms. These resample 15 paired blocks 10,000 times with a fixed seed. The three traces recur across repetitions, so the intervals are descriptive and should not be treated as a formal independent-seed significance test. No p-values or superiority claim are made.

## Long-request fairness

All 300 long requests per policy completed. The prespecified near-starvation flag is initial queue wait **>10,000 ms** or a long request unselected/unfinished by cutoff; its count is zero for every policy. Additional fixed thresholds are descriptive and were not chosen from policy outcomes.

| Policy | Mean long wait | Median | p90 | p95 | Maximum | >100 ms | >250 ms | >500 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 53.917 | 27.917 | 60.770 | 111.046 | 1073.642 | 16/300 | 12/300 | 5/300 |
| short_prompt | 85.854 | 52.260 | 61.047 | 475.568 | 1057.569 | 18/300 | 18/300 | 15/300 |
| aged_short_prompt | 86.841 | 52.065 | 60.673 | 622.061 | 1095.859 | 20/300 | 20/300 | 16/300 |

Units for wait columns are milliseconds; p90/p95 are nearest-rank percentiles of 300 pooled long requests. The worst long wait was 1073.642 ms for baseline (`formal-202-000060`, seed202/rep0), 1057.569 ms for short_prompt (`formal-303-000058`, seed303/rep4), and 1095.859 ms for aged_short_prompt (`formal-303-000058`, seed303/rep0). The corresponding TTFT/E2E and all 900 long-request first-selection and finish ranks are in `analysis-summary.json` and `long-request-orders.csv`.

Across the 15 paired blocks, mean differences in each run's long-wait p95 were +71.814 ms (short_prompt − baseline) and +96.756 ms (aged_short_prompt − baseline); mean differences in each run's maximum were +270.934 and +267.872 ms. These tail effects vary widely by block. A run has only 20 long requests, so nearest-rank p95 is its 19th value and should not carry a strong standalone tail claim. Paired long-request TTFT and E2E tail differences are also retained in `paired-results.csv`.

The protocol's median long/short queue-wait ratio is also retained per run. Its median across runs is 1.02 for baseline, 1627 for short_prompt, and 1573 for aged_short_prompt. The last two ratios are numerically unstable because their median short-request wait is about **0.03 ms**; absolute wait differences and threshold counts are more interpretable here. Long TTFT and E2E pooled distributions, paired mean/median changes, and long/short TTFT ratios are in `analysis-summary.json`.

## Aging effectiveness and mathematical interpretation

The observable first-selection order of all 60 request IDs was identical between short_prompt and aged_short_prompt in **15/15 blocks**: zero position changes and zero discordant request pairs. Direct aged-minus-short_prompt mean paired changes were −1.510 ms overall TTFT, +0.688 ms long TTFT, and +0.987 ms long queue wait; their exploratory paired bootstrap intervals include zero. There is no evidence in these records that aging materially improved long-request initial waiting under the frozen workload.

For a common selection time, `score_i = L_i − α(now − first_enqueue_i) = (L_i + α·first_enqueue_i) − α·now`. The common `−α·now` cancels when ranking candidates. Relative priority therefore depends on original prompt length and first-enqueue time; merely waiting together longer does not reverse their ordering. The intended 0.2/0.3/0.5 s crossovers require a sufficient first-enqueue gap between an older medium/long and a later shorter request. As an **admission-time proxy**, among older requests still unselected at a younger request's admission, the largest observed gap was under 0.00004 s. No initial-selection overlap reached any nominal crossover threshold. The trace's three-request arrival groups and rapid initial selection explain why a crossover opportunity was not observable.

Exact scheduler first-enqueue timestamps, candidate sets, decisions, and any later preemption/requeue choices were not logged. Admission is only a proxy, and first-selection order cannot prove that every internal aged-policy decision matched short_prompt. The 15 runs did show different timing values despite identical first-selection permutations; these are not evidence of a different candidate order. The frozen 320 tokens/s rate remains unchanged.

## Throughput and output length

Mean full-run throughput was 2.827, 2.854 and 2.826 completed requests/s for baseline, short_prompt and aged_short_prompt. Mean paired throughput changes were +0.0272 requests/s (short_prompt − baseline), −0.0002 (aged_short_prompt − baseline) and −0.0274 (aged_short_prompt − short_prompt), with mixed directions across blocks. All 900 requests per policy produced 16 output tokens and all completed. These policies chiefly redistributed initial waiting latency in this fixed workload; no material throughput separation is established by these 15 blocks.

## Timing anomaly and sensitivity

`formal-mixed-v1-seed303-rep4-baseline` took 615.544 s by orchestrator UTC timestamps, while runner metadata recorded 21.875 s of monotonic observation. Request release and finish timestamps occupy 0.000–4.755 s and 0.411–21.872 s respectively; all 60 progress snapshots advance monotonically, with a largest adjacent observation gap of 1.472 s. The runner log has a completed summary and no traceback or error line. This run's mean TTFT/queue wait/E2E (54.025/23.121/7486.925 ms) is lower than the other four seed303 baseline repetitions (TTFT 82.615–97.183, wait 46.167–58.906, E2E 8899.345–9516.186 ms). The records establish a wall/monotonic clock discrepancy and unusual latency values, but not its cause. Details are in `anomaly-analysis.md`.

The **primary** results above keep the run. Sensitivity removes the entire seed303/rep4 paired block, leaving 14 matched blocks; it never edits or replaces raw data.

| Mean paired effect | Primary, 15 blocks | Sensitivity, 14 blocks |
| --- | ---: | ---: |
| short_prompt − baseline, overall TTFT (ms) | −1.656 | −5.362 |
| aged_short_prompt − baseline, overall TTFT (ms) | −3.166 | −5.202 |
| short_prompt − baseline, overall E2E (ms) | +14.165 | −115.224 |
| aged_short_prompt − baseline, overall E2E (ms) | +67.512 | −38.370 |
| short_prompt − baseline, short queue wait (ms) | −23.475 | −27.527 |
| aged_short_prompt − baseline, short queue wait (ms) | −26.603 | −28.601 |
| short_prompt − baseline, long queue wait (ms) | +31.937 | +28.890 |
| aged_short_prompt − baseline, long queue wait (ms) | +32.924 | +31.432 |

The short-versus-long initial-wait trade-off persists in sensitivity. The sign of the small overall E2E mean difference does not. All sensitivity paired metrics, including aged_short_prompt versus short_prompt, are in `analysis-summary.json`.

## Exploratory implications and limits

The fixed workload produced no observable aged-policy first-selection reversal, so it cannot establish aging's benefit under a sustained stream of later short requests. A later separately versioned experiment could test that workload; it must not retune this frozen dataset or its aging parameter. The current analysis is limited to one model, one GPU, three class-order seeds, five repeated runs per seed, and one offered-load level. Repeated traces and host variability limit causal precision. Pooled request tails are valuable diagnostics but do not supply 300 independent experimental replications per policy.

Figures: `figures/ttft-by-class.svg`, `figures/queue-wait-by-class.svg`, `figures/e2e-by-class.svg`, `figures/paired-ttft-change.svg`, and `figures/long-queue-fairness.svg`. The class figures show means of run means with one run-level SD; paired dots each represent one seed/repetition block. The long-request cumulative curve pools requests for descriptive display only.
