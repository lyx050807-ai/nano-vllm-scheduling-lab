# CURRENT_TASK.md

## Task ID

ENV-005

## Title

Install and validate ordinary runtime dependencies.

## Goal

Install the ordinary Python runtime dependencies required by the pinned
nano-vLLM repository while preserving the already validated PyTorch/Triton
GPU stack.

Do not install flash-attn yet.

## Context

Validated environment:

- Python 3.12.3
- torch 2.6.0+cu124
- PyTorch CUDA runtime 12.4
- Triton 3.2.0
- RTX 4050 GPU computation works

These versions must not be changed during this task.

## Required Work

1. Read AGENTS.md, PROJECT_STATE.md, docs/environment.md, and
   docs/gpu-stack-plan.md.

2. Inspect the pinned repository dependency declarations.

3. Identify runtime dependencies other than:

   - torch
   - triton
   - flash-attn

4. Install the required ordinary dependencies into .venv.

5. Preserve:

   - torch 2.6.0+cu124
   - triton 3.2.0

6. Do not allow pip to silently replace the validated torch or triton versions.

7. Verify imports for the important installed packages.

8. Run:

   pip check

9. Re-run a small PyTorch CUDA validation to confirm GPU operation still works.

## Output

Create:

artifacts/environment/runtime-deps-info.txt

Record:

- packages installed
- important versions
- import validation
- pip check result
- torch version after installation
- triton version after installation
- CUDA availability after installation

## Restrictions

Do not:

- install flash-attn
- install CUDA Toolkit
- download models
- run model inference
- modify nanovllm/
- change torch version
- change triton version

## Validation

Run:

git diff --check
git status --short

Confirm:

- ordinary dependencies import successfully
- pip check passes
- torch remains 2.6.0+cu124
- triton remains 3.2.0
- torch.cuda.is_available() remains True
- nanovllm/ is unchanged

## PROJECT_STATE

Update PROJECT_STATE.md with ENV-005 completion and the next recommended task.

## Acceptance Criteria

- required ordinary runtime dependencies are installed
- torch/triton versions remain unchanged
- imports succeed
- pip check passes
- CUDA still works
- no nano-vLLM source was modified
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- packages installed
- important package versions
- torch/triton versions
- pip check result
- CUDA validation result
- files modified
- recommended next step
