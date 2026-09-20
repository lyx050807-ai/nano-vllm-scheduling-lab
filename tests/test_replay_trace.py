"""Release timing tests: deterministic clocks plus a relaxed real-clock dry run."""
from decimal import Decimal
import copy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SCRIPT = ROOT / "scripts/replay_trace.py"


class FakeClock:
    def __init__(self, oversleep_ns=0, early_once=False):
        self.now = 10_000_000_000
        self.oversleep_ns = oversleep_ns
        self.early_once = early_once
        self.sleeps = []

    def clock_ns(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        ns = round(seconds * 1_000_000_000)
        if self.early_once:
            self.early_once = False
            ns //= 2
        self.now += ns + self.oversleep_ns


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.exists(), "CPU replay not implemented")
        self.replay = importlib.import_module("replay_trace")
        self.requests = [json.loads(line, parse_float=Decimal) for line in
                         (ROOT / "workloads/dev_trace.jsonl").read_text().splitlines()]

    def test_trace_order_ties_and_exactly_once(self):
        clock = FakeClock()
        received = []
        original = copy.deepcopy(self.requests)
        records = self.replay.replay_requests(self.requests, received.append,
                                             clock_ns=clock.clock_ns, sleep=clock.sleep)
        self.assertEqual(received, original)
        self.assertEqual(self.requests, original)
        self.assertEqual([r["request_id"] for r in records],
                         [f"dev-{i:06d}" for i in range(1, 13)])
        self.assertEqual([r["actual_release_s"] for r in records],
                         [0.0]*3 + [0.25]*3 + [0.5]*3 + [0.75]*3)
        self.assertEqual([r["release_error_ms"] for r in records], [0.0]*12)

    def test_callback_cost_does_not_shift_absolute_targets(self):
        clock = FakeClock()
        requests = [self.requests[i] for i in [0, 3, 6, 9]]
        def callback(request):
            clock.now += 100_000_000
        records = self.replay.replay_requests(requests, callback,
                                             clock_ns=clock.clock_ns, sleep=clock.sleep)
        self.assertEqual([r["actual_release_s"] for r in records], [0.0, 0.25, 0.5, 0.75])
        for wait in clock.sleeps:
            self.assertAlmostEqual(wait, 0.15)

    def test_oversleep_is_not_accumulated(self):
        clock = FakeClock(oversleep_ns=10_000_000)
        records = self.replay.replay_requests([self.requests[i] for i in [3, 6, 9]],
                                             clock_ns=clock.clock_ns, sleep=clock.sleep)
        self.assertEqual([r["actual_release_s"] for r in records], [0.26, 0.51, 0.76])
        self.assertEqual([r["release_error_ms"] for r in records], [10.0]*3)

    def test_overdue_requests_release_without_additional_sleep(self):
        clock = FakeClock()
        def callback(request):
            if request["request_id"] == "dev-000001":
                clock.now += 600_000_000
        records = self.replay.replay_requests([self.requests[i] for i in [0, 3, 6, 9]], callback,
                                             clock_ns=clock.clock_ns, sleep=clock.sleep)
        self.assertEqual([r["actual_release_s"] for r in records], [0.0, 0.6, 0.6, 0.75])
        self.assertEqual([r["release_error_ms"] for r in records], [0.0, 350.0, 100.0, 0.0])
        self.assertEqual(clock.sleeps, [0.15])

    def test_early_wakeup_rechecks_target(self):
        clock = FakeClock(early_once=True)
        records = self.replay.replay_requests([self.requests[3]],
                                             clock_ns=clock.clock_ns, sleep=clock.sleep)
        self.assertEqual(clock.sleeps, [0.25, 0.125])
        self.assertEqual(records[0]["actual_release_s"], 0.25)

    def test_bad_arrivals_rejected_before_clock_or_callback(self):
        def unexpected(*args):
            self.fail("invalid input reached timing/callback")
        variants = [[], list(reversed(self.requests)), [self.requests[0]]*2]
        for value in [Decimal('-1'), Decimal('NaN'), Decimal('Infinity'), True,
                      '0.0', Decimal('0.0000001')]:
            rows = copy.deepcopy(self.requests)
            rows[-1]['arrival_s'] = value
            variants.append(rows)
        for rows in variants:
            with self.subTest(rows=rows[-1:] if rows else []):
                with self.assertRaises(ValueError):
                    self.replay.replay_requests(rows, unexpected, clock_ns=unexpected, sleep=unexpected)

    def test_callback_failure_is_not_retried(self):
        clock = FakeClock()
        seen = []
        def callback(request):
            seen.append(request['request_id'])
            raise RuntimeError('callback failed')
        with self.assertRaisesRegex(RuntimeError, 'callback failed'):
            self.replay.replay_requests(self.requests, callback,
                                       clock_ns=clock.clock_ns, sleep=clock.sleep)
        self.assertEqual(seen, ['dev-000001'])

    def test_callback_mutation_does_not_change_input_or_diagnostics(self):
        clock = FakeClock()
        original = copy.deepcopy(self.requests)
        def callback(request):
            request['arrival_s'] = 99
            request['request_id'] = 'changed'
        records = self.replay.replay_requests(self.requests, callback,
                                             clock_ns=clock.clock_ns, sleep=clock.sleep)
        self.assertEqual(self.requests, original)
        self.assertEqual(records[0]['request_id'], 'dev-000001')
        self.assertEqual(records[-1]['arrival_s'], 0.75)

    def test_invalid_package_never_starts_replay(self):
        def unexpected(*args):
            self.fail('invalid package started replay')
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory)/'bad.jsonl'
            trace.write_bytes((ROOT/'workloads/dev_trace.jsonl').read_bytes().replace(
                b'"num_prompt_tokens":96', b'"num_prompt_tokens":95', 1))
            trace.with_suffix('.meta.json').write_bytes((ROOT/'workloads/dev_trace.meta.json').read_bytes())
            with self.assertRaises(ValueError):
                self.replay.replay_trace(trace, unexpected, clock_ns=unexpected, sleep=unexpected)
            trace.write_bytes((ROOT/'workloads/dev_trace.jsonl').read_bytes())
            meta = json.loads(trace.with_suffix('.meta.json').read_text())
            meta['trace_sha256'] = '0'*64
            trace.with_suffix('.meta.json').write_text(json.dumps(meta))
            with self.assertRaises(ValueError):
                self.replay.replay_trace(trace, unexpected, clock_ns=unexpected, sleep=unexpected)

    def test_real_clock_cli_and_output_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'timing.jsonl'
            command = [sys.executable, str(SCRIPT), '--output', str(output)]
            env = {**os.environ, 'CUDA_VISIBLE_DEVICES': ''}
            result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            rows = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(len(rows), 12)
            self.assertEqual([r['request_id'] for r in rows], [r['request_id'] for r in self.requests])
            for row in rows:
                self.assertGreaterEqual(row['actual_release_s'], row['arrival_s'])
                self.assertAlmostEqual(row['release_error_ms'],
                                       (row['actual_release_s']-row['arrival_s'])*1000, places=6)
            # Broad infrastructure sanity bound, not a real-time or performance promise.
            self.assertLess(summary['max_absolute_release_error_ms'], 2000)
            self.assertAlmostEqual(summary['mean_absolute_release_error_ms'],
                                   sum(abs(r['release_error_ms']) for r in rows)/12)
            before = output.read_bytes()
            result = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
