# CURRENT_TASK.md

## Task ID

ENV-002

## Title

Create and validate the project Python virtual environment.

## Goal

Create a project-local Python virtual environment using Python 3.12.3.

Do not install nano-vLLM runtime dependencies yet.

## Context

ENV-001 confirmed:

- system Python: 3.12.3
- nano-vLLM requires Python >=3.10,<3.13
- Python 3.12.3 is supported

## Required Work

1. Read AGENTS.md and PROJECT_STATE.md.
2. Confirm:

   python3 --version

3. Create:

   .venv

4. Activate .venv.

5. Record:

   python --version
   which python
   pip --version
   which pip

6. Confirm python and pip resolve from .venv.

7. Confirm .venv is ignored by Git.

8. Save evidence to:

   artifacts/environment/venv-info.txt

## Restrictions

Do not install:

- PyTorch
- transformers
- triton
- flash-attn
- nano-vLLM
- CUDA Toolkit
- models

Do not modify nanovllm/.

## Validation

Run:

git diff --check
git status --short
git check-ignore -v .venv

Confirm no file under nanovllm/ changed.

## PROJECT_STATE

Update PROJECT_STATE.md with:

- ENV-002 completion
- Python version
- virtual environment path
- recommended next task

## Acceptance Criteria

- .venv exists
- Python version is 3.12.3
- python resolves from .venv
- pip resolves from .venv
- .venv is ignored by Git
- no runtime dependencies were installed
- no nano-vLLM source was modified
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- Python version
- venv path
- python executable
- pip executable
- files modified
- validation results
- recommended next step
