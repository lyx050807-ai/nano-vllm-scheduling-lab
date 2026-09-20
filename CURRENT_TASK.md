# CURRENT_TASK.md

## Task ID

POLICY-002

## Title

Implement baseline and short_prompt waiting-request selection.

## Goal

Implement the scheduling-policy abstraction designed in POLICY-001 and add
short_prompt waiting-request selection while preserving all existing scheduler
mechanisms and baseline behavior.

Do not implement aging yet.

## Required Reads

Read:

- AGENTS.md
- PROJECT_STATE.md
- docs/architecture.md
- docs/scheduling-policy-design.md
- docs/benchmark-protocol.md
- nanovllm/config.py
- nanovllm/engine/scheduler.py
- nanovllm/engine/sequence.py

Inspect the exact current source before editing.

## Configuration

Add an explicit scheduling-policy configuration with supported values:

- baseline
- short_prompt

Reserve aged_short_prompt for a later task; do not implement it here.

Default must be:

baseline

Invalid values must fail clearly.

Existing callers that do not specify a policy must preserve the current
behavior exactly.

## Policy Abstraction

Implement a small selector that chooses the index/candidate from the waiting
deque.

Keep policy selection separate from:

- resource feasibility checks
- KV-cache allocation
- token-budget logic
- chunked-prefill handling
- running queue management
- decode scheduling

## Baseline Semantics

baseline must reproduce the current waiting behavior exactly.

Conceptually:

candidate = waiting[0]

Preserve the existing popleft/removal behavior and all subsequent checks.

## short_prompt Semantics

When waiting is non-empty, select the request having the smallest:

num_prompt_tokens

Use an O(n) scan.

Do not globally sort or permanently reorder the waiting deque.

For equal prompt lengths, select the earliest request in the existing deque.

Example:

waiting:

A: 192
B: 32
C: 96
D: 32

short_prompt candidate sequence should be:

B
D
C
A

assuming all candidates are successfully admitted/prefilled.

## Candidate Failure Semantics

After a candidate is selected, run the exact existing allocation/resource
checks.

If the selected short_prompt candidate fails a check that causes the current
baseline scheduler to stop/break, preserve that behavior.

Do not search for another candidate merely because the selected candidate
failed an existing resource check.

This task changes request priority only; it does not implement
resource-aware bypass scheduling.

## Removal Semantics

Preserve all existing chunked-prefill and waiting-to-running lifecycle rules.

Do not permanently remove a selected waiting request earlier than the current
baseline semantics permit.

When removing a non-head short_prompt candidate, preserve the relative order of
all remaining requests.

No request may be lost or duplicated.

## Telemetry

Existing telemetry must continue to function.

Do not use telemetry state to implement scheduling decisions.

## CPU Tests

Add deterministic tests covering at least:

1. default configuration is baseline
2. invalid policy fails clearly
3. baseline chooses the current deque head
4. baseline behavior is equivalent to the previous scheduler behavior
5. short_prompt selects the shortest prompt
6. equal-length requests preserve deque arrival order
7. example ordering:
   A=192, B=32, C=96, D=32
   produces B, D, C, A when all requests are admitted
8. candidate removal preserves remaining relative order
9. no request is lost or duplicated
10. short_prompt candidate failure does not fall through to a second candidate
    when baseline would stop
11. existing resource checks remain authoritative
12. running/decode ordering is unchanged
13. telemetry-on and telemetry-off do not change policy decisions

Add focused selector tests where practical rather than requiring GPU.

## Baseline Regression

Run the existing CPU tests and baseline regression tests.

Verify that policy=baseline reproduces expected existing behavior.

## Development GPU Smoke

After all CPU tests pass:

Run the existing 12-request development trace once with:

policy=baseline

and once with:

policy=short_prompt

This is a functional smoke comparison only, not benchmark data.

Verify both:

- complete 12/12
- have no OOM
- have no timeout
- preserve lifecycle invariants
- produce valid joined telemetry

Confirm that short_prompt changes waiting-request service order on a workload
where multiple different prompt lengths are simultaneously waiting.

Do not report performance superiority from these two smoke runs.

## Restrictions

Do not:

- implement aged_short_prompt
- change formal benchmark traces
- run the 45-run formal benchmark
- change KV-cache policy
- introduce resource-aware fallback selection
- change running request ordering
- change decode policy
- change model execution
- change sampling
- change dependencies

## Validation

Run:

git diff --check
git status --short

Review all nanovllm/ source changes carefully.

## PROJECT_STATE

Update PROJECT_STATE.md with:

- POLICY-002 status
- implementation files
- tests run
- baseline regression result
- short_prompt smoke result
- next recommended task

## Acceptance Criteria

- baseline remains the default
- baseline reproduces current behavior
- short_prompt implements stable shortest-prompt selection
- short_prompt uses no future information
- existing resource checks are unchanged
- candidate-failure semantics are preserved
- chunked-prefill lifecycle is preserved
- requests are neither lost nor duplicated
- telemetry remains independent
- CPU tests pass
- both development GPU smoke runs complete 12/12
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- files modified
- policy configuration/interface
- selector implementation
- short_prompt complexity
- tie-breaking behavior
- candidate removal method
- candidate failure behavior
- CPU test count/results
- baseline regression result
- baseline GPU smoke result
- short_prompt GPU smoke result
- observed service-order difference
- warnings/errors
- recommended next step
