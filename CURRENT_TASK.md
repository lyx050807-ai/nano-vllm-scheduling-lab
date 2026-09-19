# CURRENT_TASK.md

## Task ID

ENV-003

## Title

Determine the PyTorch and CUDA installation plan.

## Goal

Determine a concrete and compatible GPU software stack for this project
before installing runtime dependencies.

Do not install PyTorch or other runtime dependencies in this task.

## Context

Current environment:

- WSL2
- Ubuntu 24.04
- RTX 4050 Laptop GPU
- approximately 6 GB VRAM
- NVIDIA driver works in WSL
- Python 3.12.3
- project virtual environment: .venv

Pinned nano-vLLM requirements found in ENV-001 include:

- torch >=2.4.0
- transformers >=4.51.0
- triton >=3.0.0
- flash-attn is required but not pinned to an exact version

## Required Work

1. Read AGENTS.md, PROJECT_STATE.md, and docs/environment.md.

2. Inspect the pinned repository's dependency declarations again where needed.

3. Determine a recommended concrete PyTorch installation for:
   - Linux / WSL2
   - Python 3.12
   - NVIDIA RTX 4050
   - current NVIDIA driver

4. Clearly distinguish:
   - NVIDIA driver
   - nvidia-smi CUDA compatibility version
   - PyTorch bundled CUDA runtime
   - CUDA Toolkit / nvcc

5. Assess compatibility concerns involving:
   - PyTorch
   - Triton
   - flash-attn
   - Python 3.12

6. Do not choose versions only because they are the newest.
   Prefer a combination justified by compatibility with this project.

## Output

Create:

docs/gpu-stack-plan.md

Include:

- recommended PyTorch version
- recommended PyTorch CUDA build/runtime
- whether system CUDA Toolkit is needed at this stage
- expected Triton relationship
- expected flash-attn compatibility considerations
- proposed installation order
- commands proposed for the next task

Do not execute the installation commands.

## Restrictions

Do not:

- install PyTorch
- install CUDA Toolkit
- install Triton
- install flash-attn
- install transformers
- install nano-vLLM
- download a model
- modify nanovllm/

## Validation

Run:

git diff --check
git status --short

Confirm nanovllm/ is unchanged.

## PROJECT_STATE

Update PROJECT_STATE.md with ENV-003 findings and the recommended next task.

## Acceptance Criteria

- a concrete GPU stack plan exists
- CUDA terminology is correctly distinguished
- proposed versions are justified
- no runtime dependency was installed
- nanovllm/ is unchanged
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- proposed PyTorch version
- proposed CUDA runtime/build
- CUDA Toolkit requirement
- Triton consideration
- flash-attn consideration
- proposed installation order
- files modified
