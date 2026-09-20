"""One local Qwen3 request; no benchmark or dependency changes."""
import argparse
import atexit
import json
import os
from pathlib import Path
from time import perf_counter, perf_counter_ns

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import torch
from transformers import AutoTokenizer
from nanovllm import LLM, SamplingParams


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--telemetry-output", type=Path,
                        help="enable engine telemetry and save one completed JSONL record")
    args = parser.parse_args()
    if args.telemetry_output and (args.telemetry_output.exists() or args.telemetry_output.is_symlink()):
        parser.error("telemetry output already exists; choose a new path")
    started = perf_counter()
    model = Path(__file__).resolve().parents[1] / "models/Qwen3-0.6B"
    options = dict(enforce_eager=True, tensor_parallel_size=1,
                   max_model_len=256, max_num_batched_tokens=256,
                   max_num_seqs=1, gpu_memory_utilization=0.6)
    prompt = "Say hello in one short sentence."
    tokenizer = AutoTokenizer.from_pretrained(str(model), local_files_only=True)
    rendered = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}], tokenize=False,
        add_generation_prompt=True, enable_thinking=False)
    token_ids = tokenizer.encode(rendered)
    sampling = SamplingParams(temperature=0.6, max_tokens=32, ignore_eos=False)
    assert len(token_ids) + sampling.max_tokens <= options["max_model_len"]
    torch.manual_seed(42)
    print("Model:", model, flush=True)
    print("Config:", json.dumps(options), flush=True)
    print("Sampling: temperature=0.6 max_tokens=32 ignore_eos=False seed=42", flush=True)
    print("Prompt:", repr(prompt), flush=True)
    print("Rendered prompt:", repr(rendered), flush=True)
    print("Prompt token count:", len(token_ids), flush=True)
    print("GPU:", torch.cuda.get_device_name(0), flush=True)
    print("Pre-load free/total bytes:", torch.cuda.mem_get_info(), flush=True)
    load_started = perf_counter()
    llm = LLM(str(model), **options)
    try:
        torch.cuda.synchronize()
        print("Load/warmup seconds:", perf_counter() - load_started, flush=True)
        print("Model device:", next(llm.model_runner.model.parameters()).device, flush=True)
        assert next(llm.model_runner.model.parameters()).is_cuda
        if args.telemetry_output:
            llm.enable_telemetry(perf_counter_ns())
        generated_started = perf_counter()
        outputs = llm.generate([token_ids], sampling, use_tqdm=False)
        torch.cuda.synchronize()
        print("Generate seconds:", perf_counter() - generated_started, flush=True)
        assert len(outputs) == 1 and llm.is_finished()
        result = outputs[0]
        assert result["text"].strip() and 0 < len(result["token_ids"]) <= 32
        print("Output text:", repr(result["text"]), flush=True)
        print("Output token count:", len(result["token_ids"]), flush=True)
        print("Output token IDs:", result["token_ids"], flush=True)
        print("Peak allocated bytes (since upstream warmup reset):", torch.cuda.max_memory_allocated(), flush=True)
        print("Peak reserved bytes (since upstream warmup reset):", torch.cuda.max_memory_reserved(), flush=True)
        print("Post-generation free/total bytes:", torch.cuda.mem_get_info(), flush=True)
        if args.telemetry_output:
            records = llm.get_telemetry(completed_only=True)
            assert len(records) == 1
            record = next(iter(records.values()))
            order = [record[key] for key in ("admitted_s", "first_scheduled_s",
                     "first_prefill_dispatch_s", "first_token_s", "finished_s")]
            assert all(value is not None for value in order) and order == sorted(order)
            times = record["token_times_s"]
            assert len(times) == len(result["token_ids"]) and times == sorted(times)
            assert record["first_token_s"] == times[0] and times[-1] <= record["finished_s"]
            args.telemetry_output.parent.mkdir(parents=True, exist_ok=True)
            with args.telemetry_output.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
            print("Telemetry ordering/token count: PASS", flush=True)
            print("Telemetry record:", args.telemetry_output, flush=True)
        print("Single request: PASS", flush=True)
    finally:
        atexit.unregister(llm.exit)
        llm.exit()
    print("Total script seconds including load/warmup and cleanup:", perf_counter() - started, flush=True)


if __name__ == "__main__":
    main()
