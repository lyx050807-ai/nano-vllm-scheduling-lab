# CURRENT_TASK.md

## Task ID

TRACE-001

## Title

Define the reproducible request-trace specification.

## Goal

Define the request trace format that will later be shared by baseline,
short_prompt, and aged_short_prompt experiments.

This is a design/documentation task only.

Do not implement the generator or replay driver yet.

## Context

The trace must allow different scheduling policies to receive exactly the same:

- requests
- prompt contents
- prompt lengths
- arrival times
- generation limits

The scheduler must not use future information such as actual output length.

## Required Work

1. Read:
   - AGENTS.md
   - PROJECT_STATE.md
   - docs/architecture.md
   - artifacts/environment/model-info.txt

2. Design a versioned JSONL request schema.

3. Define each request field, including at least:

   - request_id
   - arrival_s
   - prompt_text
   - num_prompt_tokens
   - prompt_class
   - max_new_tokens

4. Define the meaning and units of arrival_s.

5. Define which fields are:
   - allowed scheduling information
   - experiment-only metadata
   - forbidden future information

6. Define reproducibility requirements:
   - random seed
   - model/tokenizer identity
   - model/tokenizer revision
   - trace version
   - SHA256 trace hash

7. Define validation invariants, including:
   - unique request IDs
   - nondecreasing arrival times
   - exact tokenizer-derived prompt lengths
   - positive generation limits
   - context-length safety

8. Define a small development-only workload profile.

Use conservative candidate prompt sizes such as approximately:

- short: 32 tokens
- medium: 96 tokens
- long: 192 tokens

with a small generation limit such as 16 tokens.

Clearly state that these are development values, not the frozen formal
benchmark configuration.

9. Explain how the same trace will later be replayed under all scheduling
policies.

## Output

Create:

docs/trace-spec.md

Include:

1. Purpose
2. JSONL schema
3. Example records
4. Field semantics
5. Scheduler-visible vs forbidden information
6. Reproducibility rules
7. Validation rules
8. Development workload profile
9. Trace hashing/versioning
10. Relationship to future replay and telemetry

## Restrictions

Do not:

- modify nanovllm/
- implement make_trace.py
- implement replay
- implement scheduler policies
- run performance experiments
- change dependencies

## Validation

Run:

git diff --check
git status --short

Confirm nanovllm/ is unchanged.

## PROJECT_STATE

Update PROJECT_STATE.md with TRACE-001 completion and next recommended task.

## Acceptance Criteria

- trace schema is explicitly defined
- arrival semantics are defined
- reproducibility rules are defined
- future-information leakage is prohibited
- development workload profile is documented
- formal benchmark parameters remain unfrozen
- no nano-vLLM source was modified
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- schema fields
- arrival-time semantics
- scheduler-visible fields
- forbidden future information
- development workload profile
- reproducibility mechanism
- validation rules
- files modified
- recommended next step
