# PROJECT_STATE.md

Last updated: 2026-09-19

## Current Phase

ENV-001 through ENV-007, MODEL-001, SMOKE-001, ARCH-001 and TRACE-001 complete;
request-trace v1 specified after validated smoke inference and architecture analysis.

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

- TRACE-001 completed: docs/trace-spec.md defines versioned JSONL, arrival/tokenization semantics, scheduler information boundaries, reproducibility, validation and a development-only workload.
- TRACE-001 is specification only; generator, replay, telemetry and policies remain unimplemented. Formal benchmark parameters remain unfrozen.

- ARCH-001 completed: source-backed request lifecycle, queue behavior, prefill/decode, KV ownership and candidate waiting-policy insertion point documented in docs/architecture.md.
- ARCH-001 was documentation only; no nano-vLLM source, dependency or scheduling behavior changes.

- WSL2 installed and validated.
- Ubuntu 24.04 installed.
- NVIDIA GPU visible inside WSL.
- Git available inside WSL.
- nano-vLLM cloned into the Linux filesystem.
- upstream remote configured.
- development branch created.
- upstream nano-vLLM commit recorded.
- initial project directory structure created.
- SMOKE-001 completed on attempt 3 after user-installed host compiler and Python development headers; same model/config/script, one request passed.
- Previous failed attempts and successful output preserved in artifacts/environment/smoke-single-request.txt.
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

Initial single-request inference, architecture analysis and trace specification
are complete. Trace implementation, replay/telemetry design and broader
integration coverage remain pending.
No formal performance experiment has run.
Evidence: artifacts/environment/smoke-single-request.txt.
Reusable entry point: scripts/smoke_single_request.py.

## Not Started

- full nano-vLLM integration validation
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
The dependency combination passed one conservative single-request inference;
broader workload/configuration compatibility remains unvalidated.
The initial missing C compiler and subsequent missing Python.h blockers were
resolved by user-installed gcc/g++ 13.3.0 and python3.12-dev 3.12.3-1ubuntu0.17.
Attempt 3 completed normally with no runtime warnings or errors. Historical
constructor failures and NCCL cleanup warnings remain in the runtime record.
No Python dependency or source changes were required.
No system CUDA Toolkit is needed for the initial prebuilt-wheel path.
No CUDA Toolkit was installed. Basic PyTorch GPU computation is now validated;
FlashAttention API tests passed. SMOKE-001 exercised the engine warmup,
Triton execution, single-GPU NCCL setup/cleanup and cached decoding on this
one-request path; this is not comprehensive kernel/integration validation.
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
MODEL-001 downloaded Qwen3-0.6B. SMOKE-001 attempt 3 completed one user
request after two preserved warmup failures.
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

TRACE-001 documentation checks include JSON example parsing, offline pinned
tokenizer counts, specification consistency, git diff --check and git status
--short. nano-vLLM source remains unchanged; no inference or benchmark run.

ARCH-001 source references and lifecycle were checked against the local pinned
implementation. Documentation-only validation: git diff --check and git status
--short; nanovllm/ remains unchanged. No inference or benchmark run for ARCH-001.

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
MODEL-001 inspected a safetensors header listing 311 tensors without loading
a model. SMOKE-001 subsequently loaded it on cuda:0 and generated a response
on attempt 3, after two failed warmup attempts.
Model directory is ignored by Git.

## Next Task

Implement a CPU-only trace generator and validator against docs/trace-spec.md
in a separately scoped task. Test deterministic bytes/hashes, schema and IDs,
arrival ordering, exact tokenizer counts, class ranges and context safety.
Keep replay, telemetry and scheduling-policy implementation separate. Preserve
the validated stack and conservative smoke script. Formal workload parameters
remain unfrozen; development trace values establish no performance claims.

## SMOKE-001 Attempt

Configuration: local Qwen3-0.6B, enforce_eager=True, tensor_parallel_size=1,
max_model_len=256, max_num_batched_tokens=256, max_num_seqs=1,
gpu_memory_utilization=0.6. Sampling: temperature=0.6, max_tokens=32,
ignore_eos=False, seed=42; local chat template enable_thinking=False.
Prompt: 'Say hello in one short sentence.' (19 tokens after chat formatting).
Initial attempt: one process; zero user requests completed and no output tokens
were produced. Upstream warmup precedes generate and is not a user request.
Process wall time: 9.315443 seconds including failure, not generation latency.
Pre-load CUDA free/total memory: 5318377472 / 6438780928 bytes; peak memory
was not captured because initialization failed. The reported error was a
compiler failure, not an out-of-memory error. Full traceback is preserved.

### Continuation after user-installed C/C++ compiler

Same script (unchanged SHA256 recorded), model and configuration; one retry.
gcc and g++ 13.3.0 are available at /usr/bin. Initialization failed during
upstream warmup because Python.h was missing. No user request was submitted,
no output generated. Process wall time: 8.905485 seconds including failure.
Pre-load free/total CUDA bytes: 5318377472 / 6438780928; peak not captured.
NCCL cleanup warning followed constructor failure. Both complete error records
are preserved in artifacts/environment/smoke-single-request.txt.

### Successful continuation after user-installed Python development headers

Attempt 3 used the exact same script/model/configuration and completed one
request normally (process exit 0). Python.h and python3.12-config were verified;
python3.12-dev version is 3.12.3-1ubuntu0.17. No package changes by the agent.
Output: 'Hello! How can I assist you today?<|im_end|>'.
Prompt tokens: 19; output tokens: 10, including EOS token 151645.
Model device: cuda:0 on NVIDIA GeForce RTX 4050 Laptop GPU.
Load/warmup: 11.072971 s; generation: 7.158313 s; script through cleanup:
18.900762 s; whole process including Python imports/startup/exit: 25.007268 s.
Timings include first-run compilation effects and are not benchmark results.
PyTorch peak allocated/reserved bytes since upstream warmup's statistics reset:
2606195712 / 2678063104 (about 2.43 / 2.49 GiB). These are allocator statistics,
not total device/process residency. Post-generation free/total CUDA bytes:
2610954240 / 6438780928. No warnings/errors observed on this successful attempt.
The first two complete failure records are preserved verbatim in the log.

## Important Constraints

Do not install dependencies during the bootstrap verification task.

Do not modify nano-vLLM source code during bootstrap.

Do not change the upstream revision during the main experiment without
documenting the change.

Do not claim any scheduling performance improvement before formal experiments
have been completed.
