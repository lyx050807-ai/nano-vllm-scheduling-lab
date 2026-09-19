# CURRENT_TASK.md

## Task ID

MODEL-001

## Title

Prepare and validate the Qwen3-0.6B model files.

## Goal

Download the planned small model for nano-vLLM experiments and validate its
configuration and tokenizer without running full model inference yet.

## Model

Use:

Qwen/Qwen3-0.6B

Store the model under the repository-local ignored model directory:

models/Qwen3-0.6B

Do not add model files to Git.

## Required Work

1. Read:
   - AGENTS.md
   - PROJECT_STATE.md
   - docs/environment.md

2. Inspect the nano-vLLM README/examples to understand how model paths are
   supplied to the engine.

3. Confirm the current validated environment is still healthy.

4. Download Qwen/Qwen3-0.6B into:

   models/Qwen3-0.6B

5. Record the Hugging Face model repository and exact downloaded revision or
   snapshot commit when available.

6. Validate locally:

   - model config loads
   - tokenizer loads
   - tokenizer can encode a short sentence
   - tokenizer can decode the resulting tokens
   - model path is usable by Transformers locally

7. Do not instantiate the full model on GPU yet.

8. Confirm models/ is ignored by Git.

## Output

Create:

artifacts/environment/model-info.txt

Record:

- model repository
- local model path
- revision/snapshot if available
- config validation result
- tokenizer validation result
- a small tokenization example
- model directory size

## Restrictions

Do not:

- run full model inference
- load model weights onto GPU
- modify nanovllm/
- change torch/triton/flash-attn versions
- commit model weights to Git

## Validation

Run:

git diff --check
git status --short
git check-ignore -v models/Qwen3-0.6B

Confirm model files do not appear as Git changes.

## PROJECT_STATE

Update PROJECT_STATE.md with:

- MODEL-001 completion
- selected model
- local path
- revision/snapshot if known
- next recommended task

## Acceptance Criteria

- Qwen3-0.6B is available locally
- config loads successfully
- tokenizer encode/decode works
- model directory is ignored by Git
- no inference was performed
- nanovllm/ remains unchanged
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- model source
- local path
- downloaded revision
- directory size
- config result
- tokenizer result
- files modified
- recommended next step
