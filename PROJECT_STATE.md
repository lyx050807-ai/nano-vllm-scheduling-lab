# PROJECT_STATE.md

Last updated: 2026-09-19

## Current Phase

ENV-001 through ENV-007 and MODEL-001 complete; Qwen3-0.6B downloaded and locally validated.

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
- MODEL-001 completed: Qwen/Qwen3-0.6B downloaded to models/Qwen3-0.6B.
- Model revision: c1899de289a04d12100db370d81485cdf75e47ca.
- Local config/tokenizer encode-decode and weight/tokenizer SHA256 validation passed; evidence in artifacts/environment/model-info.txt.
- ENV-007 completed: nano-vllm 0.2.0 installed locally in editable mode with dependency resolution disabled.
- ENV-007 isolated imports from outside the repository, editable metadata and pip check passed; all pre-existing package versions preserved.
- ENV-007 evidence: artifacts/environment/nanovllm-install-info.txt.
- ENV-006 completed: FlashAttention 2.7.4.post1 official cp312/cu12/torch2.6/cxx11abiFALSE wheel installed in .venv, with einops 0.8.2.
- ENV-006 imports, pip check and two small FlashAttention GPU API tests passed; Torch/Triton preserved.
- ENV-006 source URL, wheel SHA256, installation and validation evidence: artifacts/environment/flash-attn-info.txt.
- ENV-005 completed: ordinary runtime dependencies installed in .venv with torch/triton constraints.
- ENV-005 imports, offline Qwen3 config dtype, pip check, and GPU matmul validation passed.
- ENV-005 evidence and resolved versions: artifacts/environment/runtime-deps-info.txt.
- ENV-004 completed: installed torch 2.6.0+cu124 and its dependencies only in .venv; GPU matrix multiplication passed.
- ENV-004 evidence and package inventory: artifacts/environment/pytorch-gpu-info.txt.
- ENV-003 completed: concrete GPU stack plan documented in docs/gpu-stack-plan.md.
- ENV-001 completed: repository requirements and local environment inspected.
- ENV-002 completed: recreated and activated the project-local .venv using Python 3.12.3.
- Verified Python and pip resolve from .venv, isolation is enabled, and Git ignores .venv.
- ENV-002 evidence, including the earlier failed attempt, is in artifacts/environment/venv-info.txt.
- Environment evidence recorded in docs/environment.md and artifacts/environment/system-info.txt.

## In Progress

Model files and tokenizer are ready; full GPU integration and inference validation remain pending.

## Not Started

- full nano-vLLM integration validation
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
PyTorch, its declared dependencies and ordinary runtime dependencies are installed
in .venv; system Python
has no torch module. System site-packages are excluded.

Python 3.12.3 satisfies the pinned repository requirement >=3.10,<3.13.
Installed stack: PyTorch 2.6.0+cu124, reported CUDA runtime 12.4, Triton 3.2.0.
Measured Torch C++ ABI is False. CUDA is available; one RTX 4050 Laptop GPU
with compute capability 8.9 was detected. A 4x4 CUDA matrix multiplication
(A @ 2I == 2A) passed after synchronization, with result on cuda:0.
PyTorch reported total memory 6438780928 bytes and free memory 5272240128
bytes at the validation snapshot; these are not workload capacity guarantees.
FlashAttention 2.7.4.post1 is installed from the official
cp312/cu12/torch2.6/cxx11abiFALSE Linux wheel; einops 0.8.2 was its only
new dependency. All pre-existing packages were constrained during installation.
The complete nano-vLLM dependency combination remains unvalidated.
No system CUDA Toolkit is needed for the initial prebuilt-wheel path.
No CUDA Toolkit was installed. Basic PyTorch GPU computation is now validated;
FlashAttention contiguous-cache API smoke tests passed. Paged-cache integration,
Triton kernel execution and NCCL operation remain untested.
Source-build fallback requires a separate Toolkit/compiler assessment.
ENV-005 installed transformers 4.57.6, xxhash 4.0.1, numpy 2.5.3,
tqdm 4.70.1 and safetensors 0.8.0 plus their resolved dependencies.
Transformers 4.57.6 was chosen within the 4.x API family with config.dtype
support. Offline AutoConfig.for_model('qwen3', torch_dtype='bfloat16') produced
Qwen3Config.dtype == torch.bfloat16; no model configuration was downloaded.
The prior missing-NumPy warning is resolved. NumPy/Torch interoperability,
in-memory safetensors round-trip and xxhash checks passed before GPU validation.
Torch 2.6.0+cu124 and Triton 3.2.0 were protected by pip constraints and remained
unchanged. FlashAttention was installed in ENV-006 and nano-vllm 0.2.0 was
installed in editable mode in ENV-007. torchvision and torchaudio remain absent.
MODEL-001 subsequently downloaded Qwen3-0.6B; no inference has been run.
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
package inventory, and Git ignore checks passed.
ENV-004 pip check, version/path isolation checks, GPU detection and CUDA matrix
multiplication passed. Full package versions and memory statistics are recorded
in artifacts/environment/pytorch-gpu-info.txt. No inference was run.
ENV-005 ordinary-package imports and pip check passed. CUDA availability and
4x4 matrix multiplication were revalidated on the RTX 4050 with unchanged
Torch/Triton versions. flash_attn was absent at ENV-005. Evidence and the post-install
package inventory are in artifacts/environment/runtime-deps-info.txt.
ENV-006 confirmed flash_attn import, version 2.7.4.post1, torch 2.6.0+cu124,
Triton 3.2.0, CUDA runtime 12.4 and RTX 4050 availability. FP16 varlen causal
attention and one-token KV-cache decode passed against FP32 PyTorch SDPA
(atol=rtol=0.003); max absolute errors were 0.0005553 and 0.0005496.
pip check passed without warnings/errors. No Toolkit installation, nvcc
invocation, source build or model download was performed in ENV-006.
ENV-007 installed the local package with --editable . --no-deps
--no-build-isolation --no-index, using existing setuptools. Editable metadata
points to /home/luoyuxuan/projects/nano-vllm-scheduling-lab.
Imports from /tmp using isolated Python resolved 12 important nano-vLLM modules
to local source; public LLM and SamplingParams imports passed without engine
instantiation. pip check passed. Torch 2.6.0+cu124, Triton 3.2.0,
FlashAttention 2.7.4.post1 and Transformers 4.57.6 are unchanged, as are all
other pre-existing distributions. CUDA is available and RTX 4050 is detected.
Editable metadata resides in .venv; no egg-info directory was left in the
repository root. Source was not edited.

## Model Files

Repository: Qwen/Qwen3-0.6B.
Revision: c1899de289a04d12100db370d81485cdf75e47ca.
Local path: /home/luoyuxuan/projects/nano-vllm-scheduling-lab/models/Qwen3-0.6B.
Directory size at validation: 1519210302 bytes (1.414875 GiB), including
local download metadata; payload files total 1519209243 bytes.
Qwen3Config loaded locally: bfloat16, 28 layers, hidden size 1024.
Qwen2TokenizerFast loaded locally and round-tripped 'Hello, nano-vLLM!'.
Weight and tokenizer.json SHA256 values match the pinned Hub LFS metadata.
Safetensors header lists 311 tensors; no model instance was created and no
model weights were loaded onto GPU. Model directory is ignored by Git.

## Next Task

Plan a constrained nano-vLLM smoke test for the local pinned Qwen3-0.6B model
on the 6 GB GPU. Explicitly set conservative context/batch/memory limits and
validate the remaining paged-cache, Triton and NCCL integration as appropriate
in that separately authorized task. Preserve all dependency versions and the
model revision. MODEL-001 establishes file/config/tokenizer readiness only,
not successful inference or scheduling performance.

## Important Constraints

Do not install dependencies during the bootstrap verification task.

Do not modify nano-vLLM source code during bootstrap.

Do not change the upstream revision during the main experiment without
documenting the change.

Do not claim any scheduling performance improvement before formal experiments
have been completed.
