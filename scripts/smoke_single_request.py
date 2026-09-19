"""One local Qwen3 request; no benchmark or dependency changes."""
import atexit
import json
import os
from pathlib import Path
from time import perf_counter

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import torch
from transformers import AutoTokenizer
from nanovllm import LLM, SamplingParams


def main():
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
        print("Single request: PASS", flush=True)
    finally:
        atexit.unregister(llm.exit)
        llm.exit()
    print("Total script seconds including load/warmup and cleanup:", perf_counter() - started, flush=True)


if __name__ == "__main__":
    main()
