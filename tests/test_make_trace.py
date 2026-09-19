"""CPU-only trace contract tests; run with unittest discover -s tests."""
import copy
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/make_trace.py"
ENV = {**os.environ, "CUDA_VISIBLE_DEVICES": "", "HF_HUB_OFFLINE": "1",
       "TRANSFORMERS_OFFLINE": "1"}


class TraceCLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                              cwd=ROOT, env=ENV, capture_output=True, text=True)

    def test_cli_reproducibility_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / f"trace-{i}.jsonl" for i in range(3)]
            for path, seed in zip(paths, [42, 42, 43]):
                result = self.run_cli("--seed", seed, "--output", path)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
            a, b, c = [p.read_bytes() for p in paths]
            self.assertEqual(a, b)
            self.assertEqual(hashlib.sha256(a).hexdigest(), hashlib.sha256(b).hexdigest())
            self.assertNotEqual(a, c)
            records = [json.loads(line) for line in a.splitlines()]
            other = [json.loads(line) for line in c.splitlines()]
            self.assertNotEqual([r["prompt_class"] for r in records],
                                [r["prompt_class"] for r in other])
            self.assertEqual(len(records), 12)
            self.assertEqual({k: sum(r["prompt_class"] == k for r in records)
                              for k in ("short", "medium", "long")},
                             {"short": 4, "medium": 4, "long": 4})
            self.assertEqual([r["arrival_s"] for r in records],
                             [0.0]*3 + [0.25]*3 + [0.5]*3 + [0.75]*3)
            self.assertEqual({r["max_new_tokens"] for r in records}, {16})
            meta = json.loads(paths[0].with_suffix(".meta.json").read_text())
            self.assertEqual(meta["trace_sha256"], hashlib.sha256(a).hexdigest())
            self.assertEqual(meta["seed"], 42)
            result = self.run_cli("--validate", paths[0])
            self.assertEqual(result.returncode, 0, result.stderr)
            meta_before = paths[0].with_suffix(".meta.json").read_bytes()
            result = self.run_cli("--seed", 43, "--output", paths[0])
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(paths[0].read_bytes(), a)
            self.assertEqual(paths[0].with_suffix(".meta.json").read_bytes(), meta_before)

    def test_explicit_seed_and_local_model_required(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "trace.jsonl"
            for args in [("--output", output),
                         ("--seed", -1, "--output", output),
                         ("--seed", 42, "--model", Path(directory)/"missing", "--output", output)]:
                result = self.run_cli(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())
                self.assertFalse(output.with_suffix(".meta.json").exists())


class TraceValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SCRIPT.exists():
            return
        spec = importlib.util.spec_from_file_location("make_trace", SCRIPT)
        cls.trace = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.trace)
        cls.tokenizer, cls.assets = cls.trace.load_local_tokenizer(ROOT / "models/Qwen3-0.6B")

    def setUp(self):
        self.assertTrue(SCRIPT.exists(), "trace generator not implemented")
        self.records = self.trace.generate_records(self.tokenizer, 42)

    def test_changed_tokenizer_asset_is_rejected(self):
        # Even a harmless tokenizer-config whitespace edit invalidates snapshot identity.
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory)
            original = ROOT / "models/Qwen3-0.6B"
            for name in ("config.json", "model.safetensors", "tokenizer.json",
                         "vocab.json", "merges.txt"):
                (model / name).symlink_to(original / name)
            (model / "tokenizer_config.json").write_bytes(
                (original / "tokenizer_config.json").read_bytes() + b"\n")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                self.trace.load_local_tokenizer(model)

    def test_cpu_only_tokenizer_path(self):
        self.assertNotIn("torch", sys.modules)
        self.assertNotIn("nanovllm", sys.modules)

    def test_actual_token_counts_and_canonical_encoding(self):
        for r in self.records:
            ids = self.tokenizer.encode(r["prompt_text"], add_special_tokens=False, truncation=False)
            self.assertEqual(r["num_prompt_tokens"], len(ids))
            low, high = {"short": (24,40), "medium": (88,104), "long": (184,200)}[r["prompt_class"]]
            self.assertTrue(low <= len(ids) <= high)
            self.assertLessEqual(len(ids) + r["max_new_tokens"], 256)
        data = self.trace.encode_trace(self.records)
        self.assertTrue(data.startswith(b'{"arrival_s":0.000000,'))
        self.assertTrue(data.endswith(b'\n'))
        self.assertNotIn(b'\r', data)
        self.assertEqual(len(data.splitlines()), 12)
        self.trace.validate_trace_bytes(data, self.tokenizer)

    def test_invalid_request_fields_rejected(self):
        changes = [
            ("schema_version", "request-trace-v2"), ("request_id", "bad id"),
            ("arrival_s", Decimal("-0.1")), ("arrival_s", Decimal("0.0000001")),
            ("arrival_s", True), ("arrival_s", Decimal("NaN")),
            ("arrival_s", Decimal("Infinity")), ("arrival_s", "0.0"),
            ("prompt_class", "unknown"), ("prompt_class", []),
            ("prompt_text", ""), ("prompt_text", None),
            ("num_prompt_tokens", 1), ("num_prompt_tokens", True),
            ("num_prompt_tokens", 32.0), ("max_new_tokens", 0),
            ("max_new_tokens", -1), ("max_new_tokens", True),
            ("max_new_tokens", 300), ("actual_output_length", 10),
        ]
        for field, value in changes:
            with self.subTest(field=field, value=value):
                records = copy.deepcopy(self.records)
                records[0][field] = value
                with self.assertRaises(ValueError):
                    self.trace.validate_records(records, self.tokenizer)
        records = copy.deepcopy(self.records)
        records[1]["request_id"] = records[0]["request_id"]
        with self.assertRaises(ValueError):
            self.trace.validate_records(records, self.tokenizer)
        records = copy.deepcopy(self.records)
        records[3]["arrival_s"] = Decimal("0.5")
        with self.assertRaises(ValueError):
            self.trace.validate_records(records, self.tokenizer)
        del records[0]["prompt_text"]
        with self.assertRaises(ValueError):
            self.trace.validate_records(records, self.tokenizer)
        with self.assertRaises(ValueError):
            self.trace.validate_records([], self.tokenizer)

    def test_context_boundary_is_inclusive(self):
        record = copy.deepcopy(self.records[0])
        limit = record["num_prompt_tokens"] + record["max_new_tokens"]
        self.trace.validate_records([record], self.tokenizer, context_limit=limit)
        with self.assertRaises(ValueError):
            self.trace.validate_records([record], self.tokenizer, context_limit=limit-1)

    def test_noncanonical_or_malformed_json_rejected(self):
        data = self.trace.encode_trace(self.records)
        corruptions = [b'', b'\xef\xbb\xbf'+data, data+b'\n', data[:-1],
                       data.replace(b'\n', b'\r\n'),
                       data.replace(b'0.000000', b'-0.000000', 1),
                       data.replace(b'0.000000', b'0e0', 1),
                       data.replace(b'0.000000', b'NaN', 1),
                       data.replace(b'{', b'{"arrival_s":0.000000,', 1),
                       data.replace(b'{', b'{ ', 1), b'[]\n']
        for data in corruptions:
            with self.subTest(prefix=data[:40]):
                with self.assertRaises(ValueError):
                    self.trace.validate_trace_bytes(data, self.tokenizer)

    def test_metadata_tampering_and_profile_mismatch_rejected(self):
        data = self.trace.encode_trace(self.records)
        meta = self.trace.make_metadata(data, self.records, 42, self.assets)
        self.trace.validate_metadata(meta, data, self.records, self.assets)
        changes = [("trace_sha256", "0"*64), ("schema_version", "bad"),
                   ("request_count", 11), ("request_count", True),
                   ("class_counts", {"short": 12}), ("context_limit", 40960),
                   ("max_new_tokens", 32), ("seed", -1), ("profile_id", "formal")]
        for key, value in changes:
            with self.subTest(key=key):
                bad = copy.deepcopy(meta); bad[key] = value
                with self.assertRaises(ValueError):
                    self.trace.validate_metadata(bad, data, self.records, self.assets)
        for field, key, value in [("tokenizer", "revision", "main"),
                                  ("model", "revision", "main"),
                                  ("tokenization", "add_special_tokens", True),
                                  ("sampling", "temperature", 0),
                                  ("sampling", "ignore_eos", "false")]:
            bad = copy.deepcopy(meta); bad[field][key] = value
            with self.assertRaises(ValueError):
                self.trace.validate_metadata(bad, data, self.records, self.assets)
        bad = copy.deepcopy(meta)
        del bad["generator"]
        with self.assertRaises(ValueError):
            self.trace.validate_metadata(bad, data, self.records, self.assets)
        records = copy.deepcopy(self.records)
        records[3]["arrival_s"] = Decimal("0.125000")
        other = self.trace.encode_trace(records)
        bad = copy.deepcopy(meta); bad["trace_sha256"] = hashlib.sha256(other).hexdigest()
        with self.assertRaises(ValueError):
            self.trace.validate_metadata(bad, other, records, self.assets)


if __name__ == "__main__":
    unittest.main()
