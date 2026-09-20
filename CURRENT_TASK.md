# CURRENT_TASK.md

## Task ID

BENCH-001

## Title

Freeze the formal benchmark and comparison protocol.

## Goal

Define the formal workload, repetition, run-order, metadata, timeout, and
comparison rules before implementing any new scheduling policy.

Do not implement short_prompt or aging in this task.

## Required Reads

Read:

- AGENTS.md
- PROJECT_STATE.md
- docs/trace-spec.md
- docs/telemetry-spec.md
- artifacts/baseline/dev-baseline-summary.json
- scripts/make_trace.py
- scripts/run_replay.py

## Development Baseline Context

The 12-request development trace and BASELINE-001 results are validation data,
not formal benchmark data.

Use them only to inform safe experiment sizing and infrastructure design.

## Formal Workload Design

Define a formal mixed-length workload with substantially more requests than
the 12-request development trace.

Target a balanced prompt-class design such as:

- 20 short requests
- 20 medium requests
- 20 long requests

for 60 requests per trace, unless repository/hardware evidence shows this is
unsafe.

Preserve the existing tokenizer-verified prompt length methodology.

Use multiple fixed trace seeds rather than relying on one request ordering.

Prefer at least 3 fixed formal trace seeds.

## Load Calibration

Before freezing arrival timing, perform baseline-only calibration if needed.

The goal is to create meaningful queue contention while maintaining:

- 100% request completion
- no OOM
- no experiment timeout
- lifecycle invariants
- nontrivial waiting-queue behavior

Do not select a workload based on whether a future scheduling policy performs
well on it.

Document any calibration procedure and the criteria used before freezing the
formal workload.

## Comparison Protocol

Define the future comparison for:

- baseline
- short_prompt
- aged_short_prompt

Every policy must use identical:

- model and revision
- trace and trace SHA256
- generation configuration
- engine configuration
- prompt contents
- arrival schedule
- output limits

Use paired comparisons by trace seed.

Plan at least 5 repeated runs per policy/trace combination for the final
benchmark unless later runtime evidence justifies a documented change.

## Run Order

Do not always run all baseline trials first and all policy trials later.

Define a rotated or randomized run order so GPU thermal/power drift is less
likely to systematically favor one policy.

Each measured run must use the same warm-up procedure.

## Metrics

Primary:

- TTFT
- queue_wait
- E2E latency

Secondary:

- engine TTFT
- admission overhead
- ITL
- completion rate
- throughput

Report overall results and results by:

- short
- medium
- long

Include both central tendency and tail behavior where sample size supports it.

Do not make inferential/statistical claims from the 12-request development
baseline.

## Fairness

Define long-request fairness diagnostics.

The protocol must be able to detect whether short-request improvements cause:

- increased long-request queue wait
- increased long-request TTFT
- increased long-request E2E
- starvation or near-starvation

## Timeout / Failure Rules

Freeze explicit rules for:

- experiment timeout
- request failure
- incomplete request
- OOM
- partial artifact preservation

Failed runs must not silently enter the successful performance summary.

## Reproducibility Metadata

Every formal run must record:

- project Git commit
- upstream commit
- model revision
- trace SHA256
- trace seed
- policy
- engine configuration
- generation configuration
- run ID
- environment metadata
- completion count

## Output

Create:

docs/benchmark-protocol.md

If formal trace-generation changes are required, document them but do not
implement scheduling policies.

Clearly distinguish:

- development validation workload
- formal benchmark workload

## Restrictions

Do not:

- implement short_prompt
- implement aging
- modify scheduler ordering
- modify KV-cache behavior
- modify model execution
- change dependencies

If calibration discovers a hardware or infrastructure blocker, report it
rather than silently weakening the protocol.

## Validation

Run:

git diff --check
git status --short

Confirm baseline scheduler semantics remain unchanged.

## PROJECT_STATE

Update PROJECT_STATE.md with:

- BENCH-001 completion
- frozen comparison protocol
- formal workload plan
- next recommended task

## Acceptance Criteria

- formal workload design is specified
- fixed trace seeds are specified
- repetition count is specified
- policy run ordering is controlled
- warm-up procedure is fixed
- metrics are fixed
- fairness metrics are fixed
- timeout/failure rules are fixed
- reproducibility metadata is fixed
- no scheduling policy is implemented
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- formal request count/classes
- trace seeds
- arrival/load design
- repetition plan
- run-order design
- metrics
- fairness diagnostics
- timeout/failure rules
- files modified
- recommended next step
