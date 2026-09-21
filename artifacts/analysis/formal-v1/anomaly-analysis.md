# Timing anomaly: seed303-rep4-baseline

The frozen primary dataset retains this completed run. The sensitivity view excludes the entire seed303-rep4 block to preserve pairing.

- UTC orchestrator duration: 615.544 s.
- Runner metadata UTC duration: 610.552 s.
- Monotonic observation end: 21.875 s.
- Request release range: 0.000–4.755 s; finish range: 0.411–21.872 s.
- Progress snapshots: 60; largest adjacent monotonic observation gap: 1.472 s.
- Runner log: 2935 bytes; traceback present: False; error marker present: False.
- Outcome: 60/60 completed, lifecycle invariants passed.

The UTC and monotonic clocks disagree substantially during this run. The artifacts do not establish whether host suspension, clock behavior, or another cause produced the discrepancy. No request timestamp or measured latency was edited.

## Comparison to other seed303 baseline repetitions

| Run-mean metric | Anomalous run (ms) | Other four runs, range (ms) |
| --- | ---: | ---: |
| ttft_ms | 54.025 | 82.615–97.183 |
| queue_wait_ms | 23.121 | 46.167–58.906 |
| e2e_latency_ms | 7486.925 | 8899.345–9516.186 |
