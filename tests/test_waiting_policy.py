"""CPU scheduling contracts for baseline and shortest-prompt selection."""
from collections import deque
from pathlib import Path
import sys
from types import ModuleType
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def scheduler(policy="baseline", *, budget=256, batch=1, blocks=16):
    return Scheduler(SimpleNamespace(scheduling_policy=policy, max_num_seqs=batch,
                     max_num_batched_tokens=budget, eos=999,
                     num_kvcache_blocks=blocks, kvcache_block_size=256))


def sequences(lengths):
    return [Sequence([i + 1] * n, SamplingParams(max_tokens=2))
            for i, n in enumerate(lengths)]


class WaitingPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Defer nano-vLLM imports so trace-generator tests can prove that their
        # tokenizer-only path never imports torch during test discovery. The
        # fake root also avoids importing the GPU engine through __init__.
        package = ModuleType('nanovllm')
        package.__path__ = [str(ROOT / 'nanovllm')]
        cls.modules = patch.dict(sys.modules, {'nanovllm': package})
        cls.modules.start()
        global Config, Scheduler, Sequence, SequenceStatus, SamplingParams, Telemetry
        from nanovllm.config import Config
        from nanovllm.engine.scheduler import Scheduler
        from nanovllm.engine.sequence import Sequence, SequenceStatus
        from nanovllm.sampling_params import SamplingParams
        from nanovllm.telemetry import Telemetry

    @classmethod
    def tearDownClass(cls):
        cls.modules.stop()

    def test_config_default_and_invalid_values(self):
        with patch("nanovllm.config.AutoConfig.from_pretrained",
                   return_value=SimpleNamespace(max_position_embeddings=40960)):
            default = Config(str(ROOT / "models/Qwen3-0.6B"))
            explicit = Config(str(ROOT / "models/Qwen3-0.6B"), scheduling_policy="baseline")
            self.assertEqual(default.scheduling_policy, "baseline")
            self.assertEqual(explicit.scheduling_policy, "baseline")
            positional = Config(str(ROOT / "models/Qwen3-0.6B"), 16384, 512, 4096,
                                0.9, 1, False, None, -1, 256, -1)
            self.assertEqual(positional.scheduling_policy, "baseline")
            self.assertEqual(positional.num_kvcache_blocks, -1)
            self.assertEqual(Config(str(ROOT / "models/Qwen3-0.6B"),
                                    scheduling_policy="short_prompt").scheduling_policy,
                             "short_prompt")
            for invalid in ("aged_short_prompt", "unknown", "BASELINE", None, 1):
                with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError,
                                                                            "scheduling_policy"):
                    Config(str(ROOT / "models/Qwen3-0.6B"), scheduling_policy=invalid)

    def test_selector_is_stable_and_does_not_mutate_waiting(self):
        from nanovllm.engine.waiting_policy import choose_waiting_index
        waiting = deque(sequences([192, 32, 96, 32]))
        before = list(waiting)
        self.assertEqual(choose_waiting_index(waiting, "baseline"), 0)
        self.assertEqual(choose_waiting_index(waiting, "short_prompt"), 1)
        self.assertEqual(list(waiting), before)
        waiting[1].append_token(7)  # generated history cannot change prompt priority
        waiting[3].max_tokens = 100  # output cap is not a priority input
        self.assertEqual(choose_waiting_index(waiting, "short_prompt"), 1)

    def test_example_order_and_non_head_removal(self):
        sched = scheduler("short_prompt")
        seqs = sequences([192, 32, 96, 32])
        for seq in seqs: sched.add(seq)
        chosen = []
        expected_remaining = [[0, 2, 3], [0, 2], [0], []]
        for remaining in expected_remaining:
            batch, prefill = sched.schedule()
            self.assertTrue(prefill)
            chosen.append(seqs.index(batch[0]))
            self.assertEqual([seqs.index(s) for s in sched.waiting], remaining)
        self.assertEqual(chosen, [1, 3, 2, 0])
        self.assertEqual(len(sched.running), 4)
        self.assertEqual(len({id(s) for s in sched.running}), 4)

    def test_default_and_explicit_baseline_preserve_head_and_trajectory(self):
        def trajectory(policy=None):
            config = SimpleNamespace(max_num_seqs=1, max_num_batched_tokens=128,
                       eos=999, num_kvcache_blocks=8, kvcache_block_size=256)
            if policy is not None: config.scheduling_policy = policy
            sched = Scheduler(config)
            seqs = sequences([192, 32, 96])
            for seq in seqs: sched.add(seq)
            states = []
            for _ in range(4):
                batch, prefill = sched.schedule()
                states.append((seqs.index(batch[0]), prefill,
                    [seqs.index(s) for s in sched.waiting],
                    [seqs.index(s) for s in sched.running],
                    batch[0].num_scheduled_tokens,
                    len(sched.block_manager.used_block_ids)))
                sched.postprocess(batch, [7], prefill)
            return states
        expected = [(0, True, [0, 1, 2], [], 128, 1),
                    (0, True, [1, 2], [0], 64, 1),
                    (1, True, [2], [0, 1], 32, 2),
                    (2, True, [], [0, 1, 2], 96, 3)]
        self.assertEqual(trajectory(), expected)
        self.assertEqual(trajectory("baseline"), expected)

    def test_selected_allocation_failure_does_not_backfill(self):
        sched = scheduler("short_prompt")
        long, short, medium = sequences([192, 32, 96])
        for seq in (long, short, medium): sched.add(seq)
        seen = []
        def can_allocate(seq):
            seen.append(seq)
            return -1 if seq is short else 0
        with patch.object(sched.block_manager, "can_allocate", side_effect=can_allocate):
            with self.assertRaises(AssertionError):
                sched.schedule()  # baseline also asserts with no runnable decode
        self.assertEqual(seen, [short])
        self.assertEqual(list(sched.waiting), [long, short, medium])
        self.assertFalse(sched.running)
        self.assertEqual(len(sched.block_manager.used_block_ids), 0)

    def test_non_first_chunk_stops_without_removal_or_fallback(self):
        sched = scheduler("short_prompt", budget=64, batch=2)
        short, medium, long = sequences([32, 96, 192])
        for seq in (short, medium, long): sched.add(seq)
        batch, prefill = sched.schedule()
        self.assertTrue(prefill)
        self.assertEqual(batch, [short])
        self.assertEqual(list(sched.waiting), [medium, long])
        self.assertEqual(list(sched.running), [short])
        self.assertEqual(medium.num_scheduled_tokens, 0)

    def test_partial_prefill_stays_in_place_then_moves_once(self):
        sched = scheduler("short_prompt", budget=128)
        long, medium = sequences([192, 160])
        for seq in (long, medium): sched.add(seq)
        first, _ = sched.schedule()
        self.assertEqual(first, [medium])
        self.assertEqual(list(sched.waiting), [long, medium])
        self.assertEqual(medium.status, SequenceStatus.WAITING)
        self.assertEqual(len(medium.block_table), 1)
        sched.postprocess(first, [7], True)
        second, _ = sched.schedule()
        self.assertEqual(second, [medium])
        self.assertEqual(list(sched.waiting), [long])
        self.assertEqual(list(sched.running), [medium])

    def test_preempted_original_prompt_and_current_deque_tie(self):
        sched = scheduler("short_prompt")
        older, newer = sequences([32, 32])
        older.append_token(7)
        sched.add(newer)
        sched.waiting.appendleft(older)  # same ordering established by preempt()
        batch, _ = sched.schedule()
        self.assertEqual(batch, [older])
        self.assertEqual(list(sched.waiting), [newer])

    def test_telemetry_does_not_change_decisions(self):
        def order(enabled):
            sched = scheduler("short_prompt")
            seqs = sequences([96, 32, 192])
            if enabled:
                capture = Telemetry(0, clock_ns=lambda: 1_000_000_000)
                for seq in seqs: capture.register(seq.seq_id, str(seq.seq_id),
                                                  seq.num_prompt_tokens, seq.max_tokens)
                sched.telemetry = capture
            for seq in seqs: sched.add(seq)
            chosen = []
            while sched.waiting:
                batch, _ = sched.schedule()
                chosen.append(seqs.index(batch[0]))
            return chosen
        self.assertEqual(order(False), [1, 0, 2])
        self.assertEqual(order(True), [1, 0, 2])

    def test_decode_running_order_is_policy_independent(self):
        def decode(policy):
            sched = scheduler(policy, batch=2)
            seqs = sequences([32, 96])
            for seq in seqs: sched.add(seq)
            batch, prefill = sched.schedule()
            self.assertTrue(prefill)
            sched.postprocess(batch, [7] * len(batch), True)
            selected, prefill = sched.schedule()
            self.assertFalse(prefill)
            return [seqs.index(s) for s in selected]
        self.assertEqual(decode("baseline"), [0, 1])
        self.assertEqual(decode("short_prompt"), [0, 1])


if __name__ == "__main__":
    unittest.main()
