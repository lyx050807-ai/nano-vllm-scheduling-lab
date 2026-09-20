"""Generate and validate immutable formal-mixed-v1 trace packages on CPU.

Generate: .venv/bin/python scripts/make_formal_trace.py --seed 101
Validate: .venv/bin/python scripts/make_formal_trace.py --validate workloads/formal_trace_seed101.jsonl
"""
import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import platform
import random
import re
import subprocess

if __package__:
    from . import make_trace
else:
    import make_trace

ROOT = Path(__file__).resolve().parents[1]
PROFILE = "formal-mixed-v1"
SEEDS = (101, 202, 303)
CLASS_COUNTS = {name: 20 for name in make_trace.TARGETS}
RECIPE = {
    "request_count": 60, "class_counts": CLASS_COUNTS,
    "targets": make_trace.TARGETS, "class_intervals": make_trace.INTERVALS,
    "max_new_tokens": 16, "arrival_group_size": 3,
    "arrival_group_spacing_us": 250000,
    "initial_class_order": [name for name in make_trace.TARGETS for _ in range(20)],
    "randomization": "random.Random(seed).shuffle(initial_class_order) once",
    "tie_order": "JSONL line order",
    "request_ids": "formal-{seed}-{one_based_index:06d}",
}


def generate_records(tokenizer, seed):
    make_trace.require(type(seed) is int and seed in SEEDS, "unsupported formal seed")
    classes = list(RECIPE["initial_class_order"])
    random.Random(seed).shuffle(classes)
    records = []
    for index, label in enumerate(classes, 1):
        source = make_trace.TEMPLATE.format(number=index) + make_trace.DETAIL * 12
        ids = tokenizer.encode(source, add_special_tokens=False, truncation=False)
        target = make_trace.TARGETS[label]
        make_trace.require(len(ids) >= target, "synthetic source shorter than target")
        text = tokenizer.decode(ids[:target], skip_special_tokens=False,
                                clean_up_tokenization_spaces=False)
        actual = len(tokenizer.encode(text, add_special_tokens=False, truncation=False))
        make_trace.require(actual == target, f"tokenizer round trip failed at {index}")
        records.append({"schema_version": make_trace.SCHEMA,
                        "request_id": f"formal-{seed}-{index:06d}",
                        "arrival_s": Decimal((index - 1) // 3) / 4,
                        "prompt_text": text, "num_prompt_tokens": actual,
                        "prompt_class": label, "max_new_tokens": 16})
    make_trace.validate_records(records, tokenizer)
    return records


def make_metadata(data, records, seed, assets):
    digest = make_trace.sha256(data)
    return {"schema_version": make_trace.SCHEMA, "profile_id": PROFILE,
            "trace_id": f"{PROFILE}-seed{seed}-{digest}",
            "seed": seed, "request_count": len(records),
            "class_counts": dict(Counter(r["prompt_class"] for r in records)),
            "max_new_tokens": 16, "trace_sha256": digest, "context_limit": 256,
            "generation_recipe": RECIPE, "prompt_source": make_trace.PROMPT_SOURCE,
            "tokenization": make_trace.TOKENIZATION,
            "sampling": make_trace.SAMPLING,
            "generator": {"identity": "scripts/make_formal_trace.py", "version": "1",
                          "source_sha256": make_trace.file_hash(Path(__file__)),
                          "project_commit": make_trace.git_output("rev-parse", "HEAD").decode().strip(),
                          "dirty": bool(make_trace.git_output("status", "--porcelain")),
                          "tracked_diff_sha256": make_trace.sha256(
                              make_trace.git_output("diff", "--binary", "HEAD")),
                          "rng": "Python random.Random MT19937; shuffle",
                          "python_version": platform.python_version()},
            **make_trace.asset_metadata(assets)}


def validate_package(data, metadata_bytes, tokenizer, assets):
    records = make_trace.validate_trace_bytes(data, tokenizer)
    meta = make_trace.strict_json(metadata_bytes.decode("utf-8"))
    make_trace.require(type(meta) is dict, "metadata must be an object")
    make_trace.require(type(meta.get("seed")) is int and meta["seed"] in SEEDS,
                       "unsupported formal seed")
    expected_rows = generate_records(tokenizer, meta["seed"])
    make_trace.require(make_trace.encode_trace(expected_rows) == data,
                       "formal recipe/seed does not reproduce trace bytes")
    expected = make_metadata(data, expected_rows, meta["seed"], assets)
    generator = meta.get("generator")
    make_trace.require(type(generator) is dict and set(generator) == set(expected["generator"]),
                       "invalid generator provenance")
    # Provenance values describe generation time; validate their form rather
    # than replacing them with today's dirty tree/commit state.
    for name in ("source_sha256", "tracked_diff_sha256"):
        make_trace.require(type(generator[name]) is str and
                           re.fullmatch(r"[0-9a-f]{64}", generator[name]), f"invalid {name}")
    make_trace.require(type(generator["project_commit"]) is str and
                       re.fullmatch(r"[0-9a-f]{40}", generator["project_commit"]),
                       "invalid project commit")
    make_trace.require(type(generator["dirty"]) is bool and
                       type(generator["python_version"]) is str and
                       re.fullmatch(r"\d+\.\d+\.\d+", generator["python_version"]),
                       "invalid generator environment")
    for name in ("identity", "version", "rng"):
        make_trace.require(generator[name] == expected["generator"][name],
                           f"invalid generator {name}")
    expected["generator"] = generator
    make_trace.require(set(meta) == set(expected), "metadata fields mismatch")
    for name in expected:
        make_trace.require(make_trace.json_equal(meta[name], expected[name]),
                           f"metadata mismatch: {name}")
    return records, meta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate", type=Path)
    parser.add_argument("--model", type=Path, default=ROOT / "models/Qwen3-0.6B")
    args = parser.parse_args()
    try:
        make_trace.require((args.validate is None) != (args.seed is None),
                           "provide exactly one of --seed or --validate")
        output = args.validate or args.output or ROOT / f"workloads/formal_trace_seed{args.seed}.jsonl"
        if args.validate:
            make_trace.require(args.output is None, "--output cannot accompany --validate")
        else:
            make_trace.require(args.seed in SEEDS, "unsupported formal seed")
            make_trace.require(not output.exists() and not output.with_suffix(".meta.json").exists(),
                               "refusing to overwrite formal package")
        tokenizer, assets = make_trace.load_local_tokenizer(args.model)
        if args.validate:
            data = output.read_bytes()
            metadata_bytes = output.with_suffix(".meta.json").read_bytes()
            records, meta = validate_package(data, metadata_bytes, tokenizer, assets)
        else:
            records = generate_records(tokenizer, args.seed)
            data = make_trace.encode_trace(records)
            meta = make_metadata(data, records, args.seed, assets)
            metadata_bytes = (json.dumps(meta, sort_keys=True, indent=2,
                                         ensure_ascii=False, allow_nan=False) + "\n").encode()
            validate_package(data, metadata_bytes, tokenizer, assets)
            make_trace.write_package(output, data, metadata_bytes)
        print(json.dumps({"status": "valid", "trace": str(output),
                          "seed": meta["seed"], "request_count": len(records),
                          "class_counts": meta["class_counts"],
                          "trace_sha256": make_trace.sha256(data),
                          "metadata_sha256": make_trace.sha256(metadata_bytes)}, sort_keys=True))
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()
