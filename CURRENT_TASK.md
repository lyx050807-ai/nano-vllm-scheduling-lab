# CURRENT_TASK.md

## Task ID

AGING-001

## Title

Design the aged_short_prompt scheduling policy.

## Goal

Design an aging-based extension of short_prompt that preserves the latency
benefit of short prompts while reducing starvation risk for requests that wait
unusually long.

This is a design task only.

Do not implement aged_short_prompt yet.

## Required Reads

Read:

- AGENTS.md
- PROJECT_STATE.md
- docs/scheduling-policy-design.md
- docs/benchmark-protocol.md
- artifacts/calibration/formal-mixed-v1/capacity-summary.json
- nanovllm/engine/scheduler.py
- nanovllm/engine/sequence.py
- nanovllm/engine/waiting_policy.py

Inspect the exact current preemption and waiting-queue lifecycle.

## Problem

Explain why pure short_prompt can cause priority starvation when shorter
requests continue to arrive.

Distinguish:

- priority starvation
- resource infeasibility
- preemption/requeue behavior

Aging should address priority starvation only.

## Candidate Aging Score

Analyze:

score_i = num_prompt_tokens_i - aging_rate * waiting_seconds_i

Select the waiting request with the smallest score.

Units:

- num_prompt_tokens: tokens
- waiting_seconds: seconds
- aging_rate: tokens/second
- score: token-equivalent priority

Do not use future output length or other future information.

## Aging Parameter

Use the frozen prompt classes:

- short = 32 tokens
- medium = 96 tokens
- long = 192 tokens

Use only baseline/calibration evidence when choosing the aging parameter.

Analyze an interpretable candidate where:

A 192-token long request that has waited about 0.5 seconds reaches priority
parity with a newly arrived 32-token short request.

Derive:

- aging_rate
- medium vs short crossover
- long vs medium crossover
- long vs short crossover

Do not tune aging_rate using future aged_short_prompt performance.

## Waiting-Time Semantics

Compare:

1. time since original engine admission
2. time since current entry into waiting

Inspect the current preemption behavior and choose one explicitly.

Explain how a preempted request should behave.

Do not depend on telemetry for scheduler correctness.

## Scheduler-Owned State

Define the minimum scheduler-owned timing state needed for aging.

Use a monotonic clock.

Telemetry may observe aging behavior but must not supply the scheduler's age.

## Tie Breaking

If effective scores are equal, preserve the existing waiting deque order.

## Complexity

Preserve O(n) candidate selection.

Do not sort the waiting deque globally.

## Resource Checks

After candidate selection, preserve all current allocation and budget checks.

Do not add fallback to another candidate when the selected request fails an
existing resource check.

## Starvation Reasoning

Explain whether an old request eventually gains priority over newly arriving
finite-length requests.

State assumptions and limitations.

Do not claim starvation freedom under resource infeasibility or unlimited
preemption.

## Evaluation Plan

Define tests for:

- zero waiting reproduces short_prompt ranking
- score improves monotonically with waiting time
- stable equal-score ties
- old long request eventually outranks new short request
- baseline unchanged
- short_prompt unchanged
- telemetry on/off does not affect decisions
- preemption/requeue aging semantics
- no future information used

Define later fairness diagnostics:

- long-request queue wait
- long-request TTFT
- long-request E2E
- maximum queue wait
- near-starvation count

## Output

Create:

docs/aging-policy-design.md

Include:

1. starvation problem
2. score formula
3. units
4. crossover derivation
5. proposed aging parameter
6. waiting-time origin
7. preemption semantics
8. scheduler-owned state
9. tie-breaking
10. complexity
11. assumptions and limitations
12. implementation locations
13. CPU test plan
14. GPU validation plan

## Restrictions

Do not:

- implement aged_short_prompt
- modify scheduler behavior
- change formal traces
- run formal policy benchmarks
- modify KV-cache behavior
- change dependencies

## Validation

Run:

git diff --check
git status --short

Confirm nanovllm/ is unchanged.

## PROJECT_STATE

Update PROJECT_STATE.md with:

- AGING-001 completion
- aging semantics
- proposed parameter
- next recommended task

## Acceptance Criteria

- starvation is clearly defined
- formula and units are explicit
- aging parameter has an interpretable crossover meaning
- waiting-time semantics are explicit
- preemption semantics are explicit
- telemetry is not required for correctness
- stable ties are preserved
- O(n) selection is preserved
- limitations are documented
- no scheduler behavior changed
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- score formula
- aging rate and crossover interpretation
- waiting-time origin
- preemption/requeue semantics
- tie-breaking
- complexity
- starvation guarantee and limitations
- proposed implementation files
- files modified
- recommended next step
