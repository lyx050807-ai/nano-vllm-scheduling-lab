# CURRENT_TASK.md

## Task ID

ENV-001

## Title

Inspect nano-vLLM environment and dependency requirements.

## Goal

Determine the software environment required by the currently pinned nano-vLLM
revision before installing anything.

This is an inspection-only task.

Do not install, upgrade, downgrade, or remove any software or Python package.

## Context

Current environment already known:

- WSL2
- Ubuntu 24.04
- NVIDIA GeForce RTX 4050 Laptop GPU
- approximately 6 GB VRAM
- system Python 3.12.3
- Git repository is based on the pinned nano-vLLM upstream revision

The upstream revision is recorded in:

artifacts/environment/upstream-commit.txt

We need to determine whether the existing system environment is suitable and
what isolated Python environment should be created later.

## Required Reads

Before doing anything:

1. Read AGENTS.md.
2. Read PROJECT_STATE.md.
3. Read CURRENT_TASK.md.
4. Inspect repository files that define installation and dependencies.

## Repository Inspection

Inspect all relevant files that exist, including where applicable:

- pyproject.toml
- setup.py
- setup.cfg
- requirements.txt
- requirements/*.txt
- README.md
- README files
- package metadata
- installation instructions
- dependency declarations

Do not assume files exist. Inspect the repository first.

## Questions To Answer

Determine from repository evidence:

1. What Python version or version range is supported or expected?
2. What PyTorch version is declared or recommended?
3. Is torchvision required?
4. Is transformers required, and which version?
5. Is triton required?
6. Is flash-attn required, optional, or not used?
7. Are there any other important runtime dependencies?
8. Does the repository assume Linux?
9. Are there CUDA-specific installation requirements?
10. Does the repository provide a recommended installation command?
11. Is system Python 3.12.3 clearly supported, clearly unsupported, or unclear?

Do not guess.

If the repository does not provide enough evidence, explicitly mark the answer
as unclear.

## Local Environment Inspection

Run and record the relevant output of:

python3 --version
which python3
pip3 --version || true
nvidia-smi
nvcc --version || true
uname -a
cat /etc/os-release

Also inspect whether these commands currently exist:

python3.11 --version || true
python3.10 --version || true

Do not install missing versions.

## Important CUDA Interpretation

Do not treat the CUDA version reported by nvidia-smi as proof that the CUDA
Toolkit of that version is installed.

Clearly distinguish:

- NVIDIA driver
- CUDA compatibility reported by nvidia-smi
- CUDA Toolkit / nvcc
- future PyTorch CUDA runtime

## Output File

Create:

docs/environment.md

The document should contain:

### 1. Local System

- OS
- WSL version/context
- GPU
- VRAM
- NVIDIA driver
- nvidia-smi CUDA compatibility version
- nvcc status/version
- Python versions currently available

### 2. nano-vLLM Requirements

For every important requirement, include the repository file that provides the
evidence.

Summarize:

- Python requirement
- PyTorch requirement
- transformers requirement
- triton requirement
- flash-attn requirement
- other important dependencies

### 3. Compatibility Assessment

State whether the current system Python 3.12.3 should be used for this project.

Classify it as one of:

- supported
- unsupported
- unclear

Explain briefly based only on repository evidence.

### 4. Recommended Next Environment Step

Recommend the next environment setup step, but do not execute it.

If a different Python version is recommended, explain why.

Do not recommend arbitrary package versions without evidence.

## Raw Environment Records

Save useful raw environment information under:

artifacts/environment/

For example:

artifacts/environment/system-info.txt

Do not store large logs.

## Restrictions

Do not:

- install packages
- run apt install
- run pip install
- create a virtual environment
- install Python
- install CUDA
- install PyTorch
- install FlashAttention
- download a model
- run nano-vLLM inference
- modify files under nanovllm/
- modify upstream dependency declarations

## Validation

Run:

git diff --check

Inspect:

git status --short
git diff --name-only

Confirm that no file under nanovllm/ has changed.

## Acceptance Criteria

The task passes only if:

- local environment information is recorded
- repository dependency requirements are documented from actual evidence
- Python 3.12.3 compatibility is assessed without guessing
- CUDA driver compatibility and CUDA Toolkit are correctly distinguished
- no package was installed
- no virtual environment was created
- no nano-vLLM source file was modified
- git diff --check passes

## Completion Requirements

Update PROJECT_STATE.md with:

- ENV-001 completion status
- important environment findings
- current known compatibility issues
- recommended next task

Do not create a Git commit.

At completion report:

- files inspected
- local environment summary
- declared Python requirement
- declared PyTorch requirement
- other important dependency requirements
- Python 3.12.3 assessment
- files created/modified
- validation results
- recommended next step
