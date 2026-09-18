# AGENTS.md

## Project

This repository is a student AI infrastructure project based on nano-vLLM.

Project name:

Lightweight LLM Scheduling and Performance Analysis for Mixed-Length Requests.

The project studies how waiting-queue scheduling policies affect request
latency under mixed prompt lengths.

## Source of Truth

The local Git repository is the only source of truth.

Do not assume that previous ChatGPT or Codex conversations reflect the current
repository state.

Before making changes, inspect the actual repository.

## Upstream

This project extends nano-vLLM.

The upstream revision used by the project is recorded in:

artifacts/environment/upstream-commit.txt

Do not change the upstream revision during the main experiment without explicit
instruction and documentation.

Do not redesign or replace upstream model execution, KV cache management,
chunked prefill, sampling, attention kernels, or CUDA execution unless a task
explicitly requires it.

Preserve upstream behavior for the baseline policy.

## Main Project Scope

The project will implement:

1. Request trace generation.
2. Request arrival replay.
3. Request and token telemetry.
4. Baseline scheduling.
5. Short-prompt-first scheduling.
6. Aging-aware short-prompt scheduling.
7. Unit tests.
8. Single-GPU experiments.
9. Offline analysis and visualization.

Do not add unrelated infrastructure such as HTTP servers, Kubernetes,
multi-GPU support, speculative decoding, custom attention kernels, or other
features outside the project scope.

## Scheduling Constraints

Supported experimental policies will be:

- baseline
- short_prompt
- aged_short_prompt

Do not use future output length when making scheduling decisions.

Scheduling may only use information available when or before the decision is
made, such as prompt token count, arrival time, and waiting time.

## Development Rules

Before editing code:

1. Read PROJECT_STATE.md.
2. Read CURRENT_TASK.md.
3. Inspect the relevant existing source files.
4. Do not modify unrelated files.

During implementation:

- Prefer small and understandable changes.
- Preserve backward compatibility unless explicitly instructed otherwise.
- Keep pure policy logic separate from CUDA-dependent code where practical.
- Do not silently change experiment definitions.
- Do not silently change baseline behavior.
- Do not overwrite previous formal experiment results.
- Avoid large refactors unless explicitly required.

## Testing

Every implementation task must include appropriate validation.

Run CPU unit tests before GPU tests whenever possible.

Never claim that a task succeeded if required tests failed.

If a GPU test cannot run, clearly report why.

## Experiment Integrity

For formal experiment runs, preserve enough metadata to reproduce the run,
including:

- project Git commit
- upstream nano-vLLM commit
- model identity/revision
- trace identity/hash
- experiment configuration
- scheduling policy

Do not change experiment definitions after inspecting final results without
documenting the change as a new experiment.

## Task Completion

Before declaring a task complete:

1. Run all tests required by CURRENT_TASK.md.
2. Run git diff --check.
3. Report files changed.
4. Report commands/tests executed.
5. Report test results.
6. Update PROJECT_STATE.md when required.
7. Do not create a Git commit unless CURRENT_TASK.md explicitly allows it.

## Completion Report

At the end of each task report:

- What changed
- Why it changed
- Files changed
- Tests/checks run
- Results
- Remaining issues
- Recommended next step
