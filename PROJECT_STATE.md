# PROJECT_STATE.md

Last updated: 2026-09-21

## Current Phase

ENV-001 through ENV-007, MODEL-001, SMOKE-001, ARCH-001, TRACE-001/002 and
REPLAY-001/002, TELEMETRY-001/002, BASELINE-001, BENCH-001/002 and
POLICY-001/002, AGING-001/002 and BENCH-003/004 complete. The formal-mixed-v1 traces and
baseline capacity gate are validated. Baseline, short_prompt and
aged_short_prompt are implemented and passed CPU and 12-request GPU functional
smoke. The frozen 45-run formal benchmark is complete; its raw results and
paired per-run summary are preserved under artifacts/formal-benchmark/.

## Current Git Branch

codex/scheduling-lab

## Upstream Project

nano-vLLM

Repository:

GeeeekExplorer/nano-vllm

The exact upstream commit is stored in:

artifacts/environment/upstream-commit.txt

## Project Goal

Build a reproducible single-GPU experiment based on nano-vLLM to study
waiting-queue scheduling under mixed prompt lengths.

The planned scheduling policies are:

1. baseline
2. short_prompt
3. aged_short_prompt

Primary performance dimensions:

- TTFT
- scheduling wait time
- long-request waiting behavior
- throughput
- ITL
- completion rate

## Hardware Known So Far

GPU:

NVIDIA GeForce RTX 4050 Laptop GPU

VRAM:

6141 MiB reported by nvidia-smi

Development environment:

WSL2
Ubuntu 24.04

## Completed

- BENCH-004 executed the unchanged 45-entry formal manifest in its precomputed
  order: 15 runs each for baseline, short_prompt and aged_short_prompt, with
  five repetitions for each policy/seed combination. All 45 independent
  attempts exited successfully; 2700/2700 measured requests completed,
  including 20 short, 20 medium and 20 long requests per run. There were no
  timeout, OOM, runner or lifecycle failures and no retries. The first run
  started 2026-09-21 06:07:08 UTC and the last finished 07:01:09 UTC,
  for 3240.755 s elapsed wall time. Execution used project commit
  f582364e1248a3b1f9ec241c07c4895eac75783f; the manifest's frozen
  plan-creation commit remains 86d088d1ec6243cbed71fcb9c94bed47727005d6.
  Source and workload content were unchanged between those commits.
- Preflight provenance is in artifacts/formal-benchmark/preflight.json. Raw
  requests, progress, logs and metadata are retained in 45 unique
  artifacts/formal-benchmark/runs/<run_id>/ directories; terminal outcomes
  are checkpointed in manifest.json. The independent validation record is
  artifacts/formal-benchmark/validation.json. It confirms run order, unique
  IDs/paths, one attempt per run, all request identities and counts, exclusion
  of the telemetry-disabled warm-up, correct policy/aging metadata, unchanged
  trace/sidecar and source hashes, and passed lifecycle invariants.
- Frozen aggregation produced artifacts/formal-benchmark/summary.json with
  all 45 per-run summaries, 45 outcomes and 15 complete `(trace_seed,
  repeat_index)` paired keys. Mean of the 15 run-level overall means by
  baseline/short_prompt/aged_short_prompt respectively: TTFT
  86.432/84.776/83.265 ms, queue wait 49.038/46.942/45.775 ms, and E2E
  9013.483/9027.648/9080.995 ms. These are descriptive summaries, not a
  policy superiority claim. Full short/medium/long, engine TTFT, admission
  overhead, ITL, completion and throughput values remain in the summary.
- One timing anomaly is preserved: seed303/rep4/baseline took 615.544 s by
  UTC wall timestamps versus 21.875 s recorded monotonic observation time.
  It still completed 60/60 and passed lifecycle audit; the cause of the
  wall/monotonic discrepancy has not been established. Formal runner metadata
  also retains a generic timing note mentioning calibration/development data
  despite `mode=formal-measurement`; the mode and provenance fields are
  correct. No measurement or metadata was rewritten. Next task: offline
  paired analysis of the frozen 15 keys, including class-specific latency,
  long-request fairness and sensitivity to the timing anomaly.

- BENCH-003 added scripts/formal_benchmark.py and
  scripts/aggregate_formal.py. The orchestrator freezes 45 measured runs:
  three policies by seeds 101/202/303 by five repetitions. It uses the
  benchmark protocol's repetition-major, seed-order blocks and rotates policy
  order by `(repeat_index + seed_index) mod 3`, placing each policy in each
  block position five times. Deterministic run IDs have the form
  `formal-mixed-v1-seed<seed>-rep<0..4>-<policy>`. The precomputed manifest is
  artifacts/formal-benchmark/manifest.json; all 45 entries include explicit
  identity, frozen trace and sidecar hashes, project/upstream/model/config provenance,
  policy parameter, status, completion placeholder and unique artifact path.
- The formal orchestrator creates the manifest and run directories
  exclusively, starts one fresh run_replay process per pending entry, retains
  progress/log/request metadata, enforces the frozen 90 s coordinator and
  150 s process cutoffs plus 30 s cooldown measured from the previous process
  exit, records the actual inter-run gap, and checkpoints terminal results.
  Resume skips all terminal success/failure entries by default; an interrupted
  running entry is recorded as runner failure and stops automatic launching
  until its child process and partial artifacts are inspected. Failure states
  distinguish timeout, OOM, runner/infrastructure failure and lifecycle
  failure. Explicit external-infrastructure retries use non-overwriting
  attempt directories with retry relationships; failures are never silently
  replaced. run_replay only gained the formal-measurement mode label; scheduler
  and policy source are unchanged.
- The read-only aggregation utility retains per-run latency values and
  mean/median/p95/max summaries overall and by short/medium/long for TTFT,
  queue wait, E2E, engine TTFT and admission overhead; it also prepares ITL,
  completion, full-run throughput and `(trace_seed, repeat_index)` paired keys.
  No policy comparison or superiority claim was produced. Dry-run/list mode
  validated exactly 45 pending runs, five for every policy/seed pair, unique
  IDs/paths, deterministic order and all frozen hashes without importing the
  model, using the GPU or creating run directories. The full CPU suite passed
  71/71. Additional tests cover interrupted-run reconciliation and safe stop,
  cooldown timing, frozen
  success identity/completion audit, failed-run outcome denominators and
  loading the original plan after a later project commit. No formal GPU run
  was executed.

- AGING-002 implemented the AGING-001 design in nanovllm/config.py,
  nanovllm/engine/waiting_policy.py and nanovllm/engine/scheduler.py. The
  accepted policies are baseline, short_prompt and aged_short_prompt, with
  baseline still the default. Invalid policy names and any aging rate other
  than the frozen integer 320 tokens/second fail clearly. The aged selector
  scans the waiting deque once, compares exact integer nanosecond-scaled
  scores, and keeps the leftmost entry on ties. Scheduler-owned
  `seq_id -> first_enqueue_ns` state uses perf_counter_ns (injectable in CPU
  tests), is recorded at first waiting enqueue, survives partial prefill and
  preemption/requeue, and is deleted on permanent finish. Age includes running
  time before a later preemption and is separate from telemetry queue_wait_ms.
  Baseline and short_prompt do not read the aging clock or use this state.
  Resource failure still stops without backfill; running/decode, KV cache,
  model execution and sampling logic were not changed.
- AGING-002 runner integration in scripts/run_replay.py accepts the aged
  policy and records the policy, fixed rate, and scheduler/selector/config
  source hashes in development smoke manifests. The full CPU suite passed
  59/59, including deterministic 0.2/0.3/0.5 s crossover boundaries, stable
  ties, preemption age retention, cleanup, partial prefill, no backfill,
  telemetry independence, no future information, and baseline/short_prompt
  regressions. The targeted 192-token vs 32-token scenario selected the old
  long request after a 0.6 s first-enqueue gap without using GPU timing.
- Three independent fresh-process development GPU smoke runs on the unchanged
  12-request trace completed 12/12 each for baseline, short_prompt and
  aged_short_prompt. All exited 0 with no timeout, OOM, lifecycle violation,
  duplicate/missing request ID or observed warning/error. Records and
  manifests had the expected policy labels, fixed 320 rate, valid timestamp
  order, and the same trace SHA256
  28f070031f63d3e0fc4d79accc25cd5df75c5b2e370e62e78da0c6822718d041.
  Logs, joined records and summary are preserved under
  artifacts/policy-smoke/aging002-20260921T020400166498Z/. These are
  functional diagnostics, not a policy performance comparison; no formal
  45-run benchmark was executed.

- AGING-001 completed as design only: docs/aging-policy-design.md defines
  `aged_short_prompt` score as original prompt tokens minus 320 tokens/second
  times request age since first entry into the scheduler waiting deque. This
  age can include running time before a later preemption and is separate from
  telemetry `queue_wait_ms`. The parity differences remain 0.2 s for 96-vs-32,
  0.3 s for 192-vs-96 and 0.5 s for 192-vs-32. The chosen origin is retained
  across partial prefill and preemption/requeue. A
  scheduler-owned monotonic first-enqueue timestamp, independent of optional
  telemetry, is proposed; stable deque ties, O(n) selection and existing
  no-backfill resource behavior are preserved. The rate derives from frozen
  prompt classes and an interpretable half-second crossover, not policy
  outcomes. No policy was implemented, no formal benchmark ran, and nanovllm/
  remains unchanged.

- POLICY-002 completed: nanovllm/engine/waiting_policy.py provides a pure O(n) shortest-original-prompt selector with leftmost deque tie-breaking; Config accepts only baseline/short_prompt and defaults to baseline. Scheduler uses the existing index-zero/popleft baseline path and removes a non-head short_prompt candidate only after the existing successful final-prefill check. Allocation/budget failure still breaks without backfill. Running/decode, KV-cache, model/sampling and preemption logic are unchanged; telemetry remains observational.
- CPU validation: `.venv/bin/python -m unittest discover -s tests -v` passed 51/51 tests. New tests cover default/invalid configuration, baseline trajectory, stable 192/32/96/32 -> 32/32/96/192 selection, non-head removal, no backfill on allocation failure, first-only chunk budget, partial prefill, preempted original prompt length, telemetry independence, unchanged decode ordering, and policy labels in joined records. Existing trace/replay/telemetry tests passed.
- Development GPU smoke: both baseline and short_prompt completed 12/12 on unchanged workloads/dev_trace.jsonl (SHA256 28f070031f63d3e0fc4d79accc25cd5df75c5b2e370e62e78da0c6822718d041) using the same engine/generation settings except policy. Both exited 0 without OOM, timeout, lifecycle violation or observed warnings/errors. Final observation durations were 3.974 s baseline and 3.793 s short_prompt; these are functional diagnostics, not performance claims. Baseline first-scheduled order matched trace order. Short_prompt first scheduled dev-000003 (32 tokens) before dev-000001 and dev-000002 (96 tokens); later mixed-length arrival groups also reordered. Full joined records/logs and final order summary: artifacts/policy-smoke/policy002-smoke-final-summary.json and its run directories. An earlier passing smoke pair and its summary are preserved after moving the new Config field to the end to retain positional compatibility. No formal 45-run benchmark was executed.

- POLICY-001 completed as design only: docs/scheduling-policy-design.md specifies a candidate-index selector for the waiting deque. Default baseline remains the exact current head-of-deque/popleft path, including partial prefill, preemption and head-of-line resource failure. Future short_prompt scans waiting requests for minimum original num_prompt_tokens and uses current deque order for stable ties; a selected candidate still goes through the existing allocation/budget checks with no feasibility backfill. Non-head final-prefill removal is proposed without sorting the deque. Future aging needs scheduler-owned monotonic wait state independent of optional telemetry; no formula is chosen.
- The design limits policy scope to waiting candidate selection, documents O(1) baseline and O(n) scan/deletion complexity, configuration validation, invariants, insertion points and CPU/GPU test plan. No nanovllm source, scheduler behavior, dependencies, formal traces or benchmark results changed. No policy benchmark ran.

- BENCH-002 completed: scripts/make_formal_trace.py generates and validates the frozen formal-mixed-v1 packages without changing the development generator. Each of three traces has 60 requests (20 short, 20 medium, 20 long), exact tokenizer-verified 32/96/192-token prompts, cap 16, and groups of three every 250 ms. Same-seed independent regeneration was byte-identical; all three seed class orders differ. The generic trace validator, strict formal sidecar/recipe validator and replay loader passed; the full CPU suite passed 40/40.
- Formal trace and sidecar SHA256 pairs registered in docs/benchmark-protocol.md: seed 101 workloads/formal_trace_seed101.jsonl ff3acfd57a153030e76d06af491fed20bd1498db7e12580db345c8bb1ff92ac8 / fb298e8ba8019d86e54c62487eb5906e0a59d9889ca5ca73881560f53e0b1476; seed 202 workloads/formal_trace_seed202.jsonl e3c82a96d5b7295b7e98d4d4884476ddd9cc5ee1701831f4d5e63e8872e94078 / 8603718474005a5dc3f18fac2b76cd4e37d23252dd19ea124c5f34734d95ebfc; seed 303 workloads/formal_trace_seed303.jsonl 8721930601de3f96d23287cef9038a0967f653133987a154ca18ae8e5b4d6866 / af6d5affaf40cbd7e72a0961d37d10dcdbe59664ce8a563e954ec844862d4526.
- Baseline-only 60-request calibration used fresh engines, the existing warmup/seed/configuration, 90 s coordinator cutoff and 150 s process watchdog. All seeds completed 60/60, no OOM, timeout, lifecycle violation, duplicate/missing ID or observed warning/error. Observation durations after t0: seed 101 19.375 s, 202 19.476 s, 303 20.055 s; total process wall times 30.339/29.646/29.783 s. Peak Torch allocated/reserved bytes: 2636926464/2707423232 in each run. These are allocator statistics, not whole-device residency.
- Frozen contention gate passed: each seed had 60/60 positive queue waits and 40/60 >=20 ms; requests >=100 ms were 1/2/2. Queue wait mean/median/max ms: seed 101 27.292/24.187/225.997; seed 202 33.299/25.338/442.438; seed 303 34.658/25.664/458.791. Per-class diagnostics and raw logs/records are in artifacts/calibration/formal-mixed-v1/capacity-summary.json and separate run directories. These are capacity/calibration runs, not measured formal benchmark trials.
- Only formal trace generation/validation, replay profile dispatch and calibration mode/memory metadata were changed. No nanovllm source, scheduler, KV-cache, model execution, dependency or development trace was changed. No Git commit was created.

- BENCH-001 completed: docs/benchmark-protocol.md freezes formal-mixed-v1 as three 60-request traces (20/class), construction seeds 101/202/303, exact 32/96/192-token prompt recipe, cap 16, groups of three every 250 ms, pinned Qwen3-0.6B revision and conservative engine/sampling settings. The 12-request development trace/results remain separate.
- Comparison protocol: five repetitions per seed/policy (45 measured runs), three-policy blocks rotated by seed/repetition so each policy occupies each position five times, identical warmup and 30 s between fresh processes. Paired run-level comparisons, primary release-based TTFT/E2E and initial queue wait, secondary ITL/throughput/completion and prespecified long-request fairness are defined. Coordinator timeout 90 s, process watchdog 150 s, partial artifact/failed-run rules and required provenance are fixed.
- This task did not generate formal packages or run a 60-request GPU calibration. Before policy measurement, the separately scoped formal generator/validator must create the three packages and register both hashes, then baseline-only capacity checks must pass 60/60 with no OOM/timeout and the predeclared contention criteria. A failure requires reporting the blocker and a new profile version for changed parameters, not silent relaxation. No scheduling policy or nano-vLLM source was changed.

- BASELINE-001 completed: scripts/run_replay.py now enforces a coordinator observation deadline, records partial request outcomes on failure/timeout, and durably checkpoints progress after completed batches. scripts/run_baseline_trials.py launches three fresh engine processes with separate warmups, unique run IDs/directories and a process watchdog for GPU steps that do not return. Hard process termination uses the last durable snapshot; unknown terminal times stay null and incomplete requests are explicitly failed, never counted as completed.
- Final accepted trials: dev-baseline-20260920T120738893837Z-bdd3f160, dev-baseline-20260920T120752251324Z-85cfca31, dev-baseline-20260920T120806449035Z-1c3c4440. Each completed 12/12 with no observed errors/warnings. CPU suite: 38/38 passed. Trace SHA256 was identical: 28f070031f63d3e0fc4d79accc25cd5df75c5b2e370e62e78da0c6822718d041. Model/tokenizer revision, engine/sampling options, project/upstream commits, request IDs/metadata and lifecycle checks were identical/valid. Baseline scheduler and development trace were unchanged.
- Final run mean milliseconds: TTFT 65.778/62.248/57.202; E2E 1960.832/1941.339/1939.483; queue wait 27.865/25.155/26.779. Range of run means: TTFT 8.577 ms, E2E 21.349 ms, queue wait 2.710 ms. All six metrics have mean/median/max by run and prompt class (n=4/class) in artifacts/baseline/dev-baseline-summary.json. These values describe small development runs only and support no statistical performance claim.
- An initial three trial set was preserved with its exact runner source and summary under artifacts/baseline after a correction to hard-crash terminal semantics. The final accepted three use the current runner source; per-run source hashes match. No prior run directory was overwritten.

- REPLAY-002 completed: scripts/run_replay.py connects the independent arrival producer through an unbounded thread-safe FIFO admission queue to the sole engine coordinator. Queued arrivals are admitted before the next step; idle coordinator blocks on Queue.get(). No nanovllm source or baseline ordering changed.
- Replay and engine telemetry use the same perf_counter_ns clock and t0_ns. One four-token warmup runs with telemetry disabled before establishing t0; warmup is excluded from joined results. The existing replay API retains default behavior and gains an optional external origin/release hook and cooperative cancellation.
- CPU validation: `.venv/bin/python -m unittest discover -s tests -v` passed all 35 tests (8 new integration tests). Coverage includes release during a blocked engine step, exclusive engine ownership, shared origin, stable same-arrival order, exact joins, release-based metric formulas, producer errors and cancellation.
- GPU validation: `.venv/bin/python scripts/run_replay.py` exited 0; all 12 requests completed exactly once, with lifecycle and nondecreasing token timestamp checks passing. Saved JSONL was independently checked for six metric formulas, trace hash, identity/counts and timestamp ordering. No warnings/errors were observed.
- Artifacts: artifacts/replay/dev_engine_replay.jsonl, dev_engine_replay.meta.json and dev_engine_replay.log.txt. Metadata records model/tokenizer identity, sampling, configuration, warmup, shared clock, project/upstream revisions and source hashes. Trace SHA256: 28f070031f63d3e0fc4d79accc25cd5df75c5b2e370e62e78da0c6822718d041.
- Development engine configuration: local Qwen3-0.6B; eager=True, tensor_parallel_size=1, max_model_len=256, max_num_batched_tokens=256, max_num_seqs=1, gpu_memory_utilization=0.6. Trace sampling remains temperature=0.6, ignore_eos=False, max_new_tokens=16, inference_seed=42.
- Diagnostic mean/max milliseconds: replay error 0.199524/0.442302; admission overhead 6.763655/15.975741; queue wait 23.107351/49.547368; TTFT 52.796690/84.237275; engine TTFT 46.033035/71.257523; E2E 1738.603030/2999.947949. These are development integration diagnostics, not formal benchmark results. TTFT/E2E start at actual release; planned arrival remains workload intent.
- Limits: OS/GIL scheduling can delay release; the producer is independent of engine service but is not real-time. This integration captures completed runs and propagates failures; a timeout/incomplete-record finalization layer is not yet implemented. No dependency changes or Git commit were made.

- TELEMETRY-002 completed: nanovllm/telemetry.py captures in-memory monotonic lifecycle events; llm_engine.py and scheduler.py contain opt-in hooks only.
- Events: admission, first successful scheduling, first prefill dispatch, first output token, every valid output token and completion after KV deallocation/running removal. First-event timestamps survive rescheduling/preemption.
- Request IDs are associated at add_request; completed or incomplete detached records are available through get_telemetry. No per-token file writes or GPU synchronization were added.
- 27 CPU tests passed (19 existing trace/replay tests and 8 telemetry tests). Real scheduler/BlockManager tests cover chunked prefill, EOS completion and forced preemption with capture enabled/disabled.
- Conservative GPU smoke passed with the same model, prompt, engine options and seed: nonempty output, 10 output tokens, valid lifecycle ordering, nondecreasing token timestamps, no observed warnings/errors.
- Evidence: artifacts/telemetry/smoke-completed.jsonl and artifacts/telemetry/smoke-regression.txt. Earlier runtime records remain unchanged.

- TELEMETRY-001 completed: docs/telemetry-spec.md defines the common monotonic clock, lifecycle capture points, JSONL record schema, latency/ITL formulas, failure/null behavior and candidate hook locations.
- Primary TTFT and E2E start at actual replay release_s; TTFT includes admission overhead and queue waiting. Planned arrival remains workload intent, with replay error reported separately; engine TTFT and initial queue wait retain their definitions. Telemetry remains specification-only; no hooks, policy or GPU changes.

- REPLAY-001 completed: scripts/replay_trace.py validates the trace package before establishing t0 and releases requests at absolute monotonic targets through a CPU dry-run/callback interface.
- Ten replay tests plus nine trace tests passed (19 total); stable ordering, exactly-once normal dispatch, callback delay, oversleep, early wakeup, overdue requests and invalid input are covered.
- One real-clock dry-run released all 12 development requests; diagnostics are preserved in artifacts/replay/dev_replay_timing.jsonl.
- REPLAY-001 did not connect to nano-vLLM/GPU or implement telemetry/scheduling; source, dependencies and input trace package remain unchanged.

- TRACE-002 completed: scripts/make_trace.py generates and independently validates request-trace-v1/dev-mixed-v1 using the pinned local tokenizer on CPU.
- Default workloads/dev_trace.jsonl and workloads/dev_trace.meta.json generated with explicit seed 42: 12 requests, four per class, exact 32/96/192 prompt tokens, output cap 16.
- Same-seed temporary outputs were byte-identical with equal SHA256; seed 43 changed the shuffled prompt-class assignment. Nine CPU tests passed.
- No nano-vLLM source, dependency, replay, telemetry or scheduling-policy changes were made in TRACE-002.

- TRACE-001 completed: docs/trace-spec.md defines versioned JSONL, arrival/tokenization semantics, scheduler information boundaries, reproducibility, validation and a development-only workload.
- TRACE-001 is specification only; generator, replay, telemetry and policies remain unimplemented. Formal benchmark parameters remain unfrozen.

- ARCH-001 completed: source-backed request lifecycle, queue behavior, prefill/decode, KV ownership and candidate waiting-policy insertion point documented in docs/architecture.md.
- ARCH-001 was documentation only; no nano-vLLM source, dependency or scheduling behavior changes.

- WSL2 installed and validated.
- Ubuntu 24.04 installed.
- NVIDIA GPU visible inside WSL.
- Git available inside WSL.
- nano-vLLM cloned into the Linux filesystem.
- upstream remote configured.
- development branch created.
- upstream nano-vLLM commit recorded.
- initial project directory structure created.
- SMOKE-001 completed on attempt 3 after user-installed host compiler and Python development headers; same model/config/script, one request passed.
- Previous failed attempts and successful output preserved in artifacts/environment/smoke-single-request.txt.
- MODEL-001 completed: Qwen/Qwen3-0.6B downloaded to models/Qwen3-0.6B.
- Model revision: c1899de289a04d12100db370d81485cdf75e47ca.
- Local config/tokenizer encode-decode and weight/tokenizer SHA256 validation passed; evidence in artifacts/environment/model-info.txt.
- ENV-007 completed: nano-vllm 0.2.0 installed locally in editable mode with dependency resolution disabled.
- ENV-007 isolated imports from outside the repository, editable metadata and pip check passed; all pre-existing package versions preserved.
- ENV-007 evidence: artifacts/environment/nanovllm-install-info.txt.
- ENV-006 completed: FlashAttention 2.7.4.post1 official cp312/cu12/torch2.6/cxx11abiFALSE wheel installed in .venv, with einops 0.8.2.
- ENV-006 imports, pip check and two small FlashAttention GPU API tests passed; Torch/Triton preserved.
- ENV-006 source URL, wheel SHA256, installation and validation evidence: artifacts/environment/flash-attn-info.txt.
- ENV-005 completed: ordinary runtime dependencies installed in .venv with torch/triton constraints.
- ENV-005 imports, offline Qwen3 config dtype, pip check, and GPU matmul validation passed.
- ENV-005 evidence and resolved versions: artifacts/environment/runtime-deps-info.txt.
- ENV-004 completed: installed torch 2.6.0+cu124 and its dependencies only in .venv; GPU matrix multiplication passed.
- ENV-004 evidence and package inventory: artifacts/environment/pytorch-gpu-info.txt.
- ENV-003 completed: concrete GPU stack plan documented in docs/gpu-stack-plan.md.
- ENV-001 completed: repository requirements and local environment inspected.
- ENV-002 completed: recreated and activated the project-local .venv using Python 3.12.3.
- Verified Python and pip resolve from .venv, isolation is enabled, and Git ignores .venv.
- ENV-002 evidence, including the earlier failed attempt, is in artifacts/environment/venv-info.txt.
- Environment evidence recorded in docs/environment.md and artifacts/environment/system-info.txt.

## In Progress

No measured formal performance comparison has run. The three-seed baseline
capacity gate passed, all policies are functionally validated, and the frozen
45-run manifest/orchestrator is dry-run validated. Formal GPU execution and
offline analysis remain separately scoped.

## Not Started

- formal experiments and offline analysis
- final report

## Known Issues

System Python is Python 3.12.3.

The missing ensurepip prerequisite was resolved by the user installing
python3.12-venv (3.12.3-1ubuntu0.17). The incomplete environment was removed
and recreated at /home/luoyuxuan/projects/nano-vllm-scheduling-lab/.venv.
Activated Python and pip resolve to .venv/bin/python and .venv/bin/pip.
PyTorch, its declared dependencies and ordinary runtime dependencies are installed
in .venv; system Python
has no torch module. System site-packages are excluded.

Python 3.12.3 satisfies the pinned repository requirement >=3.10,<3.13.
Installed stack: PyTorch 2.6.0+cu124, reported CUDA runtime 12.4, Triton 3.2.0.
Measured Torch C++ ABI is False. CUDA is available; one RTX 4050 Laptop GPU
with compute capability 8.9 was detected. A 4x4 CUDA matrix multiplication
(A @ 2I == 2A) passed after synchronization, with result on cuda:0.
PyTorch reported total memory 6438780928 bytes and free memory 5272240128
bytes at the validation snapshot; these are not workload capacity guarantees.
FlashAttention 2.7.4.post1 is installed from the official
cp312/cu12/torch2.6/cxx11abiFALSE Linux wheel; einops 0.8.2 was its only
new dependency. All pre-existing packages were constrained during installation.
The dependency combination passed one conservative single-request inference;
broader workload/configuration compatibility remains unvalidated.
The initial missing C compiler and subsequent missing Python.h blockers were
resolved by user-installed gcc/g++ 13.3.0 and python3.12-dev 3.12.3-1ubuntu0.17.
Attempt 3 completed normally with no runtime warnings or errors. Historical
constructor failures and NCCL cleanup warnings remain in the runtime record.
No Python dependency or source changes were required.
No system CUDA Toolkit is needed for the initial prebuilt-wheel path.
No CUDA Toolkit was installed. Basic PyTorch GPU computation is now validated;
FlashAttention API tests passed. SMOKE-001 exercised the engine warmup,
Triton execution, single-GPU NCCL setup/cleanup and cached decoding on this
one-request path; this is not comprehensive kernel/integration validation.
Source-build fallback requires a separate Toolkit/compiler assessment.
ENV-005 installed transformers 4.57.6, xxhash 4.0.1, numpy 2.5.3,
tqdm 4.70.1 and safetensors 0.8.0 plus their resolved dependencies.
Transformers 4.57.6 was chosen within the 4.x API family with config.dtype
support. Offline AutoConfig.for_model('qwen3', torch_dtype='bfloat16') produced
Qwen3Config.dtype == torch.bfloat16; no model configuration was downloaded.
The prior missing-NumPy warning is resolved. NumPy/Torch interoperability,
in-memory safetensors round-trip and xxhash checks passed before GPU validation.
Torch 2.6.0+cu124 and Triton 3.2.0 were protected by pip constraints and remained
unchanged. FlashAttention was installed in ENV-006 and nano-vllm 0.2.0 was
installed in editable mode in ENV-007. torchvision and torchaudio remain absent.
MODEL-001 downloaded Qwen3-0.6B. SMOKE-001 attempt 3 completed one user
request after two preserved warmup failures.
Declared dependencies are torch>=2.4.0, triton>=3.0.0,
transformers>=4.51.0, flash-attn (required, unpinned), and xxhash (unpinned).
NumPy, tqdm, and safetensors are imported directly but not separately declared.

Ubuntu reports 24.04.5 LTS on WSL2 kernel 6.18.33.2-microsoft-standard-WSL2.
GPU query reports RTX 4050 Laptop GPU, 6141 MiB VRAM, driver 616.64.
nvidia-smi reports CUDA UMD Version 13.4; this does not establish a CUDA
Toolkit installation or a future PyTorch CUDA runtime version.
At ENV-001, pip3, nvcc, python3.11, and python3.10 were unavailable on PATH.
ENV-002 now provides pip inside .venv; other commands were not rechecked.
The repository does not specify a tested CUDA/build compatibility matrix.

## Current Validation

TELEMETRY-002:

- `.venv/bin/python -m unittest discover -s tests -v`: 27 CPU tests passed. The initial forced-preemption test used a one-prompt batch budget and incorrectly expected both requests already scheduled; its dedicated CPU scenario was corrected to a 512-token budget. The conservative GPU configuration was unchanged.
- `.venv/bin/python scripts/smoke_single_request.py --telemetry-output artifacts/telemetry/smoke-completed.jsonl`: exit 0, nonempty output and 10 output tokens. Original model/prompt/seed/options and previous failure records preserved.
- Example seconds relative to t0: admitted=0.000107763, first_scheduled=0.000123806, first_prefill_dispatch=0.000126505, first_token=1.420844472, finished=2.615674153. Ten token timestamps are nondecreasing; last token=2.615656154.
- No warnings/errors observed in the GPU run. Load/warmup=4.592236965 s and generation=2.616846184 s are smoke diagnostics, not benchmark data. Telemetry overhead was not quantified or compared to prior runs.
- Source diff reviewed: Scheduler.schedule/preempt and LLMEngine.generate/exit remain AST-identical to HEAD; BlockManager, Sequence, ModelRunner, kernels and sampling source are unchanged. Enabling/disabling telemetry gave equal queue/output/block-state histories in the CPU preemption scenario.
- `git diff --check` and `git status --short` checked. Dependency declarations, trace inputs and existing artifacts unchanged; no commit created.

Interface: after LLM initialization/warmup, call
`llm.enable_telemetry(t0_ns)` with the coordinator's perf_counter_ns origin.
For trace requests, use `llm.add_request(tokens, sampling, request_id=external_id)`;
legacy generate calls receive auto IDs `seq-<engine_seq_id>` when capture is enabled.
Retrieve detached records using `llm.get_telemetry(completed_only=True)` keyed
by request_id. Capture defaults to disabled. The smoke script adds only an
optional --telemetry-output flag; its default inference path remains intact.

The exported engine-telemetry-v1 record is an engine-only contribution, not a
complete request-telemetry-v1 experiment record. It contains no planned arrival,
release or inferred user-facing TTFT/E2E. Those remain outside the engine and
must be joined by a future coordinator using the same t0. Incomplete engine
records retain null future timestamps; failure/cancellation/timeout finalization
and full run metadata assembly are not implemented in this task. Hot paths use
clock reads, scalar assignments and in-memory token-list appends only; records
are retained in memory for the collector lifetime and copied on retrieval.


TELEMETRY-001: documentation/source-reference review, JSON example and formula
checks, git diff --check and git status --short completed. nano-vLLM source,
replay/generator scripts, dependency declarations and existing artifacts remain
unchanged. No runtime hooks, inference or benchmarks were run for this task.


REPLAY-001 validation:

- `.venv/bin/python -m unittest discover -s tests -v`: 19 CPU tests passed (9 trace and 10 replay tests).
- `.venv/bin/python scripts/replay_trace.py`: one CPU-only dry-run released all 12 requests; no repeated selection of a better timing result.
- Clock: `time.perf_counter_ns()`; each target is `t0 + arrival_s` converted to integer nanoseconds. Sleeps use only the remaining time to that fixed target and recheck the clock after waking.
- Mean absolute release error: 4.3290755 ms. Maximum absolute release error: 11.274627 ms.
- Timing artifact: `artifacts/replay/dev_replay_timing.jsonl`; records contain request ID, planned arrival_s, actual_release_s, signed release_error_ms and both input package hashes.
- `git diff --check` and `git status --short` passed/inspected; nano-vLLM source, dependency declarations, generator and input trace/metadata unchanged.

These errors measure CPU release timing on a non-real-time OS, not model
latency or performance. Release is sampled immediately before synchronous
callback dispatch; future engine admission, scheduling, first-token and
completion timestamps are distinct and are not measured. No TTFT definition
was changed. Callback exceptions abort without retry, so exactly-once dispatch
applies to successful complete runs. Late releases never shift future targets.
CLI output defaults to the existing artifact above and refuses overwrites;
use `--output <new-path>` for any later run. `replay_trace(path, callback)`
provides full package validation before replay; `replay_requests` is the
low-level timing primitive for already validated request records.


TRACE-002 commands (all CPU; no model backend or nano-vLLM import):

- `.venv/bin/python -m unittest discover -s tests -v`: 9 tests passed, including same-seed generation into two temporary files, byte/hash equality, and a changed-seed class-order difference.
- `.venv/bin/python scripts/make_trace.py --seed 42`: generated the default trace and separate metadata without overwriting existing artifacts.
- `.venv/bin/python scripts/make_trace.py --validate workloads/dev_trace.jsonl`: independent package validation passed, including exact re-tokenized lengths and local asset fingerprints.
- `git diff --check` and `git status --short`: checked; nano-vLLM source and dependency declarations unchanged.

Trace SHA256: `28f070031f63d3e0fc4d79accc25cd5df75c5b2e370e62e78da0c6822718d041`.
Metadata SHA256: `ff239cf2ef5fab30652fd385ebbd0b3f945e6e3a4ad05f5c8cd7943cc6917131`.
Prompt lengths in file order: 96, 96, 32, 192, 192, 96, 192, 32, 96, 32, 32, 192.
Planned arrivals: three requests each at 0, 0.25, 0.5 and 0.75 seconds.
All requests have max_new_tokens=16 and fit the 256-token development context.
Metadata includes model/tokenizer revisions and asset hashes, source/recipe
fingerprints, project commit/dirty provenance, RNG/library versions and sampling
settings. Auxiliary asset fingerprints were captured from the MODEL-001 local
snapshot; model.safetensors and tokenizer.json retain the previously verified
hashes. The generator verifies all recorded snapshot assets before tokenization.
Synthetic prompts use a shared template and a documented token-prefix selection
rule; shared prefixes are possible. These are development inputs, not a formal
workload or evidence of GPU concurrency/performance. Formal values remain unfrozen.


TRACE-001 documentation checks include JSON example parsing, offline pinned
tokenizer counts, specification consistency, git diff --check and git status
--short. nano-vLLM source remains unchanged; no inference or benchmark run.

ARCH-001 source references and lifecycle were checked against the local pinned
implementation. Documentation-only validation: git diff --check and git status
--short; nanovllm/ remains unchanged. No inference or benchmark run for ARCH-001.

Repository is currently based on the recorded upstream nano-vLLM commit.

ENV-001 command outputs and exit codes are recorded. Python version and path
were inspected; no dependency imports or GPU inference validation was performed.
Upstream source and dependency declarations remain unchanged.
ENV-002 activation, Python 3.12.3, Python/pip paths, environment isolation,
package inventory, and Git ignore checks passed.
ENV-004 pip check, version/path isolation checks, GPU detection and CUDA matrix
multiplication passed. Full package versions and memory statistics are recorded
in artifacts/environment/pytorch-gpu-info.txt. No inference was run.
ENV-005 ordinary-package imports and pip check passed. CUDA availability and
4x4 matrix multiplication were revalidated on the RTX 4050 with unchanged
Torch/Triton versions. flash_attn was absent at ENV-005. Evidence and the post-install
package inventory are in artifacts/environment/runtime-deps-info.txt.
ENV-006 confirmed flash_attn import, version 2.7.4.post1, torch 2.6.0+cu124,
Triton 3.2.0, CUDA runtime 12.4 and RTX 4050 availability. FP16 varlen causal
attention and one-token KV-cache decode passed against FP32 PyTorch SDPA
(atol=rtol=0.003); max absolute errors were 0.0005553 and 0.0005496.
pip check passed without warnings/errors. No Toolkit installation, nvcc
invocation, source build or model download was performed in ENV-006.
ENV-007 installed the local package with --editable . --no-deps
--no-build-isolation --no-index, using existing setuptools. Editable metadata
points to /home/luoyuxuan/projects/nano-vllm-scheduling-lab.
Imports from /tmp using isolated Python resolved 12 important nano-vLLM modules
to local source; public LLM and SamplingParams imports passed without engine
instantiation. pip check passed. Torch 2.6.0+cu124, Triton 3.2.0,
FlashAttention 2.7.4.post1 and Transformers 4.57.6 are unchanged, as are all
other pre-existing distributions. CUDA is available and RTX 4050 is detected.
Editable metadata resides in .venv; no egg-info directory was left in the
repository root. Source was not edited.

## Model Files

Repository: Qwen/Qwen3-0.6B.
Revision: c1899de289a04d12100db370d81485cdf75e47ca.
Local path: /home/luoyuxuan/projects/nano-vllm-scheduling-lab/models/Qwen3-0.6B.
Directory size at validation: 1519210302 bytes (1.414875 GiB), including
local download metadata; payload files total 1519209243 bytes.
Qwen3Config loaded locally: bfloat16, 28 layers, hidden size 1024.
Qwen2TokenizerFast loaded locally and round-tripped 'Hello, nano-vLLM!'.
Weight and tokenizer.json SHA256 values match the pinned Hub LFS metadata.
MODEL-001 inspected a safetensors header listing 311 tensors without loading
a model. SMOKE-001 subsequently loaded it on cuda:0 and generated a response
on attempt 3, after two failed warmup attempts.
Model directory is ignored by Git.

## Next Task

In a separately scoped task, execute the frozen manifest on the GPU exactly
as recorded. Preserve terminal failures and partial artifacts, resume only
pending entries, and do not change traces, run order, policy behavior or the
fixed aging rate after inspecting results. Aggregate only after the required
valid run set is available.

## SMOKE-001 Attempt

Configuration: local Qwen3-0.6B, enforce_eager=True, tensor_parallel_size=1,
max_model_len=256, max_num_batched_tokens=256, max_num_seqs=1,
gpu_memory_utilization=0.6. Sampling: temperature=0.6, max_tokens=32,
ignore_eos=False, seed=42; local chat template enable_thinking=False.
Prompt: 'Say hello in one short sentence.' (19 tokens after chat formatting).
Initial attempt: one process; zero user requests completed and no output tokens
were produced. Upstream warmup precedes generate and is not a user request.
Process wall time: 9.315443 seconds including failure, not generation latency.
Pre-load CUDA free/total memory: 5318377472 / 6438780928 bytes; peak memory
was not captured because initialization failed. The reported error was a
compiler failure, not an out-of-memory error. Full traceback is preserved.

### Continuation after user-installed C/C++ compiler

Same script (unchanged SHA256 recorded), model and configuration; one retry.
gcc and g++ 13.3.0 are available at /usr/bin. Initialization failed during
upstream warmup because Python.h was missing. No user request was submitted,
no output generated. Process wall time: 8.905485 seconds including failure.
Pre-load free/total CUDA bytes: 5318377472 / 6438780928; peak not captured.
NCCL cleanup warning followed constructor failure. Both complete error records
are preserved in artifacts/environment/smoke-single-request.txt.

### Successful continuation after user-installed Python development headers

Attempt 3 used the exact same script/model/configuration and completed one
request normally (process exit 0). Python.h and python3.12-config were verified;
python3.12-dev version is 3.12.3-1ubuntu0.17. No package changes by the agent.
Output: 'Hello! How can I assist you today?<|im_end|>'.
Prompt tokens: 19; output tokens: 10, including EOS token 151645.
Model device: cuda:0 on NVIDIA GeForce RTX 4050 Laptop GPU.
Load/warmup: 11.072971 s; generation: 7.158313 s; script through cleanup:
18.900762 s; whole process including Python imports/startup/exit: 25.007268 s.
Timings include first-run compilation effects and are not benchmark results.
PyTorch peak allocated/reserved bytes since upstream warmup's statistics reset:
2606195712 / 2678063104 (about 2.43 / 2.49 GiB). These are allocator statistics,
not total device/process residency. Post-generation free/total CUDA bytes:
2610954240 / 6438780928. No warnings/errors observed on this successful attempt.
The first two complete failure records are preserved verbatim in the log.

## Important Constraints

Do not install dependencies during the bootstrap verification task.

Do not modify nano-vLLM source code during bootstrap.

Do not change the upstream revision during the main experiment without
documenting the change.

Do not claim any scheduling performance improvement before formal experiments
have been completed.
