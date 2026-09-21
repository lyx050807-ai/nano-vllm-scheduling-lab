"""CPU contracts for the frozen formal benchmark plan and aggregation."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class FormalBenchmarkTests(unittest.TestCase):
    def setUp(self):
        global benchmark, aggregate
        import formal_benchmark as benchmark
        import aggregate_formal as aggregate

    def test_matrix_is_frozen_balanced_unique_and_deterministic(self):
        first = benchmark.build_plan(ROOT)
        second = benchmark.build_plan(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 45)
        self.assertEqual(len({row["run_id"] for row in first}), 45)
        self.assertEqual(len({row["artifact_directory"] for row in first}), 45)
        self.assertEqual(Counter((r["policy"], r["trace_seed"]) for r in first),
                         Counter({(p, s): 5 for p in benchmark.POLICIES
                                             for s in benchmark.TRACE_SEEDS}))
        self.assertEqual(Counter(r["policy"] for r in first if r["block_position"] == 0),
                         Counter({p: 5 for p in benchmark.POLICIES}))
        self.assertEqual([r["run_order_index"] for r in first], list(range(45)))
        self.assertTrue(all(r["status"] == "pending" for r in first))

    def test_frozen_trace_hashes_and_run_identity(self):
        plan = benchmark.build_plan(ROOT)
        hashes = {101: "ff3acfd57a153030e76d06af491fed20bd1498db7e12580db345c8bb1ff92ac8",
                  202: "e3c82a96d5b7295b7e98d4d4884476ddd9cc5ee1701831f4d5e63e8872e94078",
                  303: "8721930601de3f96d23287cef9038a0967f653133987a154ca18ae8e5b4d6866"}
        sidecars = {101: "fb298e8ba8019d86e54c62487eb5906e0a59d9889ca5ca73881560f53e0b1476",
                    202: "8603718474005a5dc3f18fac2b76cd4e37d23252dd19ea124c5f34734d95ebfc",
                    303: "af6d5affaf40cbd7e72a0961d37d10dcdbe59664ce8a563e954ec844862d4526"}
        for row in plan:
            self.assertEqual(row["trace_sha256"], hashes[row["trace_seed"]])
            self.assertEqual(row["trace_metadata_sha256"], sidecars[row["trace_seed"]])
            self.assertIn(f"seed{row['trace_seed']}", row["run_id"])
            self.assertIn(f"rep{row['repeat_index']}", row["run_id"])
            self.assertTrue(row["run_id"].endswith(row["policy"]))
            self.assertEqual(row["paired_key"],
                             f"seed{row['trace_seed']}-rep{row['repeat_index']}")
            self.assertEqual(row["aging_rate_tokens_per_second"],
                             320 if row["policy"] == "aged_short_prompt" else None)
            self.assertEqual(row["model_revision"],
                             "c1899de289a04d12100db370d81485cdf75e47ca")
            self.assertEqual(row["generation_configuration"]["inference_seed"], 42)

    def test_manifest_exclusive_creation_serialization_and_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = benchmark.create_manifest(root, ROOT)
            loaded = benchmark.load_manifest(root / "manifest.json", ROOT)
            self.assertEqual(loaded, manifest)
            with self.assertRaises(FileExistsError):
                benchmark.create_manifest(root, ROOT)
            loaded["runs"][0]["status"] = "success"
            loaded["runs"][1]["status"] = "timeout"
            benchmark.write_manifest(root / "manifest.json", loaded, replace=True)
            resumed = benchmark.pending_runs(benchmark.load_manifest(root / "manifest.json", ROOT))
            self.assertNotIn(manifest["runs"][0]["run_id"], {r["run_id"] for r in resumed})
            self.assertNotIn(manifest["runs"][1]["run_id"], {r["run_id"] for r in resumed})
            self.assertEqual(len(resumed), 43)

    def test_frozen_manifest_remains_loadable_after_later_git_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = benchmark.create_manifest(root, ROOT)
            with patch.object(benchmark, "git_output", return_value="later-project-commit"):
                loaded = benchmark.load_manifest(root / "manifest.json", ROOT)
            self.assertEqual(loaded, created)

    def test_run_directory_and_attempt_creation_never_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = benchmark.build_plan(ROOT)[0]
            created = benchmark.create_run_directory(Path(tmp), run)
            self.assertTrue(created.is_dir())
            with self.assertRaises(FileExistsError):
                benchmark.create_run_directory(Path(tmp), run)
            first = benchmark.create_retry_directory(created, "external-infrastructure", None)
            second = benchmark.create_retry_directory(created, "external-infrastructure", first.name)
            self.assertEqual(first.name, "attempt-001")
            self.assertEqual(second.name, "attempt-002")
            retry = json.loads((second / "retry.json").read_text())
            self.assertEqual(retry["retry_of"], "attempt-001")

    def test_interrupted_running_entry_becomes_recorded_failure_on_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = benchmark.create_manifest(root, ROOT)
            run = manifest["runs"][0]
            benchmark.create_run_directory(root, run)
            run["status"] = "running"
            benchmark.write_manifest(root / "manifest.json", manifest, replace=True)
            resumed = benchmark.reconcile_interrupted(root / "manifest.json", ROOT)
            self.assertEqual(resumed["runs"][0]["status"], "runner_failure")
            self.assertEqual(resumed["runs"][0]["attempts"][0]["reason"],
                             "orchestrator_interrupted")
            self.assertEqual(len(benchmark.pending_runs(resumed)), 44)
            self.assertTrue((root / run["artifact_directory"]).is_dir())

    def test_resume_stops_before_launch_if_previous_run_was_interrupted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = benchmark.create_manifest(root, ROOT)
            manifest["runs"][0]["status"] = "running"
            benchmark.write_manifest(root / "manifest.json", manifest, replace=True)
            with patch.object(benchmark, "execute_run") as launch:
                with self.assertRaisesRegex(RuntimeError, "interrupted"):
                    benchmark.execute_pending(root / "manifest.json", ROOT)
                launch.assert_not_called()
            recorded = benchmark.load_manifest(root / "manifest.json", ROOT)
            self.assertEqual(recorded["runs"][0]["status"], "runner_failure")

    def test_cooldown_waits_from_previous_process_exit(self):
        now = [datetime(2026, 9, 21, tzinfo=timezone.utc)]
        previous = (now[0] - timedelta(seconds=11)).isoformat()
        slept = []
        def sleep(seconds):
            slept.append(seconds)
            now[0] += timedelta(seconds=seconds)
        gap = benchmark.wait_cooldown(previous, clock=lambda: now[0], sleep=sleep)
        self.assertEqual(slept, [19])
        self.assertEqual(gap, 30)

    def test_failure_classification_and_record_are_explicit(self):
        cases = [(0, "completed", "passed", "success"),
                 (2, "timed_out", "partial", "timeout"),
                 (1, "failed", "partial", "runner_failure"),
                 (1, "failed", "failed", "lifecycle_failure")]
        for code, capture, lifecycle, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(benchmark.classify_result(code, capture, lifecycle, ""), expected)
        self.assertEqual(benchmark.classify_result(1, "failed", "partial",
                                                    "CUDA out of memory"), "oom")

    def test_success_requires_frozen_identity_and_complete_records(self):
        run = benchmark.build_plan(ROOT)[0]
        meta = {"policy": run["policy"], "trace_sha256": run["trace_sha256"],
                "metadata_sha256": run["trace_metadata_sha256"],
                "request_count": 60, "completion_count": 60,
                "aging_rate_tokens_per_second": 320,
                "engine_config": {"scheduling_policy": run["policy"]}}
        rows = [{"request_id": f"formal-101-{i:06d}", "policy": run["policy"],
                 "status": "completed", "trace_sha256": run["trace_sha256"]}
                for i in range(1, 61)]
        self.assertTrue(benchmark.validate_success(run, meta, rows))
        with self.assertRaises(ValueError):
            benchmark.validate_success(run, {**meta, "policy": "short_prompt"}, rows)
        with self.assertRaises(ValueError):
            benchmark.validate_success(run, meta, rows[:-1])

    def test_aggregation_keeps_run_and_class_values_and_paired_keys(self):
        rows = []
        for prompt_class, value in (("short", 10.0), ("medium", 20.0), ("long", 30.0)):
            rows.append({"status": "completed", "prompt_class": prompt_class,
                         "ttft_ms": value, "queue_wait_ms": value + 1,
                         "e2e_latency_ms": value + 2, "engine_ttft_ms": value + 3,
                         "admission_overhead_ms": 1.0,
                         "token_times_s": [0.0, .01, .03], "finished_s": .5,
                         "release_s": 0.0})
        result = aggregate.summarize_run(rows, policy="baseline", trace_seed=101,
                                         repeat_index=2, run_id="x")
        self.assertEqual(result["paired_key"], "seed101-rep2")
        self.assertEqual(result["completion_rate"], 1.0)
        self.assertEqual(result["metrics"]["overall"]["ttft_ms"]["values"],
                         [10.0, 20.0, 30.0])
        self.assertEqual(result["metrics"]["long"]["e2e_latency_ms"]["values"], [32.0])
        for value in result["itl_ms"]["overall"]["per_request_mean_values"]:
            self.assertAlmostEqual(value, 15.0)
        self.assertEqual(result["throughput_requests_per_second"], 6.0)
        rows[-1]["status"] = "failed"
        self.assertIsNone(aggregate.summarize_run(rows, policy="baseline", trace_seed=101,
            repeat_index=2, run_id="x")["throughput_requests_per_second"])

    def test_aggregation_keeps_failed_runs_in_outcome_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = benchmark.create_manifest(root, ROOT)
            manifest["runs"][0]["status"] = "timeout"
            manifest["runs"][0]["completion_count"] = 17
            benchmark.write_manifest(root / "manifest.json", manifest, replace=True)
            result = aggregate.aggregate(root / "manifest.json")
            self.assertFalse(result["runs"])
            self.assertEqual(len(result["outcomes"]), 45)
            self.assertEqual(result["outcomes"][0]["status"], "timeout")
            self.assertEqual(result["outcomes"][0]["completion_count"], 17)
            self.assertEqual(result["outcomes"][0]["completion_rate"], 17 / 60)


if __name__ == "__main__":
    unittest.main()
