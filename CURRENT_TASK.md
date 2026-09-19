# CURRENT_TASK.md

## Task ID

ENV-006

## Title

Install and validate FlashAttention safely.

## Goal

Install a FlashAttention build compatible with the already validated project
environment without changing the working PyTorch/Triton stack.

Prefer a compatible prebuilt wheel.

Do not install CUDA Toolkit or perform an uncontrolled source build.

## Current Validated Environment

- Python 3.12.3
- torch 2.6.0+cu124
- PyTorch CUDA runtime 12.4
- Triton 3.2.0
- RTX 4050 Laptop GPU
- torch CUDA computation works
- nvcc is not currently installed

These validated versions must remain unchanged.

## Required Work

1. Read:
   - AGENTS.md
   - PROJECT_STATE.md
   - docs/environment.md
   - docs/gpu-stack-plan.md

2. Inspect the pinned nano-vLLM dependency declaration for flash-attn.

3. Determine whether a compatible prebuilt FlashAttention package exists for:
   - Linux x86_64
   - Python 3.12
   - torch 2.6.0
   - CUDA 12.x / cu124-compatible environment

4. Prefer a prebuilt wheel when available.

5. If a compatible prebuilt wheel is available:
   - install it only inside .venv
   - do not allow torch or triton to be replaced

6. If no compatible prebuilt wheel is available and installation would require
   CUDA Toolkit/nvcc or a source build:
   - STOP
   - do not install CUDA Toolkit
   - do not start a source build
   - document the blocker and recommended next action

## Validation If Installation Succeeds

Verify:

- import flash_attn succeeds
- flash-attn version
- torch remains 2.6.0+cu124
- triton remains 3.2.0
- torch.cuda.is_available() remains True
- RTX 4050 is still detected
- pip check passes

If practical, run a minimal FlashAttention import/API smoke test that does not
require downloading a model.

## Output

Create:

artifacts/environment/flash-attn-info.txt

Record:

- installation path chosen
- whether a prebuilt wheel was used
- flash-attn version
- import result
- torch version after installation
- triton version after installation
- CUDA availability
- pip check result
- any warnings or blockers

## Restrictions

Do not:

- install CUDA Toolkit
- install or invoke nvcc
- change torch version
- change triton version
- download model weights
- modify nanovllm/
- perform a long source build without explicit approval

## PROJECT_STATE

Update PROJECT_STATE.md with:

- ENV-006 status
- FlashAttention installation result or blocker
- next recommended task

## Acceptance Criteria

Success path:

- compatible FlashAttention installs and imports
- torch remains 2.6.0+cu124
- triton remains 3.2.0
- CUDA still works
- pip check passes
- nanovllm/ unchanged

Blocked path is also acceptable if:

- no safe compatible prebuilt wheel is available
- no CUDA Toolkit/source build was attempted
- blocker is clearly documented

Run:

git diff --check
git status --short

Do not create a Git commit.

## Completion Report

Report:

- installed or blocked
- FlashAttention version if installed
- wheel or source-build requirement
- torch version
- triton version
- CUDA status
- pip check result
- files modified
- recommended next step
