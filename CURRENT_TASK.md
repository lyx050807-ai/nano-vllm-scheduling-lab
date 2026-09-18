# CURRENT_TASK.md

## Task ID

BOOTSTRAP-001

## Title

Verify project repository bootstrap.

## Goal

Inspect the current repository and verify that the project bootstrap and Git
structure are correct before any development environment is installed.

This is an inspection and documentation task.

Do not modify nano-vLLM source code.

## Context

This repository is based on nano-vLLM and will be used for a reproducible
single-GPU scheduling experiment.

The local Git repository is the source of truth.

The repository should currently be in bootstrap state only.

## Required Reads

Before doing anything:

1. Read AGENTS.md.
2. Read PROJECT_STATE.md.
3. Read this CURRENT_TASK.md.

## Required Checks

Verify:

1. The repository is located in the Linux filesystem rather than /mnt/c.
2. The current branch is:

   codex/scheduling-lab

3. The upstream remote points to:

   GeeeekExplorer/nano-vllm

4. The upstream commit file exists:

   artifacts/environment/upstream-commit.txt

5. The upstream commit file contains a valid Git commit hash.

6. These project files exist:

   - AGENTS.md
   - PROJECT_STATE.md
   - CURRENT_TASK.md
   - .gitignore

7. These project directories exist:

   - docs
   - scripts
   - lab
   - tests
   - workloads
   - results
   - artifacts/environment

8. .gitignore excludes:

   - virtual environments
   - Python caches
   - model files/caches
   - temporary files
   - large raw results

9. No nano-vLLM source file has been modified.

10. Run:

   git diff --check

11. Inspect:

   git status --short

## Allowed Changes

You may only correct problems in:

- AGENTS.md
- PROJECT_STATE.md
- CURRENT_TASK.md
- .gitignore
- .gitkeep files
- artifacts/environment metadata

Do not modify files under nanovllm/.

Do not install any software or Python package.

## Out of Scope

Do not:

- create a Python virtual environment
- install Python
- install PyTorch
- install CUDA
- install FlashAttention
- install nano-vLLM dependencies
- download a model
- run inference
- change scheduler code
- change any file under nanovllm/

## Acceptance Criteria

The task passes only if:

- repository path is inside the WSL Linux filesystem
- branch is codex/scheduling-lab
- upstream commit is recorded
- required project files/directories exist
- no upstream nano-vLLM source file is modified
- git diff --check passes
- repository status is fully understood

## Completion Requirements

Update PROJECT_STATE.md only if a bootstrap fact needs correction.

Do not create a Git commit.

At completion report:

- repository path
- current branch
- upstream commit
- remote configuration
- files inspected
- files modified, if any
- git status
- git diff --check result
- any detected problems
