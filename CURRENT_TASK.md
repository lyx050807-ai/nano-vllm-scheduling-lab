# CURRENT_TASK.md

## Task ID

REPLAY-002

## Title

Integrate timed trace replay with nano-vLLM and lifecycle telemetry.

## Goal

Connect the validated request replay layer to the instrumented nano-vLLM
engine while preserving request arrival timing independently from blocking GPU
engine steps.

This is an integration task for the existing baseline scheduler.

Do not implement a new scheduling policy.

## Required Reads

Read:

- AGENTS.md
- PROJECT_STATE.md
- docs/architecture.md
- docs/trace-spec.md
- docs/telemetry-spec.md
- scripts/replay_trace.py
- nanovllm/telemetry.py
- workloads/dev_trace.jsonl

Inspect the current engine API before implementation.

## Architecture Requirement

Use two roles:

1. Replay producer thread
   - releases requests according to trace arrival_s
   - never calls nano-vLLM engine methods
   - places released requests into a thread-safe admission queue

2. Engine coordinator/main thread
   - exclusively owns LLMEngine
   - drains the admission queue
   - calls add_request()
   - calls engine.step()
   - collects completed outputs and telemetry

Do not call LLMEngine concurrently from multiple threads.

## Shared Clock

Use one shared monotonic perf_counter_ns clock domain and one shared t0_ns.

Replay release timestamps and engine telemetry timestamps must be directly
comparable.

If useful, extend replay_trace.py to accept an externally supplied t0_ns while
preserving existing behavior and tests.

## Warmup

Before the formal development replay:

- initialize the model/engine
- run one small warm-up request with telemetry disabled
- confirm the engine is idle
- then establish the shared experiment t0_ns
- enable telemetry
- run the development trace

Warm-up data must not appear in the development trace results.

## Replay / Admission Behavior

During engine.step(), the replay producer must remain able to release future
requests into the admission queue.

After each engine step, the coordinator should admit queued requests before the
next engine step where practical.

When the engine is idle and no request is currently available, avoid a
high-CPU busy-wait loop.

Preserve stable trace order for requests released at the same arrival time.

## Request Identity

Pass the trace request_id through to LLMEngine.add_request().

Use request_id to join:

- trace metadata
- planned arrival
- actual release
- engine telemetry
- completion/output data

## Development Configuration

Use the existing local Qwen3-0.6B model.

Use a conservative configuration appropriate for the RTX 4050 and the existing
development trace.

Prefer the previously validated small-context/single-sequence configuration
unless repository evidence requires a change.

Do not treat this configuration as the frozen formal benchmark.

## Joined Output

Create a joined per-request JSONL record under:

artifacts/replay/

Each completed request record should include at least:

- request_id
- prompt_class
- num_prompt_tokens
- max_new_tokens
- planned_arrival_s
- release_s
- admitted_s
- first_scheduled_s
- first_prefill_dispatch_s
- first_token_s
- finished_s
- output_token_count
- generated text or a concise output field

Compute:

- replay_error_ms
- admission_overhead_ms
- queue_wait_ms
- ttft_ms
- engine_ttft_ms
- e2e_latency_ms

Use the formulas defined in docs/telemetry-spec.md.

Do not use planned_arrival_s as the primary TTFT/E2E origin.

## Required Invariants

For every completed request:

release_s <= admitted_s
admitted_s <= first_scheduled_s
first_scheduled_s <= first_prefill_dispatch_s
first_prefill_dispatch_s <= first_token_s
first_token_s <= finished_s

Token timestamps must be nondecreasing.

All 12 development requests must be accounted for exactly once.

## CPU Tests

Add tests using a fake/mock engine where useful.

Include a test that simulates a blocking engine step and verifies the replay
producer can still release a later request while the engine coordinator is
blocked.

Also test:

- request_id joins
- metric calculations
- shared t0 behavior
- no duplicate/lost requests
- stable same-arrival ordering

CPU tests must not require the GPU.

## GPU Integration Run

After CPU tests pass, run the development trace on the existing local
Qwen3-0.6B engine.

This run validates integration only.

Do not present its latency as formal benchmark results.

Record:

- request count
- completion count
- trace SHA256
- lifecycle invariant result
- basic diagnostic latency summary
- any errors/warnings

## Restrictions

Do not:

- implement short_prompt
- implement aging
- change waiting queue ordering
- change running queue ordering
- change KV-cache policy
- change model execution or sampling semantics
- change dependency versions
- download another model

## Validation

Run:

git diff --check
git status --short

Run relevant CPU tests and the development GPU integration.

Review any nanovllm/ diff carefully.

## PROJECT_STATE

Update PROJECT_STATE.md with:

- REPLAY-002 completion
- integration architecture
- tests run
- GPU development replay result
- next recommended task

## Acceptance Criteria

- replay timing remains independent of blocking engine steps
- only the coordinator thread calls LLMEngine
- replay and telemetry share one clock/t0
- all 12 requests complete exactly once
- joined timing records are produced
- lifecycle invariants hold
- metric formulas match telemetry spec
- CPU tests pass
- GPU integration passes
- baseline scheduler semantics remain unchanged
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- integration architecture
- shared clock/t0 design
- files modified
- CPU test count/results
- GPU request/completion count
- trace SHA256
- example joined request record
- latency diagnostics
- invariant results
- warnings/errors
- recommended next step
