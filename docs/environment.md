# Environment inspection (ENV-001)

Inspection date: 2026-09-18. No installation, package changes, virtual environment
creation, model download, or inference was performed.

Repository: `/home/luoyuxuan/projects/nano-vllm-scheduling-lab`.
Project HEAD: `4b59662156d7f179c065120c9bea960b6af8aec1`.
Pinned upstream: `bb823b3e06983d71485a8e1f23715ebd87d98ef8`
(`artifacts/environment/upstream-commit.txt`). Dependency declarations, README,
and `nanovllm/` are unchanged relative to that upstream revision.

## 1. Local System

| Item | Observed result |
| --- | --- |
| OS | Ubuntu 24.04.5 LTS (Noble Numbat), x86_64 |
| WSL context | WSL2 kernel `6.18.33.2-microsoft-standard-WSL2`; Windows-hosted Ubuntu-24.04 distribution |
| GPU | NVIDIA GeForce RTX 4050 Laptop GPU |
| Total VRAM | 6141 MiB; snapshot usage 807 MiB, not a reserved memory budget |
| NVIDIA driver | `616.64`, from GPU query and KMD Version |
| NVIDIA-SMI utility | `615.65.07`; distinct from the reported driver version |
| Driver-side CUDA report | Header explicitly says `CUDA UMD Version: 13.4` |
| CUDA Toolkit / nvcc | `nvcc` command not found (exit 127); no Toolkit version established |
| Python | `python3`: Python 3.12.3, `/usr/bin/python3` |
| Other requested Python commands | `python3.11` and `python3.10` not found (exit 127) |
| pip | `pip3` not found (exit 127) |

Raw command outputs and exit codes are in
`artifacts/environment/system-info.txt`. Missing commands establish that they
are unavailable on the inspected PATH, not that no installation exists anywhere
on disk. The WSL application release was not queried; WSL2 is established by
`uname -a`.

The NVIDIA driver, its CUDA user-mode/compatibility report, the CUDA Toolkit
compiler (`nvcc`), and a future PyTorch build's CUDA runtime are separate facts.
The 13.4 driver-side report does not prove CUDA Toolkit 13.4 is installed and
must not be used as the choice of a PyTorch runtime. PyTorch's CUDA runtime and
GPU operation were not inspected or validated in this task.

## 2. nano-vLLM Requirements

Repository inventory found `pyproject.toml` and one `README.md`. There is no
`setup.py`, `setup.cfg`, `requirements.txt`, `requirements/` directory, lockfile,
or generated package metadata in this checkout. All Python imports were scanned
statically without importing or executing nano-vLLM.

| Requirement | Repository evidence | Conclusion |
| --- | --- | --- |
| Python | `pyproject.toml`, `[project].requires-python` | `>=3.10,<3.13` |
| PyTorch | `pyproject.toml`, dependencies | `torch>=2.4.0`; no exact version or CUDA build pinned |
| torchvision | Absent from dependency declarations and all source imports | Not required by this repository's declared dependencies or source; no reason here to add it |
| transformers | `pyproject.toml`; `nanovllm/config.py:3`, `nanovllm/engine/llm_engine.py:5` | Required, `>=4.51.0` |
| Triton | `pyproject.toml`; `nanovllm/layers/attention.py:3` and `:10` | Required, `>=3.0.0`; executes a JIT KV-cache kernel |
| FlashAttention | `pyproject.toml`; `nanovllm/layers/attention.py:6`, `:67`, `:72` | Required, unversioned `flash-attn`; unconditional import and prefill/decode calls, no optional fallback |
| xxhash | `pyproject.toml`; `nanovllm/engine/block_manager.py:2` | Required, no version constraint |
| NumPy | `nanovllm/engine/block_manager.py:3` | Direct runtime import, not separately declared in top-level dependencies; no version stated |
| tqdm | `nanovllm/engine/llm_engine.py:4` | Direct runtime import, not separately declared; no version stated |
| safetensors | `nanovllm/utils/loader.py:5` | Direct runtime import for weight loading, not separately declared; no version stated |
| Build backend | `pyproject.toml`, `[build-system]` | `setuptools>=61`, `setuptools.build_meta`; build requirement rather than inference dependency |

Whether the undeclared direct imports are supplied transitively by a selected
dependency set must be verified later; the checkout does not lock that set.

**Linux assumption:** README and metadata do not explicitly declare a supported
OS matrix. `nanovllm/engine/model_runner.py:26-30` unconditionally initializes
NCCL and CUDA, including with world size 1. Together with the Triton and
FlashAttention implementation this is evidence of an NVIDIA GPU-oriented
execution path, consistent with the Linux/WSL target. Explicit Linux-only or
native Windows support is unclear from repository evidence alone.

**CUDA-specific requirements:** execution requires working CUDA-enabled PyTorch
and NCCL, plus the imported Triton and FlashAttention functionality. The
repository does not specify a minimum driver, CUDA Toolkit version, CUDA wheel
index, compiler version, FlashAttention build procedure, or tested dependency
matrix. Whether local nvcc is needed for the eventual installation is unclear
until its binary/source distribution path is established. Eager execution does
not remove the unconditional FlashAttention dependency.

**Upstream installation command:** `README.md`, Installation, gives:

```bash
pip install git+https://github.com/GeeeekExplorer/nano-vllm.git
```

This was read, not executed. It contains no revision pin and therefore should
not be used unchanged to reproduce this project's pinned source. README also
shows Qwen3-0.6B and an RTX 4070 Laptop with 8 GB in its benchmark; that is not
proof that the benchmark configuration fits this GPU's 6141 MiB.

## 3. Compatibility Assessment

**Python 3.12.3 classification: supported by the declared Python requirement.**
It falls within `>=3.10,<3.13` in `pyproject.toml`. There is no repository evidence
requiring a switch to Python 3.11 or 3.10.

Use Python 3.12.3 as the candidate interpreter for a future isolated project
environment; do not install project packages into the system environment.
This classification does not establish that all allowed dependency versions
are mutually compatible, that FlashAttention has a suitable binary, or that
GPU inference succeeds. Those compatibility questions remain unvalidated.

## 4. Recommended Next Environment Step

Prepare a dependency/build compatibility plan for an isolated Python 3.12.3
environment using this pinned local checkout. Before installation, establish a
compatible PyTorch CUDA build, Triton and FlashAttention combination, whether a
local Toolkit is required, and how pip/venv support will be made available.
Select exact package versions only with additional evidence; the repository's
lower bounds alone are not a tested installation recipe. Verify the NumPy,
tqdm and safetensors imports in the resulting environment later.

After a separately authorized setup task, create the isolated environment and
validate PyTorch CUDA before any model smoke test. No alternative Python version,
exact CUDA version, or exact dependency pins are justified by this inspection.

## Validation and scope

Only this document, the raw environment record, and `PROJECT_STATE.md` are
ENV-001 outputs. `CURRENT_TASK.md` was already modified at task entry and was
not edited. No source or dependency declaration was changed. Required final
checks are `git diff --check`, `git status --short`, `git diff --name-only`, and
comparison of `nanovllm/` against both HEAD and the recorded upstream revision.
