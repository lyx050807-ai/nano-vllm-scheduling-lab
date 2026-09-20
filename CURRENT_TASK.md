# CURRENT_TASK.md

## Task ID

POLICY-001

## Title

Design the waiting-request scheduling policy abstraction.

## Goal

Design a minimal policy abstraction that allows the pinned nano-vLLM scheduler
to select waiting requests using:

- baseline
- future short_prompt
- future aged_short_prompt

Do not implement the policies yet.

## Required Reads

Read:

- AGENTS.md
- PROJECT_STATE.md
- docs/architecture.md
- docs/benchmark-protocol.md
- nanovllm/engine/scheduler.py
- nanovllm/engine/sequence.py
- nanovllm/config.py

Inspect the exact current scheduling loop before proposing the design.

## Baseline Requirement

The default baseline policy must reproduce the current scheduler behavior
exactly.

No configuration change should alter existing behavior unless a non-baseline
policy is explicitly selected.

## Policy Scope

The policy abstraction should control only:

which waiting request is selected as the next candidate for admission/prefill.

It must not control:

- running request ordering
- decode scheduling
- KV-cache allocation
- block-manager behavior
- model execution
- sampling
- preemption

## Short-Prompt Semantics

Define future short_prompt as:

Select the waiting request with the smallest num_prompt_tokens.

For equal prompt lengths, preserve original waiting/arrival order.

Do not use:

- actual output length
- future completion information
- generated-token count from the future

## Selection vs Sorting

Prefer a candidate-selection abstraction rather than permanently sorting the
entire waiting deque.

Analyze:

- current deque behavior
- O(n) minimum selection
- arbitrary candidate removal
- stable tie-breaking
- interaction with existing feasibility checks

## Resource-Check Semantics

Preserve the existing scheduler's allocation/budget checks after candidate
selection.

Do not add a new policy that scans for another request after the selected
candidate fails an existing allocation/resource check unless the current
baseline already does so.

The first short_prompt implementation should change priority, not introduce a
separate resource-aware scheduling algorithm.

## Future Aging Compatibility

The abstraction must be extendable to aged_short_prompt later.

Identify what scheduler-owned information aging will require.

Do not make future aging depend on telemetry being enabled.

Telemetry is measurement infrastructure, not scheduler state.

## Configuration Design

Propose how policy selection should be configured.

Expected conceptual values:

- baseline
- short_prompt
- aged_short_prompt

The default must remain baseline.

Invalid policy values should fail clearly.

Do not implement configuration changes yet.

## Invariants

Document invariants including:

- baseline reproduces current behavior
- waiting requests are neither lost nor duplicated
- stable ordering is preserved for equal priority
- running queue behavior is unchanged
- existing resource checks remain authoritative
- request identity is preserved
- no future information is used

## Complexity

Document expected candidate-selection complexity for each policy.

For short_prompt, explain why an O(n) scan is sufficient and why globally
sorting the waiting queue is unnecessary.

## Output

Create:

docs/scheduling-policy-design.md

Include:

1. current baseline selection behavior
2. proposed policy interface
3. baseline semantics
4. short_prompt semantics
5. stable tie-breaking
6. selection/removal approach
7. resource-check interaction
8. future aging requirements
9. complexity
10. invariants
11. proposed implementation locations
12. test plan for the implementation task

Include concise pseudocode.

## Restrictions

Do not:

- modify nanovllm scheduler behavior
- implement short_prompt
- implement aging
- run policy benchmarks
- change dependencies
- change formal benchmark traces

## Validation

Run:

git diff --check
git status --short

Confirm nanovllm/ is unchanged.

## PROJECT_STATE

Update PROJECT_STATE.md with:

- POLICY-001 completion
- chosen abstraction
- next recommended task

## Acceptance Criteria

- policy scope is explicitly limited
- baseline compatibility is specified
- short_prompt semantics are unambiguous
- equal-length tie behavior is defined
- resource-check semantics are preserved
- future aging does not depend on telemetry
- complexity is documented
- implementation/test locations are identified
- no scheduler behavior changed
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- proposed policy interface
- baseline selection rule
- short_prompt selection rule
- tie-breaking rule
- candidate-removal approach
- resource-check behavior
- future aging state requirements
- complexity
- proposed files for implementation
- files modified
- recommended next step
