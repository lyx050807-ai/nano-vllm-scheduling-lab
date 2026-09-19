# CURRENT_TASK.md

## Task ID

ENV-007

## Title

Install nano-vLLM in editable mode and validate package imports.

## Goal

Install the pinned local nano-vLLM repository into the project .venv without
changing the validated dependency stack.

Do not download a model or run full inference yet.

## Validated Environment

- Python 3.12.3
- torch 2.6.0+cu124
- Triton 3.2.0
- FlashAttention 2.7.4.post1
- Transformers 4.57.6
- RTX 4050 CUDA validation passed

These versions must remain unchanged.

## Required Work

1. Read AGENTS.md, PROJECT_STATE.md, docs/environment.md, and
   docs/gpu-stack-plan.md.

2. Inspect the repository package metadata and confirm the local package name.

3. Install the current repository into .venv in editable mode.

4. Prevent dependency resolution from replacing the already validated
   environment.

5. Verify that the installed package resolves to this repository's local source.

6. Run minimal import smoke tests for the important nano-vLLM modules.

7. Do not run model inference yet.

8. Run:

   pip check

9. Reconfirm:

   - torch version
   - triton version
   - flash-attn version
   - torch.cuda.is_available()
   - GPU name

## Output

Create:

artifacts/environment/nanovllm-install-info.txt

Record:

- installation command
- package/import name
- editable installation path
- import test results
- pip check result
- torch/triton/flash-attn versions after installation
- CUDA availability

## Restrictions

Do not:

- download models
- run full LLM inference
- modify nanovllm source files
- change torch
- change triton
- change flash-attn
- install CUDA Toolkit

If installation requires changing the validated stack, stop and report the
blocker instead.

## Validation

Run:

git diff --check
git status --short

Confirm:

- nano-vLLM imports from the local repository
- pip check passes
- validated GPU stack remains unchanged
- nanovllm source files were not modified

## PROJECT_STATE

Update PROJECT_STATE.md with ENV-007 status and next recommended task.

## Acceptance Criteria

- local nano-vLLM is installed in editable mode
- imports succeed
- dependency versions remain unchanged
- CUDA remains available
- no model was downloaded
- no source file was modified
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- installation result
- editable package path
- import results
- pip check result
- torch/triton/flash-attn versions
- CUDA status
- files modified
- recommended next step
