# Scheduling lab v1 release audit

FINAL-002 audit, 2026-09-21. The v1 repository is ready for a release tag; this task did not create one.

This student single-GPU study extends pinned nano-vLLM with deterministic mixed-length traces, timed arrival replay, optional request/token telemetry, and three waiting-candidate policies: `baseline`, `short_prompt`, and `aged_short_prompt`. The default baseline retains upstream waiting-head behavior. The short-prompt policy uses original prompt length; aging uses first-enqueue request age at the frozen rate of 320 tokens/s. Resource checks, running/decode, KV-cache, model execution, and sampling stay outside policy selection.

The frozen `formal-mixed-v1` experiment used three 60-request traces (seeds 101, 202, 303), five repetitions per seed and policy, and 45 successful runs. All 2,700 request records completed. Comparisons use 15 matched seed/repetition blocks. The archived trace hashes, manifest, run records, and 188 raw-input SHA256 entries match; the full 71-test CPU suite passes.

Compared with baseline, mean paired short-request TTFT changed by −22.848 ms for `short_prompt` and −25.959 ms for `aged_short_prompt`. Long-request TTFT changed by +31.370 and +32.058 ms, with long initial queue wait also increasing by +31.937 and +32.924 ms. All long requests completed, and the fixed >10 s near-starvation count was zero. Mean throughput stayed near 2.8 completed requests/s; small overall E2E differences were sensitive to one timing anomaly. The two non-baseline policies had identical observed first-selection order in all 15 blocks. This workload does not establish whether aging helps under sustained later short arrivals.

The anomalous `seed303-rep4-baseline` run remains in the primary dataset. Its UTC duration and monotonic observation disagree; the cause is unestablished. Sensitivity excludes the entire matched three-policy block, preserving the short-versus-long initial-wait trade-off while reversing the sign of small overall E2E mean differences. The results are limited to one model, one laptop GPU, one offered-load profile, and three trace seeds.

Start with [the reproduction guide](reproduce-v1.md) to inspect archived data or plan a separate measurement; [the detailed report](v1-report.md) and [analysis report](../artifacts/analysis/formal-v1/report.md) give the evidence and interpretation. The current release-audit HEAD is `c27a45c8ade1c0694892bef140f8e1db64f349d2`; measured runs executed project commit `f582364e1248a3b1f9ec241c07c4895eac75783f` on upstream nano-vLLM commit `bb823b3e06983d71485a8e1f23715ebd87d98ef8`. The manifest retains its earlier plan-creation commit separately. Recommended tag after review: `scheduling-lab-v1`.

The pre-run protocol text describes a timestamp/random run-ID suffix, while the archived manifest uses unique deterministic profile/seed/repetition/policy IDs. This naming difference did not change run order, pairing, measurements, or artifact uniqueness.
