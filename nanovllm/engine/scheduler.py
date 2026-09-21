from collections import deque
from time import perf_counter_ns

from nanovllm.config import Config
from nanovllm.engine.sequence import Sequence, SequenceStatus
from nanovllm.engine.block_manager import BlockManager
from nanovllm.engine.waiting_policy import (AGING_RATE_TOKENS_PER_SECOND,
                                           choose_waiting_index, validate_aging_rate,
                                           validate_policy)


class Scheduler:

    def __init__(self, config: Config, *, clock_ns=None):
        self.scheduling_policy = validate_policy(getattr(config, "scheduling_policy", "baseline"))
        self.aging_rate_tokens_per_second = validate_aging_rate(
            getattr(config, "aging_rate_tokens_per_second", AGING_RATE_TOKENS_PER_SECOND))
        self._clock_ns = (clock_ns or perf_counter_ns) if self.scheduling_policy == "aged_short_prompt" else None
        self.first_enqueue_ns = {} if self.scheduling_policy == "aged_short_prompt" else None
        self.max_num_seqs = config.max_num_seqs
        self.max_num_batched_tokens = config.max_num_batched_tokens
        self.eos = config.eos
        self.block_size = config.kvcache_block_size
        self.block_manager = BlockManager(config.num_kvcache_blocks, config.kvcache_block_size)
        self.waiting: deque[Sequence] = deque()
        self.running: deque[Sequence] = deque()
        self.telemetry = None

    def is_finished(self):
        return not self.waiting and not self.running

    def add(self, seq: Sequence):
        if self.first_enqueue_ns is not None and seq.seq_id not in self.first_enqueue_ns:
            self.first_enqueue_ns[seq.seq_id] = self._clock_ns()
        self.waiting.append(seq)
        if self.telemetry is not None:
            self.telemetry.admitted(seq.seq_id)

    def schedule(self) -> tuple[list[Sequence], bool]:
        scheduled_seqs = []
        num_batched_tokens = 0

        # prefill
        while self.waiting and len(scheduled_seqs) < self.max_num_seqs:
            if self.scheduling_policy == "baseline":
                index = 0
            elif self.scheduling_policy == "aged_short_prompt":
                index = choose_waiting_index(
                    self.waiting, self.scheduling_policy, now_ns=self._clock_ns(),
                    first_enqueue_ns=self.first_enqueue_ns,
                    aging_rate_tokens_per_second=self.aging_rate_tokens_per_second)
            else:
                index = choose_waiting_index(self.waiting, self.scheduling_policy)
            seq = self.waiting[index]
            remaining = self.max_num_batched_tokens - num_batched_tokens
            if remaining == 0:
                break
            if not seq.block_table:
                num_cached_blocks = self.block_manager.can_allocate(seq)
                if num_cached_blocks == -1:
                    break
                num_tokens = seq.num_tokens - num_cached_blocks * self.block_size
            else:
                num_tokens = seq.num_tokens - seq.num_cached_tokens
            if remaining < num_tokens and scheduled_seqs:  # only allow chunked prefill for the first seq
                break
            if not seq.block_table:
                self.block_manager.allocate(seq, num_cached_blocks)
            seq.num_scheduled_tokens = min(num_tokens, remaining)
            num_batched_tokens += seq.num_scheduled_tokens
            if seq.num_cached_tokens + seq.num_scheduled_tokens == seq.num_tokens:
                seq.status = SequenceStatus.RUNNING
                if index == 0:
                    self.waiting.popleft()
                else:
                    del self.waiting[index]
                self.running.append(seq)
            scheduled_seqs.append(seq)

        if scheduled_seqs:
            return scheduled_seqs, True

        # decode
        while self.running and len(scheduled_seqs) < self.max_num_seqs:
            seq = self.running.popleft()
            while not self.block_manager.can_append(seq):
                if self.running:
                    self.preempt(self.running.pop())
                else:
                    self.preempt(seq)
                    break
            else:
                seq.num_scheduled_tokens = 1
                seq.is_prefill = False
                self.block_manager.may_append(seq)
                scheduled_seqs.append(seq)
        assert scheduled_seqs
        self.running.extendleft(reversed(scheduled_seqs))
        return scheduled_seqs, False

    def preempt(self, seq: Sequence):
        seq.status = SequenceStatus.WAITING
        seq.is_prefill = True
        self.block_manager.deallocate(seq)
        self.waiting.appendleft(seq)

    def postprocess(self, seqs: list[Sequence], token_ids: list[int], is_prefill: bool):
        for seq, token_id in zip(seqs, token_ids):
            self.block_manager.hash_blocks(seq)
            seq.num_cached_tokens += seq.num_scheduled_tokens
            seq.num_scheduled_tokens = 0
            if is_prefill and seq.num_cached_tokens < seq.num_tokens:
                continue
            seq.append_token(token_id)
            if self.telemetry is not None:
                self.telemetry.token(seq.seq_id)
            if (not seq.ignore_eos and token_id == self.eos) or seq.num_completion_tokens == seq.max_tokens:
                seq.status = SequenceStatus.FINISHED
                self.block_manager.deallocate(seq)
                self.running.remove(seq)
                if self.first_enqueue_ns is not None:
                    del self.first_enqueue_ns[seq.seq_id]
                if self.telemetry is not None:
                    self.telemetry.finished(seq.seq_id)
