# Reproducing and inspecting scheduling-lab v1

This guide covers the completed **formal-mixed-v1** experiment. It separates
reading the archived results from intentionally collecting a *new*
45-run measurement. The existing [formal manifest](../artifacts/formal-benchmark/manifest.json),
[raw run directories](../artifacts/formal-benchmark/runs),
[frozen aggregate](../artifacts/formal-benchmark/summary.json), and
[paired analysis](../artifacts/analysis/formal-v1/report.md) are already
present; viewing them does **not** require a model download, CUDA, or a rerun.
The [v1 report](v1-report.md) explains the measured findings.

## 1. What must match for an independent measurement

Run from the Linux filesystem in WSL2/Ubuntu 24.04 or a compatible NVIDIA
Linux environment. The recorded machine had one 6141 MiB RTX 4050 Laptop GPU,
Python 3.12.3, torch 2.6.0+cu124, Triton 3.2.0, FlashAttention 2.7.4.post1,
and the locally editable nano-vLLM checkout. The exact installed environment
and validation are documented in [PyTorch evidence](../artifacts/environment/pytorch-gpu-info.txt),
[runtime dependencies](../artifacts/environment/runtime-deps-info.txt),
[FlashAttention evidence](../artifacts/environment/flash-attn-info.txt), and
[local editable install evidence](../artifacts/environment/nanovllm-install-info.txt).
The project declares bounds rather than a complete lockfile; use these
records to recreate the validated stack instead of allowing an unconstrained
upgrade. No dependency installation is needed to inspect archived outputs.

The pinned model is `Qwen/Qwen3-0.6B` revision
`c1899de289a04d12100db370d81485cdf75e47ca`, present at
`models/Qwen3-0.6B`. Its validated weight and tokenizer hashes are in
[model-info.txt](../artifacts/environment/model-info.txt). The original
execution used project source commit
`f582364e1248a3b1f9ec241c07c4895eac75783f` and upstream nano-vLLM
commit `bb823b3e06983d71485a8e1f23715ebd87d98ef8`, recorded in
[preflight.json](../artifacts/formal-benchmark/preflight.json). The manifest
was created at an earlier project commit, preserved in its provenance;
compare the **executed** commit and source hashes for source equivalence.
For a new measurement, use a separate clean checkout and a unique output
directory. Later documentation commits do not change the v1 scheduler, but
they do change the Git commit recorded in a newly created manifest.

The three frozen JSONL traces and `.meta.json` sidecars are in
[`workloads/`](../workloads). Their exact SHA256 pairs are registered in the
[benchmark protocol](benchmark-protocol.md) and
[preflight.json](../artifacts/formal-benchmark/preflight.json):

| Seed | Trace SHA256 | Sidecar SHA256 |
| --- | --- | --- |
| 101 | `ff3acfd57a153030e76d06af491fed20bd1498db7e12580db345c8bb1ff92ac8` | `fb298e8ba8019d86e54c62487eb5906e0a59d9889ca5ca73881560f53e0b1476` |
| 202 | `e3c82a96d5b7295b7e98d4d4884476ddd9cc5ee1701831f4d5e63e8872e94078` | `8603718474005a5dc3f18fac2b76cd4e37d23252dd19ea124c5f34734d95ebfc` |
| 303 | `8721930601de3f96d23287cef9038a0967f653133987a154ca18ae8e5b4d6866` | `af6d5affaf40cbd7e72a0961d37d10dcdbe59664ce8a563e954ec844862d4526` |

Each trace has 60 requests (20 each of 32/96/192 prompt tokens), with three
planned arrivals every 0.25 s. The frozen manifest fixes baseline,
short_prompt, and aged_short_prompt at 320 tokens/s, five repetitions per
seed/policy, the rotated 45-run order, engine/generation settings, one
telemetry-disabled warm-up, 90 s coordinator cutoff, 150 s process watchdog,
and 30 s inter-process cooldown. Do not regenerate a trace or change this
profile to compare with the published v1 values.

## 2. Inspect the archived results without measuring again

From the repository root in WSL/Linux, files can be read directly:

```bash
cd /home/luoyuxuan/projects/nano-vllm-scheduling-lab
git status --short
.venv/bin/python scripts/formal_benchmark.py \
  --output-root artifacts/formal-benchmark --dry-run
```

Use your own Linux checkout path in place of the `cd` path above when it
differs from the recorded machine.

With the completed manifest, `--dry-run` validates the frozen identities and
prints 45 entries with **zero pending**; it does not launch a GPU run or
rewrite the existing manifest. The JSON output is verbose. The archived
[summary.json](../artifacts/formal-benchmark/summary.json) already contains
all 45 per-run summaries and 15 `(seed, repetition)` paired keys.
The [class CSV](../artifacts/analysis/formal-v1/class-summary.csv),
[paired CSV](../artifacts/analysis/formal-v1/paired-results.csv),
[analysis JSON](../artifacts/analysis/formal-v1/analysis-summary.json), and
[figures](../artifacts/analysis/formal-v1/figures) can be opened without
Python or CUDA. [input-hashes.json](../artifacts/analysis/formal-v1/input-hashes.json)
records the raw files consumed by offline analysis.

## 3. Validate the existing Python/GPU environment before a new run

These commands check the already installed environment; they do not install
or change packages:

```bash
cd /home/luoyuxuan/projects/nano-vllm-scheduling-lab
.venv/bin/python --version
.venv/bin/python -m pip check
nvidia-smi
.venv/bin/python -c 'import torch, triton, flash_attn; print(torch.__version__, triton.__version__, flash_attn.__version__, torch.cuda.is_available())'
```

Check that `models/Qwen3-0.6B` contains the pinned snapshot and that the
frozen traces match the hashes above. The formal orchestrator validates trace
identity again when loading a manifest. A clean worktree and a usable CUDA
GPU are preflight requirements for a new measured run. The existing
`CURRENT_TASK.md` may differ from a commit while a task is open; resolve that
in the **separate reproduction checkout** before launching measurements.

## 4. Plan and execute a separate 45-run reproduction

The commands below exist in this repository. They are **not required** to
inspect published results and should only be run in a prepared, clean
measurement checkout with the pinned model and validated dependencies.
Choose a genuinely unused output root **outside the checkout**, so its new
manifest does not dirty the source worktree. `--dry-run` creates a manifest
if that root has none, and `--execute` then uses its precomputed order. Both
commands keep the archived `artifacts/formal-benchmark/` untouched.

```bash
cd /home/luoyuxuan/projects/nano-vllm-scheduling-lab
git status --short
.venv/bin/python scripts/formal_benchmark.py \
  --output-root ../formal-benchmark-reproduction-001 --dry-run
.venv/bin/python scripts/formal_benchmark.py \
  --output-root ../formal-benchmark-reproduction-001 --execute
```

The orchestrator creates one exclusive directory per run, preserves
`requests.jsonl`, `requests.meta.json`, `progress.jsonl`, and `runner.log`,
and checkpoints outcomes in its manifest. It does not silently retry or
overwrite successful results. A running/interrupted entry requires inspection
of child processes and partial artifacts before any resume; follow the
[frozen failure rules](benchmark-protocol.md). A new measurement has its own
recorded project commit and is not a replacement for the archived v1 run.

## 5. Aggregate and analyze

The frozen aggregation utility reads any completed formal manifest and
requires an **unused** output filename. For the independent reproduction
above, run:

```bash
.venv/bin/python scripts/aggregate_formal.py \
  ../formal-benchmark-reproduction-001/manifest.json \
  --output ../formal-benchmark-reproduction-001/summary.json
```

The published `artifacts/formal-benchmark/summary.json` already exists; do
not overwrite it. To reproduce the **published offline analysis** from the
archived raw root, run the existing standard-library-only script:

```bash
.venv/bin/python artifacts/analysis/formal-v1/analyze.py
```

That script is intentionally bound to the archived
`artifacts/formal-benchmark/` input. It validates 45 runs, 15 paired blocks,
request IDs and hashes, recomputes descriptive/paired statistics, checks the
frozen aggregate, writes derived CSV/JSON/SVG files under
`artifacts/analysis/formal-v1/`, and confirms the raw input hashes again.
Running it is unnecessary merely to read the committed report or figures;
it does not analyze `../formal-benchmark-reproduction-001/` without a
separately scoped adaptation.

## 6. Artifact map and interpretation boundaries

| Path | What it contains |
| --- | --- |
| `nanovllm/` | Upstream-based engine, scoped waiting policy, optional telemetry (source) |
| `scripts/` | Trace/replay utilities, frozen benchmark orchestrator and aggregation (source) |
| `workloads/` | Frozen formal JSONL inputs and sidecars; development trace is separate (input) |
| `tests/` | CPU regression/validation tests (source) |
| `docs/` | Architecture, design/protocol, this guide, detailed v1 report (documentation) |
| `artifacts/formal-benchmark/manifest.json` | Frozen order, identities, parameters, terminal outcomes (raw record) |
| `artifacts/formal-benchmark/runs/` | 45 request/progress/log/metadata packages (raw measurements) |
| `artifacts/formal-benchmark/summary.json` | Frozen per-run aggregation and paired-key index (derived from raw) |
| `artifacts/analysis/formal-v1/` | Paired/class tables, anomaly sensitivity, report, and figures (derived) |

TTFT and E2E use actual replay release as their latency origin; queue wait
starts at engine admission. Compare policies by the 15 matched
`(trace_seed, repeat_index)` run blocks, not by treating 2,700 requests as
independent policy trials. The anomalous seed303/rep4/baseline run remains in
the primary data; the published sensitivity view removes its **whole paired
block**, not just that baseline row. The [v1 report](v1-report.md) gives the
measured trade-offs and limits on generalization.
