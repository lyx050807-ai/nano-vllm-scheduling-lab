# CURRENT_TASK.md

## Task ID

ARCH-001

## Title

Trace the nano-vLLM request lifecycle and scheduling architecture.

## Goal

Understand how a request moves through the pinned nano-vLLM implementation
before designing any scheduling policy.

This is a source-reading and documentation task only.

Do not modify nano-vLLM source code.

## Required Work

Read the existing source and trace one request through the system.

Identify the relevant implementation for:

1. Public LLM API
2. LLMEngine
3. Request/Sequence representation
4. Waiting queue
5. Running queue
6. Scheduler
7. Prefill scheduling
8. Decode scheduling
9. KV-cache block allocation
10. ModelRunner / GPU execution
11. Generated token append/update
12. Request completion and cleanup

## Questions To Answer

Document the exact flow for:

prompt
→ request creation
→ waiting queue
→ scheduler
→ prefill
→ running state
→ decode
→ token update
→ completion

Also answer:

- Where is prompt length stored?
- When is prompt token count known?
- What data structure stores waiting requests?
- What determines waiting-request order today?
- Can waiting requests be reordered without changing running requests?
- Where are requests moved from waiting to running?
- How does the scheduler distinguish prefill from decode?
- Where is KV cache allocated and freed?
- Is preemption present in the pinned implementation?
- At what point could a short_prompt policy be inserted with minimal changes?

Do not guess. Cite file paths, classes, functions, and important line regions.

## Output

Create:

docs/architecture.md

Include:

1. Component overview
2. Request lifecycle
3. Scheduler lifecycle
4. Waiting/running queue behavior
5. Prefill vs decode behavior
6. KV-cache interaction
7. Candidate policy insertion point
8. Risks/invariants that future scheduler changes must preserve

Include a simple ASCII flow diagram.

## Restrictions

Do not:

- modify nanovllm/
- implement a policy
- change scheduler behavior
- run benchmarks
- change dependencies

Small read-only source inspection commands are allowed.

## Validation

Run:

git diff --check
git status --short

Confirm nanovllm/ is unchanged.

## PROJECT_STATE

Update PROJECT_STATE.md with ARCH-001 completion and next recommended task.

## Acceptance Criteria

- request lifecycle is documented from actual source
- waiting and running queues are identified
- prefill/decode distinction is explained
- KV-cache interaction is identified
- candidate policy insertion point is identified
- no nano-vLLM source file changed
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- main classes/files
- waiting queue implementation
- current scheduling behavior
- prefill/decode flow
- KV-cache interaction
- candidate policy insertion point
- important invariants
- files modified
