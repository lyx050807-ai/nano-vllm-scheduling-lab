# CURRENT_TASK.md

## Task ID

TRACE-002

## Title

Implement the deterministic request-trace generator and validator.

## Goal

Implement a CPU-only trace generator that follows docs/trace-spec.md and
produces reproducible JSONL workloads for later scheduler experiments.

Do not modify nano-vLLM source code.

## Required Work

1. Read:
   - AGENTS.md
   - PROJECT_STATE.md
   - docs/trace-spec.md
   - artifacts/environment/model-info.txt

2. Implement:

   scripts/make_trace.py

3. The generator must use the local Qwen3-0.6B tokenizer and follow the
   versioned schema in docs/trace-spec.md.

4. Implement the development workload defined by TRACE-001:

   - 12 total requests
   - 4 short
   - 4 medium
   - 4 long
   - target prompt lengths defined in the trace specification
   - max_new_tokens = 16

5. Use an explicit random seed.

6. For every generated request, verify the actual tokenizer-derived prompt
   length rather than assuming word count equals token count.

7. Produce nondecreasing arrival_s values according to the trace specification.

8. Implement trace validation covering at least:

   - schema version
   - unique request IDs
   - nonnegative/nondecreasing arrivals
   - valid prompt classes
   - exact tokenizer-derived prompt lengths
   - positive max_new_tokens
   - context-length safety

9. Compute and report the SHA256 hash of the final JSONL file.

10. Default development output:

    workloads/dev_trace.jsonl

11. Save generation metadata separately under:

    workloads/dev_trace.meta.json

The metadata should include at least:

- trace version
- seed
- model/tokenizer identity
- tokenizer revision
- request count
- class counts
- max_new_tokens
- trace SHA256

## Reproducibility Tests

Generate the trace twice with the same seed into two temporary files.

Confirm:

- byte-for-byte file equality
- identical SHA256 hashes

Then generate with a different seed and confirm the resulting trace changes
in at least one intended stochastic field.

## Restrictions

Do not:

- modify nanovllm/
- run GPU inference
- implement replay
- implement telemetry
- implement scheduling policies
- change dependencies

This task should run on CPU.

## Validation

Run the generator and validator.

Run:

git diff --check
git status --short

Confirm nanovllm/ is unchanged.

## PROJECT_STATE

Update PROJECT_STATE.md with TRACE-002 completion and next recommended task.

## Acceptance Criteria

- generator works
- generated trace validates
- prompt lengths are tokenizer-verified
- same seed produces byte-identical trace
- same seed produces identical SHA256
- different seed changes intended stochastic content
- metadata records reproducibility information
- no nano-vLLM source is modified
- git diff --check passes

Do not create a Git commit.

## Completion Report

Report:

- generator interface
- seed used
- request/class counts
- prompt token counts
- arrival behavior
- trace SHA256
- reproducibility-test results
- files created/modified
- recommended next step
