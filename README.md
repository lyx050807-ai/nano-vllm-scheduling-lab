# Lightweight LLM Scheduling and Performance Analysis for Mixed-Length Requests

An AI infrastructure study of how **waiting-request selection** changes latency and fairness when short, medium, and long prompts share one GPU. Built on [nano-vLLM](https://github.com/GeeeekExplorer/nano-vllm), it keeps upstream model execution, KV-cache management, chunked prefill, and decoding in place.

| Scheduling policies | Formal GPU runs | Measured requests | Paired blocks | Final CPU tests |
| ---: | ---: | ---: | ---: | ---: |
| **3** | **45/45 successful** | **2,700/2,700 completed** | **15** | **71/71 passed** |

**Observed trade-off:** With `short_prompt`, short-request time to first token (TTFT) fell from **80.8 to 57.9 ms**, while long-request TTFT rose from **92.6 to 124.0 ms** versus baseline. These are means of run-level class means for the frozen workload; [class data](artifacts/analysis/formal-v1/class-summary.csv) give the unrounded values. Throughput was approximately unchanged. The study concerns **latency allocation and fairness**, not raw GPU speed or a universal performance improvement. [Portfolio case study](docs/portfolio-v1.md) · [Reproduce or inspect results](docs/reproduce-v1.md) · [Detailed report](docs/v1-report.md)

## System architecture and what I built

```text
Frozen traces -> timed producer -> thread-safe admission queue
                                         |
                                         v
                              coordinator owns LLMEngine
                                         |
                          waiting-candidate policy selector
                                         |
                       upstream prefill / KV cache / decode
                                         |
                           request + token telemetry
                                         |
                               paired offline analysis
```

The lab adds [deterministic trace generation](scripts/make_formal_trace.py), [timed arrival replay](scripts/replay_trace.py) with an [engine-owning coordinator](scripts/run_replay.py), [opt-in lifecycle/token telemetry](nanovllm/telemetry.py), [CPU-testable waiting selection](nanovllm/engine/waiting_policy.py), and [formal orchestration](scripts/formal_benchmark.py) with [paired analysis](artifacts/analysis/formal-v1/report.md). Only the coordinator thread accesses `LLMEngine`; policy selection does not use future output length. The [architecture analysis](docs/architecture.md) maps the upstream boundaries.

| Policy | Choice among current waiting requests |
| --- | --- |
| `baseline` | Current deque head, preserving upstream partial-prefill and preemption behavior. |
| `short_prompt` | Smallest original prompt-token count; equal lengths keep deque order. |
| `aged_short_prompt` | Smallest `prompt_tokens - 320 × age_seconds`; age starts at first scheduler enqueue, survives preemption, and can include time spent running. |

The non-baseline selectors scan the waiting deque; the existing allocation checks and running/decode behavior remain in place. [Policy design](docs/scheduling-policy-design.md) · [Aging design](docs/aging-policy-design.md)

## Frozen experiment and results

The [formal-mixed-v1 protocol](docs/benchmark-protocol.md) fixes three 60-request traces, five repetitions per seed and policy, a rotated policy order, Qwen3-0.6B, and one 6 GB RTX 4050 Laptop GPU. All 45 runs completed; comparisons use 15 matched `(seed, repetition)` blocks. TTFT starts at actual replay release, while initial queue wait starts at engine admission. [Manifest](artifacts/formal-benchmark/manifest.json) · [Validation](artifacts/formal-benchmark/validation.json)

| Prompt class | Baseline TTFT | `short_prompt` TTFT | `aged_short_prompt` TTFT |
| --- | ---: | ---: | ---: |
| Short | 80.8 ms | 57.9 ms | 54.8 ms |
| Medium | 85.9 ms | 72.4 ms | 70.3 ms |
| Long | 92.6 ms | 124.0 ms | 124.7 ms |

Values are means of 15 run-level class means, rounded to one decimal; [class-summary.csv](artifacts/analysis/formal-v1/class-summary.csv) is the source. Against baseline, the mean paired `short_prompt` change was **−22.848 ms** for short TTFT and **+31.370 ms** for long TTFT. Its long-request initial queue wait also rose **+31.937 ms** on average across paired run means. All long requests completed, but their pooled queue-wait p95 rose from **111.046 to 475.568 ms**; pooled tails are descriptive, not independent run-level replications. [Paired results](artifacts/analysis/formal-v1/paired-results.csv) · [Fairness analysis](artifacts/analysis/formal-v1/report.md)

![TTFT by prompt class and policy](artifacts/analysis/formal-v1/figures/ttft-by-class.svg)

Mean full-run throughput was **2.827 / 2.854 / 2.826 completed requests/s** for baseline / `short_prompt` / `aged_short_prompt`; these runs do not establish a material throughput gain. Under `formal-mixed-v1`, the two candidate policies had the same **observed first-selection order in all 15 paired blocks**. That does not establish identical internal decisions or tell us whether aging helps under other arrival patterns. The [full analysis](artifacts/analysis/formal-v1/report.md) also preserves a timing anomaly in the primary data and reports a whole-block sensitivity check.

## Reproduction and deeper technical documentation

The [reproduction guide](docs/reproduce-v1.md) separates inspection of the archived results from a new GPU measurement. The [frozen manifest](artifacts/formal-benchmark/manifest.json), [per-run summaries](artifacts/formal-benchmark/summary.json), [analysis tables](artifacts/analysis/formal-v1/analysis-summary.json), and [figures](artifacts/analysis/formal-v1/figures) are already present. For implementation and study details, see the [portfolio case study](docs/portfolio-v1.md), [architecture](docs/architecture.md), [waiting-policy design](docs/scheduling-policy-design.md), [aging design](docs/aging-policy-design.md), [benchmark protocol](docs/benchmark-protocol.md), and [v1 report](docs/v1-report.md).

## Upstream nano-vLLM reference

<p align="center">
<img width="300" src="assets/logo.png">
</p>

<p align="center">
<a href="https://trendshift.io/repositories/15323" target="_blank"><img src="https://trendshift.io/api/badge/repositories/15323" alt="GeeeekExplorer%2Fnano-vllm | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>
</p>

This project extends [GeeeekExplorer/nano-vllm](https://github.com/GeeeekExplorer/nano-vllm)
at the [pinned upstream revision](artifacts/environment/upstream-commit.txt).
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
