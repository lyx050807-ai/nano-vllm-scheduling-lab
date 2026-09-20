"""Opt-in, coordinator-local lifecycle capture with no CUDA or disk operations.

Call LLM.enable_telemetry(t0_ns) after warmup and before admitting requests.
The caller owns the perf_counter_ns origin and later joins replay release/planned
arrival and run metadata. Snapshots are engine-telemetry-v1 fragments, not full
request-telemetry-v1 experiment records. No user-facing TTFT is inferred here.
"""
from time import perf_counter_ns


class Telemetry:
    def __init__(self, t0_ns, *, clock_ns=perf_counter_ns):
        if type(t0_ns) is not int or t0_ns < 0 or not callable(clock_ns):
            raise ValueError("supply a nonnegative monotonic t0_ns and callable clock")
        self.t0_ns = t0_ns
        self._clock_ns = clock_ns
        self._records = {}
        self._request_ids = set()

    def register(self, seq_id, request_id, num_prompt_tokens, max_new_tokens):
        if request_id is None:
            request_id = f"seq-{seq_id}"
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("request_id must be a nonempty string")
        if seq_id in self._records or request_id in self._request_ids:
            raise ValueError("duplicate telemetry request/sequence ID")
        self._records[seq_id] = dict(
            request_id=request_id, engine_seq_id=seq_id,
            num_prompt_tokens=num_prompt_tokens, max_new_tokens=max_new_tokens,
            admitted_ns=None, first_scheduled_ns=None, first_prefill_dispatch_ns=None,
            first_token_ns=None, finished_ns=None, token_times_ns=[])
        self._request_ids.add(request_id)

    def _now(self):
        return self._clock_ns() - self.t0_ns

    def _first(self, seq_id, field):
        row = self._records[seq_id]
        if row[field] is None:
            row[field] = self._now()

    def admitted(self, seq_id):
        self._first(seq_id, "admitted_ns")

    def _batch_first(self, seq_ids, field):
        timestamp = self._now()
        for seq_id in seq_ids:
            row = self._records[seq_id]
            if row[field] is None:
                row[field] = timestamp

    def scheduled(self, seq_ids):
        self._batch_first(seq_ids, "first_scheduled_ns")

    def prefill_dispatched(self, seq_ids):
        self._batch_first(seq_ids, "first_prefill_dispatch_ns")

    def token(self, seq_id):
        row = self._records[seq_id]
        timestamp = self._now()
        row["token_times_ns"].append(timestamp)
        if row["first_token_ns"] is None:
            row["first_token_ns"] = timestamp

    def finished(self, seq_id):
        self._first(seq_id, "finished_ns")

    def snapshot(self, *, completed_only=False):
        """Return detached JSON-serializable records keyed by external request ID.

        Incomplete captures retain None for future events. Completed records remain
        retrievable for the lifetime of this collector; no per-token serialization.
        The coordinator must not reset this origin or reuse IDs for preempted work.
        """
        result = {}
        for row in self._records.values():
            if completed_only and row["finished_ns"] is None:
                continue
            record = {key: row[key] for key in
                      ("request_id", "engine_seq_id", "num_prompt_tokens", "max_new_tokens")}
            record.update(schema_version="engine-telemetry-v1", t0_ns=self.t0_ns,
                          status="completed" if row["finished_ns"] is not None else "incomplete")
            for field in ("admitted", "first_scheduled", "first_prefill_dispatch", "first_token", "finished"):
                value = row[field + "_ns"]
                record[field + "_s"] = None if value is None else value / 1_000_000_000
            record["token_times_s"] = [value / 1_000_000_000 for value in row["token_times_ns"]]
            record["observed_output_tokens"] = len(row["token_times_ns"])
            for metric, end in (("queue_wait_ms", "first_scheduled_ns"), ("engine_ttft_ms", "first_token_ns")):
                a, b = row["admitted_ns"], row[end]
                record[metric] = None if a is None or b is None else (b - a) / 1_000_000
            result[row["request_id"]] = record
        return result
