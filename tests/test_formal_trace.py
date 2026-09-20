"""CPU-only validation of the frozen formal-mixed-v1 package."""
from collections import Counter
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import make_formal_trace as formal
import make_trace


class FormalTraceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokenizer, cls.assets = make_trace.load_local_tokenizer(ROOT / "models/Qwen3-0.6B")

    def test_each_seed_is_deterministic_and_has_frozen_recipe(self):
        orders = []
        for seed in formal.SEEDS:
            first = formal.generate_records(self.tokenizer, seed)
            second = formal.generate_records(self.tokenizer, seed)
            data = make_trace.encode_trace(first)
            self.assertEqual(data, make_trace.encode_trace(second))
            self.assertEqual(len(first), 60)
            self.assertEqual(Counter(r["prompt_class"] for r in first), formal.CLASS_COUNTS)
            self.assertEqual([r["arrival_s"] for r in first],
                             [formal.Decimal(i // 3) / 4 for i in range(60)])
            self.assertTrue(all(r["num_prompt_tokens"] == make_trace.TARGETS[r["prompt_class"]]
                                and r["max_new_tokens"] == 16 and
                                r["num_prompt_tokens"] + 16 <= 256 for r in first))
            self.assertEqual(len({r["request_id"] for r in first}), 60)
            orders.append(tuple(r["prompt_class"] for r in first))
        self.assertEqual(len(set(orders)), 3)

    def test_package_rejects_changed_bytes_or_metadata(self):
        records = formal.generate_records(self.tokenizer, 101)
        data = make_trace.encode_trace(records)
        meta = formal.make_metadata(data, records, 101, self.assets)
        meta_bytes = (json.dumps(meta, sort_keys=True, indent=2,
                                 ensure_ascii=False, allow_nan=False) + "\n").encode()
        validated, parsed = formal.validate_package(data, meta_bytes, self.tokenizer, self.assets)
        self.assertEqual(validated, records)
        self.assertEqual(parsed["trace_sha256"], make_trace.sha256(data))
        broken = copy.deepcopy(meta)
        broken["seed"] = 202
        with self.assertRaises(ValueError):
            formal.validate_package(data, json.dumps(broken).encode(), self.tokenizer, self.assets)
        broken = copy.deepcopy(meta)
        broken["trace_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            formal.validate_package(data, json.dumps(broken).encode(), self.tokenizer, self.assets)
        with self.assertRaises(ValueError):
            formal.validate_package(data.replace(b'"max_new_tokens":16', b'"max_new_tokens":17', 1),
                                    meta_bytes, self.tokenizer, self.assets)


if __name__ == "__main__":
    unittest.main()
