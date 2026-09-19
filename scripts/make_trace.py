"""Generate/validate dev-mixed-v1 traces using the local tokenizer on CPU.

Generate: .venv/bin/python scripts/make_trace.py --seed 42
Validate: .venv/bin/python scripts/make_trace.py --validate workloads/dev_trace.jsonl
Existing outputs are never overwritten. See docs/trace-spec.md.
"""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import random
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "request-trace-v1"
PROFILE = "dev-mixed-v1"
MODEL_ID = "Qwen/Qwen3-0.6B"
REVISION = "c1899de289a04d12100db370d81485cdf75e47ca"
TARGETS = {"short": 32, "medium": 96, "long": 192}
INTERVALS = {name: [target-8, target+8] for name, target in TARGETS.items()}
CLASS_COUNTS = {name: 4 for name in TARGETS}
KEYS = {"schema_version", "request_id", "arrival_s", "prompt_text",
        "num_prompt_tokens", "prompt_class", "max_new_tokens"}
TOKENIZATION = {"use_fast": True, "add_special_tokens": False, "truncation": False,
                "padding": False, "normalization": False, "template_mode": "plain_text"}
SAMPLING = {"temperature": 0.6, "ignore_eos": False, "inference_seed": 42}
TEMPLATE = (
    "Request {number:06d}: Explain how a language model server handles waiting requests. "
    "Discuss arrival order, prompt length, and the time before the first response. "
)
DETAIL = (
    "Consider a small server with limited memory. Some requests contain short questions "
    "and others contain longer descriptions. Explain the tradeoffs in plain language "
    "and keep the final answer brief. "
)
RECIPE = {
    "request_count": 12, "class_counts": CLASS_COUNTS, "targets": TARGETS,
    "class_intervals": INTERVALS, "max_new_tokens": 16,
    "arrival_group_size": 3, "arrival_group_spacing_us": 250000,
    "initial_class_order": [name for name in TARGETS for _ in range(4)],
    "randomization": "random.Random(seed).shuffle(initial_class_order) once",
    "tie_order": "JSONL line order", "request_ids": "dev-{one_based_index:06d}",
}
PROMPT_SOURCE = {
    "identity": "synthetic-server-instructions-v1", "template": TEMPLATE,
    "detail": DETAIL, "detail_repetitions": 12,
    "sha256": hashlib.sha256((TEMPLATE + DETAIL).encode()).hexdigest(),
    "transformation": "Encode template plus 12 details; decode first target tokens; "
                      "re-encode final text and require exact target count. No padding.",
    "prefix_reuse": "Shared template/detail text may produce shared KV prefixes; not controlled away.",
}
# Snapshot fingerprints: MODEL-001 validated primary files; auxiliary files
# fingerprinted from that same local snapshot during TRACE-002.
PINNED_HASHES = {
    "config.json": "660db3b73d788119c04535e48cf9be5f55bc3100841a718637ae695b442f27dd",
    "tokenizer_config.json": "d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101",
    "vocab.json": "ca10d7e9fb3ed18575dd1e277a2579c16d108e32f27439684afa0e10b1440910",
    "merges.txt": "8831e4f1a044471340f7c0a83d7bd71306a5b867e95fd870f74d0c5308a904d5",
    "tokenizer.json": "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4",
    "model.safetensors": "f47f71177f32bcd101b7573ec9171e6a57f4f4d31148d38e382306f42996874b",
}
TOKENIZER_FILES = ("tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def positive_int(value):
    return type(value) is int and value > 0


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def compact(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                      allow_nan=False)


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError(f"nonfinite JSON number: {value}")

    return json.loads(text, object_pairs_hook=pairs, parse_float=Decimal,
                      parse_constant=invalid_constant)


def load_local_tokenizer(model_dir):
    """Hash local assets and load only tokenizer data, never model tensors."""
    model_dir = Path(model_dir)
    require(model_dir.is_dir(), f"local model directory missing: {model_dir}")
    assets = {name: file_hash(model_dir / name)
              for name in (*TOKENIZER_FILES, "config.json", "model.safetensors")}
    for name, expected in PINNED_HASHES.items():
        require(assets[name] == expected, f"pinned asset hash mismatch: {name}")
    config = strict_json((model_dir / "config.json").read_text(encoding="utf-8"))
    require(config.get("model_type") == "qwen3", "expected Qwen3 model config")
    require(positive_int(config.get("max_position_embeddings")) and
            config["max_position_embeddings"] >= 256, "model context is below 256")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["USE_TORCH"] = "0"
    os.environ["USE_TF"] = "0"
    os.environ["USE_FLAX"] = "0"
    # Tokenizer-only mode intentionally disables model backends; keep CLI stderr
    # for errors instead of the expected "no model backend" advisory.
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        str(model_dir.resolve()), local_files_only=True, trust_remote_code=False, use_fast=True)
    require(type(tokenizer).__name__ == "Qwen2TokenizerFast" and tokenizer.is_fast,
            "expected Qwen2TokenizerFast")
    return tokenizer, assets


def generate_records(tokenizer, seed):
    require(type(seed) is int and seed >= 0, "seed must be a nonnegative integer")
    classes = list(RECIPE["initial_class_order"])
    random.Random(seed).shuffle(classes)
    records = []
    for i, label in enumerate(classes):
        source = TEMPLATE.format(number=i+1) + DETAIL * 12
        ids = tokenizer.encode(source, add_special_tokens=False, truncation=False)
        target = TARGETS[label]
        require(len(ids) >= target, "synthetic source shorter than target")
        text = tokenizer.decode(ids[:target], skip_special_tokens=False,
                                clean_up_tokenization_spaces=False)
        actual = len(tokenizer.encode(text, add_special_tokens=False, truncation=False))
        require(actual == target, f"tokenizer round trip failed for request {i+1}")
        records.append({"schema_version": SCHEMA, "request_id": f"dev-{i+1:06d}",
                        "arrival_s": Decimal(i // 3) / 4, "prompt_text": text,
                        "num_prompt_tokens": actual, "prompt_class": label,
                        "max_new_tokens": 16})
    validate_records(records, tokenizer)
    return records


def validate_records(records, tokenizer, context_limit=256):
    """Validate request semantics; full development-profile checks are separate."""
    require(positive_int(context_limit), "context limit must be a positive integer")
    require(isinstance(records, list) and records, "trace must contain requests")
    seen = set()
    previous = Decimal(-1)
    for index, row in enumerate(records, 1):
        prefix = f"request {index}: "
        require(type(row) is dict and set(row) == KEYS, prefix + "unexpected/missing fields")
        require(row["schema_version"] == SCHEMA, prefix + "unsupported schema")
        request_id = row["request_id"]
        require(isinstance(request_id, str) and
                re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id), prefix + "invalid ID")
        require(request_id not in seen, prefix + "duplicate ID")
        seen.add(request_id)
        arrival = row["arrival_s"]
        require(type(arrival) in (int, Decimal), prefix + "arrival must be numeric")
        arrival = Decimal(arrival)
        require(arrival.is_finite() and arrival >= 0, prefix + "invalid arrival")
        require(arrival.as_tuple().exponent >= -6, prefix + "arrival exceeds microsecond precision")
        require(arrival >= previous, prefix + "decreasing arrival")
        previous = arrival
        label = row["prompt_class"]
        require(isinstance(label, str) and label in INTERVALS, prefix + "invalid prompt class")
        text = row["prompt_text"]
        require(isinstance(text, str) and text, prefix + "empty/invalid prompt")
        try:
            text.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError(prefix + "invalid Unicode prompt") from exc
        count, limit = row["num_prompt_tokens"], row["max_new_tokens"]
        require(positive_int(count), prefix + "invalid prompt token count")
        require(positive_int(limit), prefix + "invalid generation limit")
        actual = len(tokenizer.encode(text, add_special_tokens=False, truncation=False))
        require(count == actual, prefix + "tokenizer length mismatch")
        low, high = INTERVALS[label]
        require(low <= count <= high, prefix + "prompt outside class interval")
        require(count + limit <= context_limit, prefix + "context limit exceeded")


def encode_trace(records):
    """Serialize already validated records without float formatting ambiguity."""
    lines = []
    for row in records:
        fields = []
        for key in sorted(row):
            value = format(row[key], ".6f") if key == "arrival_s" else compact(row[key])
            fields.append(compact(key) + ":" + value)
        lines.append("{" + ",".join(fields) + "}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def validate_trace_bytes(data, tokenizer, context_limit=256):
    try:
        text = data.decode("utf-8")
        require(text and text.endswith("\n") and "\r" not in text and
                not text.startswith("\ufeff"), "invalid JSONL encoding/line endings")
        lines = text[:-1].split("\n")
        require(all(lines), "empty JSONL line")
        records = [strict_json(line) for line in lines]
        validate_records(records, tokenizer, context_limit)
        # Decimal preserves negative zero, which needs an explicit rejection.
        require(all(not Decimal(r["arrival_s"]).is_signed() for r in records),
                "negative-zero arrival is not canonical")
        require(encode_trace(records) == data, "noncanonical JSONL serialization")
        return records
    except (UnicodeError, ArithmeticError) as exc:
        raise ValueError(f"invalid trace encoding/number: {exc}") from exc


def git_output(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def asset_metadata(assets):
    return {
        "model": {"repository": MODEL_ID, "revision": REVISION,
                  "files_sha256": {name: assets[name] for name in ("config.json", "model.safetensors")}},
        "tokenizer": {"repository": MODEL_ID, "revision": REVISION,
                      "class": "Qwen2TokenizerFast", "transformers_version": version("transformers"),
                      "tokenizers_version": version("tokenizers"),
                      "files_sha256": {name: assets[name] for name in TOKENIZER_FILES}},
    }


def make_metadata(data, records, seed, assets):
    digest = sha256(data)
    return {
        "schema_version": SCHEMA, "profile_id": PROFILE, "trace_id": f"{PROFILE}-{digest}",
        "seed": seed, "request_count": len(records), "class_counts": dict(Counter(
            row["prompt_class"] for row in records)), "max_new_tokens": 16,
        "trace_sha256": digest, "context_limit": 256,
        "generation_recipe": RECIPE, "prompt_source": PROMPT_SOURCE,
        "tokenization": TOKENIZATION, "sampling": SAMPLING,
        "generator": {
            "identity": "scripts/make_trace.py", "version": "1",
            "source_sha256": file_hash(Path(__file__)),
            "project_commit": git_output("rev-parse", "HEAD").decode().strip(),
            "dirty": bool(git_output("status", "--porcelain")),
            "tracked_diff_sha256": sha256(git_output("diff", "--binary", "HEAD")),
            "rng": "Python random.Random MT19937; shuffle",
            "python_version": platform.python_version(),
        },
        **asset_metadata(assets),
    }


def json_equal(left, right):
    """Compare JSON types as well as values (True and 1 must differ)."""
    # Metadata read with Decimal must be converted only for JSON number output.
    def normalize(value):
        if isinstance(value, Decimal):
            require(value.is_finite(), "nonfinite metadata number")
            return float(value)
        if isinstance(value, dict):
            return {k: normalize(v) for k, v in value.items()}
        if isinstance(value, list):
            return [normalize(v) for v in value]
        return value
    return compact(normalize(left)) == compact(normalize(right))


def validate_metadata(meta, data, records, assets):
    require(type(meta) is dict, "metadata must be an object")
    expected = {
        "schema_version": SCHEMA, "profile_id": PROFILE,
        "trace_id": f"{PROFILE}-{sha256(data)}", "trace_sha256": sha256(data),
        "request_count": 12, "class_counts": CLASS_COUNTS, "max_new_tokens": 16,
        "context_limit": 256, "generation_recipe": RECIPE, "prompt_source": PROMPT_SOURCE,
        "tokenization": TOKENIZATION, "sampling": SAMPLING, **asset_metadata(assets),
    }
    require(set(meta) == set(expected) | {"seed", "generator"}, "unexpected/missing metadata fields")
    for key, value in expected.items():
        require(json_equal(meta[key], value), f"metadata mismatch: {key}")
    require(type(meta["seed"]) is int and meta["seed"] >= 0, "invalid construction seed")
    generator = meta["generator"]
    require(type(generator) is dict, "invalid generator provenance")
    require(set(generator) == {"identity", "version", "source_sha256", "project_commit",
                              "dirty", "tracked_diff_sha256", "rng", "python_version"},
            "missing/unknown generator provenance")
    for key, length in (("source_sha256", 64), ("tracked_diff_sha256", 64), ("project_commit", 40)):
        require(isinstance(generator[key], str) and
                re.fullmatch(r"[0-9a-f]{%d}" % length, generator[key]), f"invalid {key}")
    require(generator["identity"] == "scripts/make_trace.py" and generator["version"] == "1",
            "unsupported generator")
    require(type(generator["dirty"]) is bool and
            generator["rng"] == "Python random.Random MT19937; shuffle" and
            isinstance(generator["python_version"], str) and
            re.fullmatch(r"\d+\.\d+\.\d+", generator["python_version"]), "invalid RNG provenance")
    require(len(records) == 12 and dict(Counter(r["prompt_class"] for r in records)) == CLASS_COUNTS,
            "development class/count mismatch")
    classes = list(RECIPE["initial_class_order"])
    random.Random(meta["seed"]).shuffle(classes)
    for i, row in enumerate(records):
        require(row["arrival_s"] == Decimal(i // 3) / 4, "development arrival mismatch")
        require(row["max_new_tokens"] == 16, "development generation cap mismatch")
        require(row["request_id"] == f"dev-{i+1:06d}", "development ID/order mismatch")
        require(row["prompt_class"] == classes[i], "seed/class assignment mismatch")


def write_package(output, data, metadata_bytes):
    """Exclusive creation protects prior artifacts, including an existing sidecar."""
    output = Path(output)
    sidecar = output.with_suffix(".meta.json")
    require(output.suffix == ".jsonl", "output must end in .jsonl")
    for path in (output, sidecar):
        require(not path.exists() and not path.is_symlink(), f"refusing to overwrite: {path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    created = []
    try:
        for path, payload in ((output, data), (sidecar, metadata_bytes)):
            with path.open("xb") as stream:
                created.append(path)
                stream.write(payload)
    except OSError:
        for path in created:
            path.unlink()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, help="explicit nonnegative construction seed")
    parser.add_argument("--output", type=Path, help="JSONL output; default workloads/dev_trace.jsonl")
    parser.add_argument("--model", type=Path, default=ROOT / "models/Qwen3-0.6B",
                        help="local pinned snapshot directory; never downloaded")
    parser.add_argument("--validate", type=Path, metavar="TRACE", help="validate existing JSONL and sibling .meta.json")
    args = parser.parse_args()
    try:
        if args.validate:
            require(args.seed is None and args.output is None,
                    "--validate cannot be combined with --seed or --output")
            output = args.validate
        else:
            require(type(args.seed) is int and args.seed >= 0, "generation requires --seed >= 0")
            output = args.output or ROOT / "workloads/dev_trace.jsonl"
            require(output.suffix == ".jsonl", "output must end in .jsonl")
            for path in (output, output.with_suffix(".meta.json")):
                require(not path.exists() and not path.is_symlink(), f"refusing to overwrite: {path}")
        tokenizer, assets = load_local_tokenizer(args.model)
        if args.validate:
            data = output.read_bytes()
            records = validate_trace_bytes(data, tokenizer)
            metadata_bytes = output.with_suffix(".meta.json").read_bytes()
            meta = strict_json(metadata_bytes.decode("utf-8"))
            validate_metadata(meta, data, records, assets)
        else:
            records = generate_records(tokenizer, args.seed)
            data = encode_trace(records)
            meta = make_metadata(data, records, args.seed, assets)
            validate_trace_bytes(data, tokenizer)
            validate_metadata(meta, data, records, assets)
            metadata_bytes = (json.dumps(meta, sort_keys=True, indent=2, ensure_ascii=False,
                                        allow_nan=False) + "\n").encode("utf-8")
            write_package(output, data, metadata_bytes)
        print(json.dumps({"status": "valid", "trace": str(output), "seed": meta["seed"],
                          "request_count": len(records), "class_counts": meta["class_counts"],
                          "prompt_token_counts": [r["num_prompt_tokens"] for r in records],
                          "trace_sha256": sha256(data), "metadata_sha256": sha256(metadata_bytes)},
                         sort_keys=True))
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()
