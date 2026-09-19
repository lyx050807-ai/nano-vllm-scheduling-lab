# GPU stack plan (ENV-003)

Date: 2026-09-19. This is a proposed stack, not an installed or experimentally
validated stack. No installation commands below were executed.

## Recommended stack and evidence

Use the existing Python 3.12.3 environment at
`/home/luoyuxuan/projects/nano-vllm-scheduling-lab/.venv`.
The pinned nano-vLLM commit is
`bb823b3e06983d71485a8e1f23715ebd87d98ef8`; current project HEAD inspected was
`eb37f5186adf9ea4d5c54a88b00120a3afa8d0f2`.

| Component | Proposed choice | Reason |
| --- | --- | --- |
| PyTorch | 2.6.0, official Linux x86_64 wheel | Satisfies local `pyproject.toml` torch>=2.4.0; CPython 3.12 artifact exists |
| PyTorch CUDA build | `2.6.0+cu124`, CUDA 12.4 | Official published build with a matching FlashAttention release family |
| Triton | 3.2.0, resolved by PyTorch | Exact dependency in the selected wheel metadata; satisfies local triton>=3.0.0 |
| FlashAttention | 2.7.4.post1, official cu12/torch2.6/cp312 Linux wheel | Both C++ ABI variants exist in the official release; select only after measuring PyTorch ABI |
| CUDA Toolkit | No system Toolkit for the initial wheel-based path | No local CUDA extension compilation is planned |
| torchvision / torchaudio | Omit | Not declared or imported by this project |

PyTorch's [official previous-version instructions](https://docs.pytorch.org/get-started/previous-versions/)
list 2.6.0 with the cu124 index. The
[CPython 3.12 Linux wheel metadata](https://download.pytorch.org/whl/cu124/torch-2.6.0%2Bcu124-cp312-cp312-linux_x86_64.whl.metadata)
was read directly without downloading the wheel. It reports
`Version: 2.6.0+cu124`, `Requires-Python: >=3.9.0`, Linux x86_64
`triton==3.2.0`, and `nvidia-cuda-runtime-cu12==12.4.127`.
It also specifies NCCL 2.21.5, cuDNN 9.1.0.70 and the other CUDA libraries;
let the selected torch wheel resolve its own dependencies.

This choice is based on intersecting project bounds, published CPython wheels,
a Torch-pinned Triton version and matching official FlashAttention assets.
It is not a recommendation based on being the newest release. The
[PyTorch 2.6 release notes](https://pytorch.org/blog/pytorch2-6/)
describe the experimental CUDA 12.6.3 Linux ABI transition; choosing the cu124
line avoids adding that transition to initial setup. The expected cu124 ABI is
FALSE, but the installed value must be checked rather than assumed.

## Four distinct CUDA facts

| Term | Meaning for this project |
| --- | --- |
| NVIDIA driver | Windows-host driver exposed in WSL; GPU query reconfirmed version 616.64 |
| nvidia-smi CUDA report | ENV-001 captured `CUDA UMD Version: 13.4`, a driver-side report, not a Toolkit inventory |
| PyTorch CUDA runtime | Proposed cu124 distribution and its environment-local NVIDIA library dependencies; expect `torch.version.cuda == "12.4"` |
| CUDA Toolkit / nvcc | Compiler, headers and development tools for source builds; nvcc remains unavailable on the inspected PATH |

[NVIDIA compatibility guidance](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)
states that newer drivers continue to support CUDA 12.x through backward
compatibility. Thus driver 616.64 is not a reason to select CUDA 13.x; driver-level
compatibility with the proposed CUDA 12.4 runtime is expected. Actual WSL GPU
execution remains a validation gate.

The [NVIDIA WSL guide](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)
distinguishes running precompiled CUDA applications from compiling new ones.
Keep the existing Windows driver; do not install a Linux display driver in WSL.
A system Toolkit is unnecessary for the initial prebuilt PyTorch/FlashAttention
path. If a later extension source build is needed, stop and plan a compatible
Toolkit and compiler explicitly, using Toolkit-only WSL packages. Do not
silently fall back to source compilation or infer nvcc availability from
nvidia-smi. No Toolkit installation is proposed for the next task.

## Triton and FlashAttention considerations

Keep Triton at 3.2.0 with torch 2.6.0; do not independently upgrade it.
`nanovllm/layers/attention.py` uses a Triton JIT cache-store kernel. Its execution
still needs a later kernel smoke test; package import alone does not verify it.
`nanovllm/engine/model_runner.py` initializes NCCL even for one GPU, so eventual
nano-vLLM validation must cover NCCL as well as basic CUDA tensor operations.

The [FlashAttention 2.7.4.post1 README](https://github.com/Dao-AILab/flash-attention/blob/v2.7.4.post1/README.md)
documents Linux, PyTorch >=2.2, CUDA >=12.0 and Ada support for FlashAttention-2.
The RTX 4050 is listed in NVIDIA's
[compute-capability table](https://developer.nvidia.com/cuda/gpus) under 8.9.
Use the FA2 package consumed by the local attention module, not the Hopper-only
FA3 subpackage. Both `flash_attn_varlen_func` and `flash_attn_with_kvcache`,
including paged-cache arguments, require later functional checks.

The [official release API](https://api.github.com/repos/Dao-AILab/flash-attention/releases/tags/v2.7.4.post1)
was inspected on 2026-09-19. It contains these artifacts:

- `flash_attn-2.7.4.post1+cu12torch2.6cxx11abiFALSE-cp312-cp312-linux_x86_64.whl`
- `flash_attn-2.7.4.post1+cu12torch2.6cxx11abiTRUE-cp312-cp312-linux_x86_64.whl`

The release [setup.py](https://github.com/Dao-AILab/flash-attention/blob/v2.7.4.post1/setup.py)
selects wheels by Python, platform, Torch major/minor, CUDA major and C++ ABI.
Its CUDA 12 wheel logic uses a CUDA 12.3 build and relies on minor-version
compatibility, supporting the cu124 pairing as an installation candidate.
A wheel's existence does not prove it loads or runs on this machine. Verify ABI,
imports, dynamic linking and a small GPU kernel before declaring compatibility.

A direct official wheel URL avoids invoking the source package build path.
If that wheel is unavailable or fails, record the error and revisit the plan.
A source build needs Toolkit/build tools and adequate host RAM; it must be a
separate task, not an automatic fallback on this laptop.

## Proposed order and next-task commands (not executed)

1. Install only the selected PyTorch build and its declared dependencies into
   .venv. This includes its Triton and CUDA runtime libraries.
2. Check versions, CUDA visibility, device identity/capability and a small
   tensor operation. Stop if any check fails; preserve outputs as evidence.
3. In a later dependency task, select the measured-ABI FlashAttention wheel,
   satisfy its declared dependencies under Torch/Triton constraints, then test
   import and GPU functionality. Resolve transformers and the remaining project
   imports separately without upgrading the selected GPU stack.
4. Only after dependency validation, install the pinned local project, record
   the resolved dependency set, then schedule model setup and an inference smoke
   test as separate work. The 6141 MiB GPU does not establish workload capacity.

Proposed immediate next task, run in WSL bash from the repository:

```bash
set -e
cd /home/luoyuxuan/projects/nano-vllm-scheduling-lab
source .venv/bin/activate
python --version
which python
python -m pip install 'torch==2.6.0+cu124' --index-url https://download.pytorch.org/whl/cu124
python -m pip check
python - <<'PY'
import sys
import torch
import triton
assert sys.version_info[:3] == (3, 12, 3)
assert torch.__version__ == '2.6.0+cu124'
assert torch.version.cuda == '12.4'
assert triton.__version__ == '3.2.0'
print('torch:', torch.__version__, 'CUDA runtime:', torch.version.cuda)
print('triton:', triton.__version__)
print('CXX11 ABI:', torch._C._GLIBCXX_USE_CXX11_ABI)
assert torch.cuda.is_available()
print('GPU:', torch.cuda.get_device_name(0))
print('capability:', torch.cuda.get_device_capability(0))
x = torch.ones((32, 32), device='cuda')
y = x @ x
assert torch.all(y == 32).item()
torch.cuda.synchronize()
print('Basic CUDA tensor check passed; FA/Triton kernels and NCCL still untested.')
PY
```

For the later FlashAttention task, the expected FALSE-ABI candidate is
[this official wheel](https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.4.post1/flash_attn-2.7.4.post1%2Bcu12torch2.6cxx11abiFALSE-cp312-cp312-linux_x86_64.whl).
Use the TRUE variant only if the measured ABI calls for it. Preserve
`torch==2.6.0+cu124` and `triton==3.2.0` as resolver constraints in that task.
The remaining top-level requirement is transformers>=4.51.0; its exact pin,
xxhash, NumPy, tqdm, safetensors and wheel transitive dependencies are not
arbitrarily pinned here. In particular, the pinned runner accesses
`hf_config.dtype`, which must be checked against the chosen transformers release;
the declared minimum alone is not proof of full runtime compatibility.

## Inspection and validation boundary

Read AGENTS.md, PROJECT_STATE.md, docs/environment.md, CURRENT_TASK.md,
pyproject.toml and the relevant attention/model-runner code. Only HTTP metadata,
release listings and documentation were read; no binary, model or runtime
package was downloaded or installed. At task entry .venv contained only pip
24.0 and CURRENT_TASK.md was already modified. ENV-003 changes only this plan
and PROJECT_STATE.md. Final checks: pip inventory unchanged, git diff --check,
git status --short and no differences under nanovllm/.
