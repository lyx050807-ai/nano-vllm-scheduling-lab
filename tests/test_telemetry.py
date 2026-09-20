"""CPU telemetry contracts and real scheduler hooks with a fake GPU boundary."""
import importlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
UTILITY = ROOT / 'nanovllm/telemetry.py'


class Clock:
    def __init__(self):
        self.value = 1_000_000_000
    def __call__(self):
        self.value += 1_000_000
        return self.value


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(UTILITY.exists(), 'telemetry capture not implemented')
        spec = importlib.util.spec_from_file_location('telemetry_cpu', UTILITY)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.clock = Clock()
        self.capture = self.module.Telemetry(1_000_000_000, clock_ns=self.clock)
        self.capture.register(17, 'request-a', 32, 16)

    def test_initial_fields_unset_and_incomplete_json(self):
        row = self.capture.snapshot()['request-a']
        for name in ['admitted_s','first_scheduled_s','first_prefill_dispatch_s','first_token_s','finished_s']:
            self.assertIsNone(row[name])
        self.assertEqual(row['token_times_s'], [])
        self.assertIsNone(row['queue_wait_ms'])
        self.assertIsNone(row['engine_ttft_ms'])
        self.assertEqual(self.capture.snapshot(completed_only=True), {})
        self.assertEqual(json.loads(json.dumps(row)), row)

    def test_first_events_and_finish_are_write_once(self):
        self.capture.admitted(17)
        admitted = self.capture.snapshot()['request-a']['admitted_s']
        self.capture.admitted(17)
        self.assertEqual(admitted, self.capture.snapshot()['request-a']['admitted_s'])
        self.capture.scheduled([17])
        scheduled = self.capture.snapshot()['request-a']['first_scheduled_s']
        self.capture.scheduled([17])
        self.assertEqual(scheduled, self.capture.snapshot()['request-a']['first_scheduled_s'])
        self.capture.prefill_dispatched([17])
        self.capture.prefill_dispatched([17])
        self.capture.token(17)
        self.capture.token(17)
        self.capture.finished(17)
        before = self.capture.snapshot()['request-a']
        self.capture.finished(17)
        self.assertEqual(before, self.capture.snapshot()['request-a'])
        self.assertEqual(before['first_token_s'], before['token_times_s'][0])
        self.assertEqual(len(before['token_times_s']), 2)
        self.assertLess(before['token_times_s'][0], before['token_times_s'][1])
        self.assertLessEqual(before['token_times_s'][-1], before['finished_s'])
        self.assertEqual(set(self.capture.snapshot(completed_only=True)), {'request-a'})

    def test_batch_time_shared_and_existing_first_selection_preserved(self):
        self.capture.register(18, 'request-b', 96, 16)
        self.capture.admitted(17); self.capture.admitted(18)
        self.capture.scheduled([17,18])
        records = self.capture.snapshot()
        self.assertEqual(records['request-a']['first_scheduled_s'], records['request-b']['first_scheduled_s'])
        self.capture.scheduled([17])
        self.assertEqual(records['request-a']['first_scheduled_s'], self.capture.snapshot()['request-a']['first_scheduled_s'])

    def test_internal_metric_units_and_snapshot_copy(self):
        self.capture.admitted(17)   # 1 ms
        self.capture.scheduled([17])  # 2 ms
        self.capture.token(17)  # 3 ms
        row = self.capture.snapshot()['request-a']
        self.assertEqual(row['queue_wait_ms'], 1.0)
        self.assertEqual(row['engine_ttft_ms'], 2.0)
        self.assertNotIn('release_s', row)
        self.assertNotIn('ttft_ms', row)
        self.assertIsNone(row['finished_s'])
        row['token_times_s'].append(999)
        self.assertEqual(len(self.capture.snapshot()['request-a']['token_times_s']), 1)

    def test_duplicate_request_identity_rejected(self):
        with self.assertRaises(ValueError):
            self.capture.register(18, 'request-a', 32, 16)
        with self.assertRaises(ValueError):
            self.capture.register(17, 'another', 32, 16)


class EngineHookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Avoid eager package __init__/GPU runner imports. All scheduling, Sequence
        # and KV block-management code below is the real local implementation.
        package = ModuleType('nanovllm'); package.__path__ = [str(ROOT/'nanovllm')]
        runner = ModuleType('nanovllm.engine.model_runner')
        runner.ModelRunner = None
        cls.modules = patch.dict(sys.modules, {'nanovllm': package,
                                               'nanovllm.engine.model_runner': runner})
        cls.modules.start()
        cls.engine_module = importlib.import_module('nanovllm.engine.llm_engine')
        cls.scheduler_module = importlib.import_module('nanovllm.engine.scheduler')
        cls.Sequence = importlib.import_module('nanovllm.engine.sequence').Sequence
        cls.SamplingParams = importlib.import_module('nanovllm.sampling_params').SamplingParams

    @classmethod
    def tearDownClass(cls):
        cls.modules.stop()

    def engine(self, *, enabled=True, blocks=8, budget=256):
        engine = self.engine_module.LLMEngine.__new__(self.engine_module.LLMEngine)
        engine.telemetry = None
        engine.scheduler = self.scheduler_module.Scheduler(SimpleNamespace(
            max_num_seqs=2, max_num_batched_tokens=budget, eos=99,
            num_kvcache_blocks=blocks, kvcache_block_size=256))
        engine.model_runner = SimpleNamespace(call=lambda name, seqs, prefill: [7]*len(seqs))
        if enabled:
            self.assertTrue(hasattr(engine, 'enable_telemetry'), 'engine hooks not implemented')
            engine.enable_telemetry(1_000_000_000, clock_ns=Clock())
        return engine

    def test_partial_prefill_does_not_emit_token_timestamp(self):
        engine = self.engine(budget=128)
        engine.add_request(list(range(200)), self.SamplingParams(max_tokens=2), request_id='chunked')
        engine.step()
        row = engine.get_telemetry()['chunked']
        self.assertIsNotNone(row['first_scheduled_s'])
        self.assertIsNotNone(row['first_prefill_dispatch_s'])
        self.assertIsNone(row['first_token_s'])
        self.assertEqual(row['token_times_s'], [])
        selected = row['first_scheduled_s']
        engine.step()
        engine.step()
        row = engine.get_telemetry(completed_only=True)['chunked']
        self.assertEqual(row['first_scheduled_s'], selected)
        self.assertEqual(len(row['token_times_s']), 2)
        self.assertTrue(engine.is_finished())

    def test_eos_on_prefill_completes_without_decode(self):
        engine = self.engine()
        engine.model_runner.call = lambda *args: [99]
        engine.add_request([1,2], self.SamplingParams(max_tokens=16), request_id='eos')
        outputs, _ = engine.step()
        row = engine.get_telemetry(completed_only=True)['eos']
        self.assertEqual(outputs[0][1], [99])
        self.assertEqual(len(row['token_times_s']), 1)
        self.assertLessEqual(row['first_token_s'], row['finished_s'])
        self.assertEqual(len(engine.scheduler.block_manager.free_block_ids), 8)

    def test_capture_preserves_scheduler_and_preemption_results(self):
        def run(enabled):
            engine = self.engine(enabled=enabled, blocks=2, budget=512)
            for i in range(2):
                engine.add_request(list(range(256)), self.SamplingParams(max_tokens=2))
            snapshots = []
            first = None
            for _ in range(10):
                outputs, count = engine.step()
                if enabled and first is None:
                    first = engine.get_telemetry()
                bm = engine.scheduler.block_manager
                snapshots.append((count, [tokens for _,tokens in outputs],
                    [s.num_completion_tokens for s in engine.scheduler.waiting],
                    [s.num_completion_tokens for s in engine.scheduler.running],
                    list(bm.free_block_ids), sorted(bm.used_block_ids)))
                if engine.is_finished():
                    break
            self.assertTrue(engine.is_finished())
            if enabled:
                rows = engine.get_telemetry(completed_only=True)
                self.assertEqual(len(rows), 2)
                for key,row in rows.items():
                    self.assertEqual(len(row['token_times_s']), 2)
                    self.assertEqual(row['admitted_s'], first[key]['admitted_s'])
                    self.assertEqual(row['first_scheduled_s'], first[key]['first_scheduled_s'])
                self.assertTrue(any(snapshot[2] for snapshot in snapshots))
            return snapshots
        self.assertEqual(run(False), run(True))


if __name__ == '__main__':
    unittest.main()
