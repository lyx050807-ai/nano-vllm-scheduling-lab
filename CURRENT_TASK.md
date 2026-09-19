# CURRENT_TASK.md

## Task ID

ENV-004

## Title

Install PyTorch CUDA and validate GPU computation.

## Goal

Install only the planned PyTorch CUDA stack into the project .venv and verify
that PyTorch can perform real computation on the RTX 4050.

## Context

ENV-003 selected:

- Python 3.12.3
- PyTorch 2.6.0
- CUDA build/runtime: cu124
- expected Triton: 3.2.0

Do not install the remaining nano-vLLM dependencies yet.

## Required Work

1. Read AGENTS.md, PROJECT_STATE.md, and docs/gpu-stack-plan.md.

2. Confirm .venv exists and use its Python explicitly.

3. Record the pre-install package state.

4. Install PyTorch 2.6.0 from the official cu124 PyTorch wheel index.

Use the project virtual environment only.

5. Do not intentionally install torchvision or torchaudio unless PyTorch itself
requires them.

6. After installation, verify and record:

   - torch.__version__
   - torch.version.cuda
   - torch.cuda.is_available()
   - torch.cuda.device_count()
   - torch.cuda.get_device_name(0)
   - Triton version if installed as a dependency

7. Run a real GPU computation:

   - create two small tensors on CUDA
   - perform matrix multiplication
   - synchronize CUDA
   - confirm the result tensor is on cuda:0

8. Record GPU memory information reported by PyTorch.

## Output

Create:

artifacts/environment/pytorch-gpu-info.txt

Record concise commands/results and package versions.

## Restrictions

Do not install:

- transformers
- flash-attn
- CUDA Toolkit
- nano-vLLM
- models

Do not modify nanovllm/.

Do not change the selected PyTorch version without reporting the blocker first.

## Validation

Run:

git diff --check
git status --short

Confirm:

- PyTorch is installed only inside .venv
- torch.cuda.is_available() is True
- RTX 4050 is detected
- CUDA tensor computation succeeds
- nanovllm/ is unchanged

## PROJECT_STATE

Update PROJECT_STATE.md with:

- ENV-004 completion
- installed torch version
- reported PyTorch CUDA runtime
- GPU validation result
- recommended next task

## Acceptance Criteria

- torch 2.6.0 cu124 installation succeeds
- CUDA is available from PyTorch
- RTX 4050 is detected
- GPU matrix multiplication succeeds
- no CUDA Toolkit installation was performed
- no nano-vLLM source was modified
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- torch version
- torch CUDA runtime
- GPU name
- Triton version
- GPU computation result
- files modified
- any warnings/errors
- recommended next step
