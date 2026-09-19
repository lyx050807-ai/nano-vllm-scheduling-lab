# CURRENT_TASK.md

## Task ID

SMOKE-001

## Title

Run the first single-request nano-vLLM GPU inference.

## Goal

Load the local Qwen3-0.6B model with the pinned nano-vLLM repository and
successfully generate a short response on the RTX 4050.

This is a single-request smoke test, not a performance experiment.

## Current Environment

- Qwen3-0.6B is available locally
- RTX 4050 Laptop GPU
- approximately 6 GB VRAM
- Python 3.12.3
- torch 2.6.0+cu124
- Triton 3.2.0
- FlashAttention 2.7.4.post1
- nano-vLLM installed editable from this repository

## Required Inspection

Before running inference:

1. Read AGENTS.md and PROJECT_STATE.md.
2. Inspect the pinned nano-vLLM README and examples.
3. Inspect the public LLM/inference API used by the existing examples.
4. Identify the relevant configuration options affecting:
   - model path
   - max model length / context length
   - GPU memory use
   - maximum generated tokens
5. Do not guess API names.

## Required Work

1. Use the local model:

   models/Qwen3-0.6B

2. Design a conservative configuration suitable for approximately 6 GB VRAM.

3. Use one short prompt.

4. Request a small number of output tokens.

5. Run exactly one request first.

6. Record:
   - prompt
   - prompt token count if available
   - generated text
   - generated token count if available
   - wall-clock runtime
   - peak or observed GPU memory when practical
   - important engine configuration

7. Confirm the generated output is non-empty and the request completes normally.

## Failure Handling

If the run fails because of GPU memory:

- stop
- do not modify source code
- report the observed memory error and configuration
- propose a smaller safe configuration

If the run fails because of an import/kernel/runtime error:

- preserve the full relevant error
- do not change dependency versions automatically
- stop and report the blocker

## Output

Create:

artifacts/environment/smoke-single-request.txt

Record the configuration, command/script used, important runtime output,
generated result, and any warnings.

If a temporary smoke-test script is useful, place it under scripts/.

Keep it minimal and reusable.

## Restrictions

Do not:

- modify nanovllm/
- implement scheduling policies
- run multiple concurrent requests
- run performance benchmarks
- change dependency versions
- install CUDA Toolkit
- download another model

## Validation

Run:

git diff --check
git status --short

Confirm:

- one request completed successfully
- generated text is non-empty
- CUDA execution was used
- nanovllm/ source is unchanged

## PROJECT_STATE

Update PROJECT_STATE.md with:

- SMOKE-001 status
- configuration used
- model load/inference result
- GPU memory observations
- next recommended task

## Acceptance Criteria

- nano-vLLM loads Qwen3-0.6B
- RTX 4050 is used
- one prompt completes successfully
- output text is produced
- no source modification was required
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- prompt
- important engine configuration
- prompt/output token counts if available
- generated output
- runtime
- GPU memory observation
- warnings/errors
- files created/modified
- recommended next step
