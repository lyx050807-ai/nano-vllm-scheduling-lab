# PROJECT_STATE.md

Last updated: 2026-09-19

## Current Phase

ENV-001 through ENV-003 complete; GPU stack planned, runtime installation pending.

## Current Git Branch

codex/scheduling-lab

## Upstream Project

nano-vLLM

Repository:

GeeeekExplorer/nano-vllm

The exact upstream commit is stored in:

artifacts/environment/upstream-commit.txt

## Project Goal

Build a reproducible single-GPU experiment based on nano-vLLM to study
waiting-queue scheduling under mixed prompt lengths.

The planned scheduling policies are:

1. baseline
2. short_prompt
3. aged_short_prompt

Primary performance dimensions:

- TTFT
- scheduling wait time
- long-request waiting behavior
- throughput
- ITL
- completion rate

## Hardware Known So Far

GPU:

NVIDIA GeForce RTX 4050 Laptop GPU

VRAM:

6141 MiB reported by nvidia-smi

Development environment:

WSL2
Ubuntu 24.04

## Completed

- WSL2 installed and validated.
- Ubuntu 24.04 installed.
- NVIDIA GPU visible inside WSL.
- Git available inside WSL.
- nano-vLLM cloned into the Linux filesystem.
- upstream remote configured.
- development branch created.
- upstream nano-vLLM commit recorded.
- initial project directory structure created.
- ENV-003 completed: concrete GPU stack plan documented in docs/gpu-stack-plan.md.
- ENV-001 completed: repository requirements and local environment inspected.
- ENV-002 completed: recreated and activated the project-local .venv using Python 3.12.3.
- Verified Python and pip resolve from .venv, isolation is enabled, and Git ignores .venv.
- ENV-002 evidence, including the earlier failed attempt, is in artifacts/environment/venv-info.txt.
- Environment evidence recorded in docs/environment.md and artifacts/environment/system-info.txt.

## In Progress

GPU stack installation is planned; no runtime dependencies installed.

## Not Started

- PyTorch installation
- CUDA runtime validation from PyTorch
- nano-vLLM dependency installation
- model setup
- nano-vLLM smoke test
- architecture analysis
- trace generator
- replay driver
- telemetry
- scheduling policies
- unit tests
- formal workloads
- experiments
- analysis
- report

## Known Issues

System Python is Python 3.12.3.

The missing ensurepip prerequisite was resolved by the user installing
python3.12-venv (3.12.3-1ubuntu0.17). The incomplete environment was removed
and recreated at /home/luoyuxuan/projects/nano-vllm-scheduling-lab/.venv.
Activated Python and pip resolve to .venv/bin/python and .venv/bin/pip.
Only the bootstrapped pip distribution is installed; no runtime dependencies
were installed. System site-packages are excluded.

Python 3.12.3 satisfies the pinned repository requirement >=3.10,<3.13.
The proposed stack is PyTorch 2.6.0+cu124 (CUDA 12.4), its required Triton
3.2.0, and FlashAttention 2.7.4.post1 via the official cp312 Linux wheel matching
the measured Torch C++ ABI. The complete combination remains unvalidated.
No system CUDA Toolkit is needed for the initial prebuilt-wheel path.
Official package metadata and release assets justify the plan, not GPU tests.
Source-build fallback requires a separate Toolkit/compiler assessment.
Declared dependencies are torch>=2.4.0, triton>=3.0.0,
transformers>=4.51.0, flash-attn (required, unpinned), and xxhash (unpinned).
NumPy, tqdm, and safetensors are imported directly but not separately declared.

Ubuntu reports 24.04.5 LTS on WSL2 kernel 6.18.33.2-microsoft-standard-WSL2.
GPU query reports RTX 4050 Laptop GPU, 6141 MiB VRAM, driver 616.64.
nvidia-smi reports CUDA UMD Version 13.4; this does not establish a CUDA
Toolkit installation or a future PyTorch CUDA runtime version.
At ENV-001, pip3, nvcc, python3.11, and python3.10 were unavailable on PATH.
ENV-002 now provides pip inside .venv; other commands were not rechecked.
The repository does not specify a tested CUDA/build compatibility matrix.

## Current Validation

Repository is currently based on the recorded upstream nano-vLLM commit.

ENV-001 command outputs and exit codes are recorded. Python version and path
were inspected; no dependency imports or GPU inference validation was performed.
Upstream source and dependency declarations remain unchanged.
ENV-002 activation, Python 3.12.3, Python/pip paths, environment isolation,
package inventory, and Git ignore checks passed. Runtime/GPU validation is
still pending.

## Next Task

Install only PyTorch 2.6.0+cu124 and its declared dependencies in .venv in a
separately authorized task, using the official cu124 index. Follow the proposed
commands in docs/gpu-stack-plan.md to check Torch/Triton versions, CUDA runtime,
GPU tensor execution and C++ ABI. Do not install Toolkit or FlashAttention in
that initial step. Resolve FlashAttention and remaining project dependencies
in later tasks, preserving the selected Torch/Triton versions.

## Important Constraints

Do not install dependencies during the bootstrap verification task.

Do not modify nano-vLLM source code during bootstrap.

Do not change the upstream revision during the main experiment without
documenting the change.

Do not claim any scheduling performance improvement before formal experiments
have been completed.
