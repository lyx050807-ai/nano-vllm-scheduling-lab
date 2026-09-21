<p align="center">
<img width="300" src="assets/logo.png">
</p>

<p align="center">
<a href="https://trendshift.io/repositories/15323" target="_blank"><img src="https://trendshift.io/api/badge/repositories/15323" alt="GeeeekExplorer%2Fnano-vllm | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>
</p>

# Nano-vLLM

## Scheduling lab v1

This repository extends [GeeeekExplorer/nano-vllm](https://github.com/GeeeekExplorer/nano-vllm)
for a student single-GPU study, **Lightweight LLM Scheduling and Performance
Analysis for Mixed-Length Requests**. The pinned upstream revision is recorded
in [artifacts/environment/upstream-commit.txt](artifacts/environment/upstream-commit.txt).
The inference engine, model execution, attention kernels, KV-cache manager,
chunked prefill, and sampling originate from upstream nano-vLLM. This lab adds
waiting-candidate policy selection, arrival replay, request/token telemetry,
frozen traces, tests, and paired analysis. The upstream project overview and
its separate benchmark are retained below.

The v1 question is how choosing the next **waiting** request changes latency
when 32-, 96-, and 192-token prompts arrive together. The baseline retains
upstream head-of-waiting-queue behavior, including partial prefill and
preemption effects. `short_prompt` scans waiting requests for the smallest
original prompt length. `aged_short_prompt` scans for the smallest
`prompt_tokens - 320 * age_seconds`, where age starts at first scheduler
enqueue and survives preemption/requeue. Equal scores keep current deque order.
The two scans take O(n) time; the existing resource checks, KV-cache behavior,
and running/decode scheduler are unchanged. Neither policy uses future output
length.

The frozen [formal-mixed-v1 protocol](docs/benchmark-protocol.md) uses local
Qwen3-0.6B on one 6 GB RTX 4050 Laptop GPU: three immutable 60-request traces
(seeds 101/202/303, 20 requests per prompt class), five measured repetitions,
and three policies. All **45 independent runs and 2,700 measured requests
completed**. The order was precomputed and rotated within each
`(trace_seed, repeat_index)` block. TTFT and E2E start at actual replay
release; queue wait measures admission to first scheduling.

The table shows the **mean of 15 run-level class means** in milliseconds;
these are descriptive values, not 300 independent policy replications per
class.

| Prompt class | Policy | TTFT (ms) | Queue wait (ms) | E2E (ms) |
| --- | --- | ---: | ---: | ---: |
| Short | baseline | 80.768 | 44.316 | 8522.091 |
| Short | short_prompt | 57.921 | 20.842 | 8338.912 |
| Short | aged_short_prompt | 54.809 | 17.714 | 8388.692 |
| Medium | baseline | 85.901 | 48.881 | 9766.988 |
| Medium | short_prompt | 72.412 | 34.131 | 9759.513 |
| Medium | aged_short_prompt | 70.304 | 32.770 | 9818.050 |
| Long | baseline | 92.625 | 53.917 | 8751.370 |
| Long | short_prompt | 123.995 | 85.854 | 8984.520 |
| Long | aged_short_prompt | 124.683 | 86.841 | 9036.243 |

Paired against baseline, short-request TTFT fell by 22.848 ms with
`short_prompt` and 25.959 ms with `aged_short_prompt`; long-request TTFT rose
by 31.370 and 32.058 ms. Medium TTFT also fell. Mean throughput stayed near
2.8 completed requests/s for all three policies. Overall E2E differences
were small and changed direction in the timing-anomaly sensitivity view.
The aged and non-aged policies had identical **observed first-selection order**
in all 15 paired blocks: this frozen arrival pattern did not strongly
activate the intended aging crossovers. That observation does not establish
that aging is ineffective for other workloads. No policy is universally
better on these results.

![Frozen v1 TTFT by prompt class](artifacts/analysis/formal-v1/figures/ttft-by-class.svg)

The [queue-wait figure](artifacts/analysis/formal-v1/figures/queue-wait-by-class.svg),
[paired TTFT changes](artifacts/analysis/formal-v1/figures/paired-ttft-change.svg),
and [long-request fairness figure](artifacts/analysis/formal-v1/figures/long-queue-fairness.svg)
show the trade-off. See the [detailed v1 report](docs/v1-report.md) for paired
effects, the preserved timing anomaly, and limitations; start with the
[reproduction guide](docs/reproduce-v1.md) to inspect the frozen artifacts or
plan an independent rerun.

| Path | Role |
| --- | --- |
| `nanovllm/` | Upstream engine plus the scoped waiting selector and optional telemetry |
| `scripts/` | Trace generation/validation, arrival replay, benchmark orchestration, aggregation |
| `workloads/` | Frozen formal traces and sidecars; the development trace is separate |
| `tests/` | CPU policy, replay, telemetry, and orchestration tests |
| `docs/` | Architecture, frozen designs/protocol, v1 report, reproduction guide |
| `artifacts/formal-benchmark/` | Immutable formal manifest, raw run records/logs, preflight, and frozen aggregate |
| `artifacts/analysis/formal-v1/` | Derived paired tables, report, anomaly analysis, and figures |

## Upstream nano-vLLM reference

The following overview, quick start, and RTX 4070 benchmark are retained from
upstream nano-vLLM. That benchmark is **not** a result of this scheduling lab;
use the local pinned checkout and the guide above to reproduce v1.

A lightweight vLLM implementation built from scratch.

### Key Features

* 🚀 **Fast offline inference** - Comparable inference speeds to vLLM
* 📖 **Readable codebase** - Clean implementation in ~ 1,200 lines of Python code
* ⚡ **Optimization Suite** - Prefix caching, Tensor Parallelism, Torch compilation, CUDA graph, etc.

### Installation

```bash
pip install git+https://github.com/GeeeekExplorer/nano-vllm.git
```

### Model Download

To download the model weights manually, use the following command:
```bash
huggingface-cli download --resume-download Qwen/Qwen3-0.6B \
  --local-dir ~/huggingface/Qwen3-0.6B/ \
  --local-dir-use-symlinks False
```

### Quick Start

See `example.py` for usage. The API mirrors vLLM's interface with minor differences in the `LLM.generate` method:
```python
from nanovllm import LLM, SamplingParams
llm = LLM("/YOUR/MODEL/PATH", enforce_eager=True, tensor_parallel_size=1)
sampling_params = SamplingParams(temperature=0.6, max_tokens=256)
prompts = ["Hello, Nano-vLLM."]
outputs = llm.generate(prompts, sampling_params)
outputs[0]["text"]
```

### Benchmark

See `bench.py` for benchmark.

**Test Configuration:**
- Hardware: RTX 4070 Laptop (8GB)
- Model: Qwen3-0.6B
- Total Requests: 256 sequences
- Input Length: Randomly sampled between 100–1024 tokens
- Output Length: Randomly sampled between 100–1024 tokens

**Performance Results:**
| Inference Engine | Output Tokens | Time (s) | Throughput (tokens/s) |
|----------------|-------------|----------|-----------------------|
| vLLM           | 133,966     | 98.37    | 1361.84               |
| Nano-vLLM      | 133,966     | 93.41    | 1434.13               |


### Star History

[![Star History Chart](https://api.star-history.com/svg?repos=GeeeekExplorer/nano-vllm&type=Date)](https://www.star-history.com/#GeeeekExplorer/nano-vllm&Date)
