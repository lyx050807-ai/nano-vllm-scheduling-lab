# Reproducible request-trace specification

TRACE-001, 2026-09-19. Schema: `request-trace-v1`.
This document specifies a future trace artifact; it does not implement a
generator, replay driver, telemetry collector or scheduling policy.

## 1. Purpose

A trace fixes request identity, prompt contents, tokenizer-derived prompt
lengths, planned arrival times and generation limits before policy comparison.
`baseline`, `short_prompt` and `aged_short_prompt` must consume the same trace
bytes and compatible metadata. Policy results must never be used to revise
that trace in place. Development workload values below are candidates for
functional validation, not a frozen formal benchmark.

Source grounding: `docs/architecture.md` describes the pinned implementation.
`LLMEngine.add_request` accepts text or token IDs
(`nanovllm/engine/llm_engine.py:43-47`); `Sequence` fixes the original prompt
count at construction (`nanovllm/engine/sequence.py:18-31`). The trace records
that original count, not generated-history length or uncached prefill work.
Model identity and local validation evidence are in
`artifacts/environment/model-info.txt`.

## 2. JSONL schema

A trace package consists of `<name>.jsonl` (requests only) and
`<name>.meta.json` (one trace-level metadata object). These are future output
artifacts; TRACE-001 creates only this specification and the project-state
update. Do not put a metadata header among request lines.

Each nonempty line is one JSON object with exactly these seven required keys;
no null values, duplicate keys, unknown keys or implicit defaults are allowed.
JSON integers exclude booleans. Unknown schema versions must be rejected.

| Field | JSON type | Contract |
| --- | --- | --- |
| `schema_version` | string | Exactly `request-trace-v1`, identical on every line and in the metadata. |
| `request_id` | string | Unique in the trace; 1-128 ASCII letters, digits, underscores or hyphens. Stable external identity, independent of engine IDs and policy. |
| `arrival_s` | number | Finite, nonnegative planned seconds from replay origin; microsecond resolution, at most six fractional decimal digits. |
| `prompt_text` | string | Nonempty final text to tokenize exactly as stored, with no further formatting or normalization. |
| `num_prompt_tokens` | integer | Positive exact length of the pinned tokenizer's encoded input. |
| `prompt_class` | string | One of `short`, `medium`, `long`; validated against metadata's explicit, disjoint inclusive token intervals. Analysis label only. |
| `max_new_tokens` | integer | Positive output-token cap, mapped to `SamplingParams.max_tokens`. Not a predicted or guaranteed realized output length. |

A trace contains at least one request. Its line order is the stable admission
order for equal arrival times; a request ID's lexical order has no ordering
meaning. Class intervals and profile identity are mandatory metadata, so a
label cannot stand in for an unverified token count.

## 3. Example records

These two independent requests illustrate valid short-class records under the
development token interval below. They are an excerpt, not the complete
12-request development profile. Counts were checked offline with the local
pinned Qwen tokenizer using `add_special_tokens=False, truncation=False`.

```jsonl
{"arrival_s":0.000000,"max_new_tokens":16,"num_prompt_tokens":30,"prompt_class":"short","prompt_text":"Explain how a waiting queue helps a language model server organize incoming requests. Keep the answer brief and focus on the order in which requests are served.","request_id":"dev-000001","schema_version":"request-trace-v1"}
{"arrival_s":0.250000,"max_new_tokens":16,"num_prompt_tokens":27,"prompt_class":"short","prompt_text":"Describe why a server should measure the time between receiving a request and returning its first generated token. Give a brief explanation using plain language.","request_id":"dev-000002","schema_version":"request-trace-v1"}
```

No response text, observed output count, latency or policy label belongs in a
request record. Escaped newlines inside `prompt_text` are allowed; literal
line breaks separating parts of one object are not.

## 4. Field semantics

**Arrival clock.** `arrival_s = 0` means eligible at a common monotonic replay
origin established after engine initialization/warmup and trace validation.
It is neither a wall-clock timestamp nor time since the previous request.
Records must be nondecreasing in `arrival_s`; equality is valid. The first
arrival may be positive and then denotes an initial idle interval. Treat the
stored decimal as an exact integer number of microseconds for comparisons;
do not accumulate floating-point interarrival deltas. Negative zero is not
allowed in canonical serialization.

A future replay admits a request no earlier than its planned arrival. If a
GPU step delays admission, retain the original `arrival_s` and record the
actual admission time separately. Do not shift subsequent planned arrivals,
submit the whole trace at time zero, or speed up arrivals for a faster policy.

**Prompt and tokenization.** In v1, `prompt_text` is the final model input
text. Encode it with the pinned fast tokenizer, `add_special_tokens=False`
and `truncation=False`, without padding, trimming or Unicode normalization.
If a future workload uses a chat template, apply that template once during
trace construction, store the resulting full text, and record the template
hash/options in metadata. Do not apply it again during replay. The development
profile uses plain text without a chat template; it is distinct from SMOKE-001's
chat-formatted request. Token counts include all tokens in the final text.

Future replay should encode/validate before starting its clock and pass those
token IDs to `add_request`. This avoids relying on the string API's default
special-token settings (`llm_engine.py:43-47`). v1 does not store token IDs in
request rows; the pinned tokenizer and exact text define them.

**Generation cap.** `max_new_tokens` counts appended completion tokens,
including an EOS token if emitted. With `ignore_eos=False`, actual completion
can be shorter; the cap is not a target output length. EOS/cap stopping is in
`nanovllm/engine/scheduler.py:88-92`. Other sampling settings belong in shared
metadata, not policy-specific trace mutations.

## 5. Scheduler-visible vs forbidden information

The future priority interface must expose a restricted view, not the entire
JSON object or trace manifest.

| Information | Permitted use |
| --- | --- |
| Validated `num_prompt_tokens` | Allowed length-based scheduling input after admission. Use original prompt length even after preemption. |
| `request_id` and trace ordinal | Identity and stable tie resolution only; never parse embedded class/seed information to choose priority. |
| `arrival_s` | Known planned arrival for an already admitted request; permitted arrival information. |
| Actual admission time, current monotonic time, elapsed waiting | Causal runtime information; allowed for a later explicitly defined aging policy. These are telemetry/runtime state, not future values stored in the trace. |
| `prompt_text` | Execution input; not a priority feature for this project's three policies. |
| `prompt_class` | Experiment grouping/analysis only; no class-based priority shortcut. |
| `max_new_tokens`, sampling settings | Execution/stopping and context validation only; excluded from priority decisions even though known in advance. |
| Schema/profile/model IDs, seeds, hashes, full trace | Validation/reproducibility metadata; not priority features. Unarrived requests must not be exposed to the scheduler. |

Forbidden future information includes actual final output length, generated
responses from prior runs, future token IDs, future arrival contents, measured
or oracle service/completion times, future latency, and other policies' outcomes.
Do not attach such information to request rows or feed result telemetry back
into priority calculation. This includes using known future arrivals from an
offline trace to anticipate load. The replay reader can hold the full trace,
but must admit only due requests and expose only causal scheduler inputs.

Waiting eligibility for partial-prefill and preempted requests remains a
separate policy contract (see `docs/architecture.md`, sections 4 and 7).
TRACE-001 does not choose a priority formula or change baseline queue behavior.

## 6. Reproducibility rules

The sidecar metadata must contain the following fields, with no missing
provenance substituted by a mutable branch name or an absolute local path.

| Metadata field | Required content |
| --- | --- |
| `schema_version`, `trace_id`, `profile_id` | Schema literal, stable trace identifier and versioned workload profile identifier. |
| `request_count`, `trace_sha256` | Positive line count and lowercase 64-hex SHA256 of the exact JSONL bytes. |
| `generator` | Generator identity/version, full project commit, dirty status and any required patch hash, plus RNG algorithm/library/version. TRACE-001 does not provide a generator. |
| `seed` | Nonnegative integer for construction randomness, explicitly supplied; no hidden wall-clock seeds. |
| `generation_recipe` | Counts/class proportions, target lengths/tolerances, class intervals, arrival rule/parameters, ordering and tie rules, and all randomization inputs. |
| `prompt_source` | Immutable source/template identity and SHA256s of inputs; final transformation rules, including padding/trimming if any. Always re-encode the final stored text. |
| `model` | Repository ID and full immutable revision; config and weight-file SHA256 inventory. |
| `tokenizer` | Repository ID and full immutable revision, tokenizer class, Transformers/tokenizers versions, and SHA256s of tokenizer assets used. |
| `tokenization` | `use_fast=true`, `add_special_tokens=false`, `truncation=false`, padding/normalization disabled; template mode and template hash/options if applicable. |
| `sampling` | Shared `temperature`, `ignore_eos` and a separate inference seed; per-request caps remain in JSONL. |
| `context_limit` | Positive intended engine context bound used to validate every request. |

Pin model and tokenizer separately even when they come from the same snapshot.
For the current development profile both are `Qwen/Qwen3-0.6B` at revision
`c1899de289a04d12100db370d81485cdf75e47ca`, locally in `models/Qwen3-0.6B`.
MODEL-001 recorded `Qwen2TokenizerFast`, model context capacity 40960, and:

- `tokenizer.json` SHA256:
  `aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4`.
- `model.safetensors` SHA256:
  `f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b`.

A future manifest must inventory other used tokenizer assets too, including
`tokenizer_config.json`, `vocab.json` and `merges.txt`. Record actual library
versions; a seed alone is not enough to reproduce random generation across
algorithms or versions. The same inputs, recipe, seed and pinned generator
must yield identical JSONL bytes. If construction cannot meet its token-length
requirements, fail rather than silently relaxing them.

Keep inference seed distinct from trace-construction seed. Equal inference
seeds do not guarantee equal sampled outputs across different batch/scheduling
orders. The invariant is equal inputs, limits and sampling configuration, not
identical realized output length. Each run additionally records project and
upstream commits, environment, engine configuration, policy/configuration,
trace and metadata hashes, inference seed and warmup/cache setup. Hold these
constant across comparisons except for the declared policy and its parameters.

## 7. Validation rules

Future validation must reject invalid input before engine admission:

1. Validate UTF-8 JSONL syntax, canonical encoding rules below, schema version,
   exact keys/types and no duplicate keys, nulls, booleans in numeric fields,
   NaN or infinity. Reject an empty trace and blank lines.
2. Require unique nonempty IDs matching `[A-Za-z0-9_-]{1,128}`; preserve input
   line order and reject decreasing arrival times rather than sorting them.
   Validate exact nonnegative microsecond-representable arrivals.
3. Check metadata identity, profile rules, request count, trace SHA256, model
   and tokenizer revisions/assets, and effective tokenization settings.
4. Re-encode every final `prompt_text` with the pinned tokenizer. Require a
   nonempty token list and `len(token_ids) == num_prompt_tokens` exactly.
   Never estimate using word count, character count or the class target.
5. Require a positive integer `max_new_tokens`; verify `prompt_class` against
   the manifest's disjoint inclusive length intervals and declared class mix.
6. Require `num_prompt_tokens + max_new_tokens <= context_limit` for every
   request. At replay also require the sum not exceed the effective engine
   bound, `min(configured max_model_len, model max_position_embeddings)`.
   The manifest's context bound must not exceed that effective bound. Never
   repair an overflow by silent truncation or lowering the output cap.
7. Validate shared sampling settings against the pinned API: finite
   `temperature > 1e-10`, Boolean `ignore_eos`, explicit inference seed
   (`nanovllm/sampling_params.py:4-12`). Reject forbidden result fields or a
   changed trace/hash. Profile changes require a new identified artifact.

Context-length safety is not proof of GPU-memory feasibility under concurrency.
The allocator reserves logical blocks for the current history, and resident
requests can exceed a selected batch's sequence limit. Future integration
validation must establish memory/progress safety separately; this task runs
no inference or performance experiment.

## 8. Development workload profile

Candidate profile ID: `dev-mixed-v1`. It is for small functional checks on the
6 GB RTX 4050, not a formal benchmark or a validated concurrency guarantee.

| Parameter | Development choice |
| --- | --- |
| Requests | 12 total: four short, four medium, four long. |
| Prompt sizes | Targets approximately 32 / 96 / 192 tokens. |
| Inclusive class intervals | Short 24-40, medium 88-104, long 184-200 tokens (target +/- 8). Counts must still be exact for each record. |
| Prompt content | Plain-text synthetic instructions; store all final text. No chat template. Deterministically shuffle the class assignment; preserve the resulting file across policies. |
| Arrival pattern | Four groups of three at 0.000000, 0.250000, 0.500000 and 0.750000 seconds. File order breaks ties. This exercises simultaneous and delayed eligibility. |
| Construction seed | 42, with the exact future generator/RNG version recorded. |
| Generation | `max_new_tokens=16` for all requests; shared temperature 0.6, `ignore_eos=false`, inference seed 42. |
| Context bound | 256 tokens. Largest allowed prompt plus output cap is 200 + 16 = 216. |
| Model/tokenizer | Pinned Qwen3-0.6B snapshot specified above. |

Distinct prompt texts are preferred; repeated templates/shared prefixes can
alter prefix-cache reuse and must be documented rather than assumed absent.
This profile has no expected completion times, throughput or guaranteed
starvation stress. Its arrival spacing may create a backlog during early slow
steps. No engine batch-size, concurrency or memory-utilization change is
prescribed here. A later GPU task must choose and validate those settings.
Formal class ratios, counts, arrival distributions/rates, prompt corpus,
length ranges, output limits, repetitions and load levels remain unfrozen;
freeze them in a separately versioned experiment definition before measuring
policy results. Do not promote this development profile implicitly.

## 9. Trace hashing/versioning

Canonical JSONL uses UTF-8 without BOM, LF line endings and exactly one final
LF. Every line is a compact JSON object with lexicographically sorted keys,
no spaces outside strings, no escaped slash and literal non-ASCII Unicode.
Use standard JSON escaping for quotes, backslashes and control characters;
other Unicode characters are not escaped. Reject invalid Unicode surrogates.
Integer fields use base-10 integers without leading zeros. Serialize
`arrival_s` in fixed-point seconds with exactly six fractional digits, no
exponent and no negative zero. This avoids ambiguity from floating-point
formatting and makes whitespace/content changes detectable.

Compute SHA256 over the complete final JSONL byte sequence, including line
endings; do not hash parsed objects or silently normalize an existing file.
Store the lowercase digest in `trace_sha256` in the sidecar. The sidecar is
outside that digest to avoid self-reference. Each run must also record the
SHA256 of the exact sidecar bytes, so changed tokenizer, sampling or profile
metadata cannot reuse a comparison identity unnoticed. Comparison identity
is the pair `(trace_sha256, metadata_sha256)`; a human-readable trace ID alone
is insufficient. No fabricated trace digest is supplied by this specification.

Change schema version for incompatible field, unit, encoding or meaning
changes. Change profile version for workload-definition changes. A different
seed, prompt, arrival, limit or ordering yields a new trace artifact/hash;
metadata-only changes yield a new package identity. Keep old artifacts and
formal results; never overwrite them after inspecting results. Future writers
should refuse existing output paths unless operating on an explicitly separate
new artifact. Consumers reject unsupported versions rather than guessing.

## 10. Relationship to future replay and telemetry

For each policy, a future replay loads and validates the same trace package,
pretokenizes once, initializes the same model/engine settings, and establishes
its own monotonic zero after the same warmup/cache procedure. At each admission
opportunity, submit all due unadmitted requests in trace order, then allow
scheduling. If the engine is idle before the next arrival, wait for that due
time. Record admission delays caused by an in-flight step; do not compensate
by changing the trace. This preserves the offered workload across policies,
although actual admission times can differ at step boundaries.

Do not call existing `generate` on the full trace as a timed replay: it adds
all prompts before its loop (`nanovllm/engine/llm_engine.py:60-75`). The future
adapter must retain a mapping from external `request_id` to engine `seq_id`;
engine IDs include warmup sequences and are not stable trace identities.
Preemption/resumption is not a new trace arrival.

Keep result telemetry in separate run artifacts keyed by request ID and the
trace/metadata hashes. Record at least planned arrival, actual admission,
first scheduling, first output token, subsequent token times, completion,
actual output count and failure/cancellation status, with timestamps relative
to the same run origin. Distinguish arrival-to-first-token latency from
admission-to-first-token latency; report admission delay separately. The exact
telemetry hooks, repeated-wait accounting and aging origin need a later task.
Do not infer first-token time from the final result: current `step` returns
only completed sequences (`llm_engine.py:49-55`). Never mutate input records to
append telemetry or leak another run's outcomes into scheduling.

Recommended next task: implement a CPU-only trace generator and validator
against this specification, with determinism, schema, exact-token-count,
ordering, context-limit and hashing tests. Replay, telemetry integration and
policy implementation should remain separate scoped tasks.
