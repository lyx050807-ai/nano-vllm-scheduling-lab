# PROJECT_STATE.md

Last updated: 2026-09-20

## Current Phase

ENV-001 through ENV-007, MODEL-001, SMOKE-001, ARCH-001, TRACE-001/002 and
REPLAY-001 and TELEMETRY-001/002 complete; opt-in engine lifecycle telemetry
passed CPU tests and the conservative single-request GPU regression.

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

Initial single-request inference, architecture analysis, trace implementation
and CPU arrival replay are complete. Engine-side telemetry is instrumented and
validated on one GPU request; replay-to-engine integration, full experiment
record assembly and broader workload validation remain pending.
No formal performance experiment has run.
Evidence: artifacts/environment/smoke-single-request.txt.
Reusable entry point: scripts/smoke_single_request.py.

## Not Started

- full nano-vLLM integration validation
- replay-to-engine integration
- full experiment telemetry assembly (replay/engine join, failures and timeout finalization)
- scheduling policies
- scheduling-policy tests (trace, CPU replay and engine telemetry tests are implemented)
- formal workloads
- experiments
- analysis
- report

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

In a separately scoped task, connect validated arrival replay to engine
admission using a shared coordinator origin and external request IDs, then join
replay release/planned times with the engine telemetry fragments. Preserve the
release-based TTFT/E2E definitions and specify failure/timeout finalization.
Validate the baseline integration before adding any scheduling policy or formal
performance workload; keep the current dependency stack and trace unchanged.

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
