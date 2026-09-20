"""CPU-only absolute-arrival replay; no engine, scheduling or token telemetry.

CLI dry run: .venv/bin/python scripts/replay_trace.py
Callback API: replay_trace(path, callback), where callback(request) is synchronous.

Timing meanings:
* arrival_s: immutable planned offset from the replay origin.
* actual_release_s: monotonic time sampled immediately before callback dispatch,
  relative to that origin (or the same release point in a callback-free dry run).
* release_error_ms: signed (actual - planned) error; positive means late.
Future engine events are not measured here:
* Admission: the engine accepts the released request into its waiting queue.
* Scheduling: the scheduler selects the request for execution.
* First-token: the first generated output token becomes observable.
* Completion: the engine marks the request finished under its stopping rules.
Release does not establish any of these times; no TTFT definition is changed here.
"""
import argparse
from decimal import Decimal
import json
from pathlib import Path
from statistics import fmean
import time

if __package__:
    from . import make_trace
else:
    import make_trace

ROOT = Path(__file__).resolve().parents[1]


def load_validated_trace(trace_path, model_dir=ROOT / "models/Qwen3-0.6B"):
    """Complete existing CPU schema/tokenizer/sidecar validation before any clock starts."""
    path = Path(trace_path)
    data = path.read_bytes()
    metadata_bytes = path.with_suffix(".meta.json").read_bytes()
    tokenizer, assets = make_trace.load_local_tokenizer(model_dir)
    records = make_trace.validate_trace_bytes(data, tokenizer)
    metadata = make_trace.strict_json(metadata_bytes.decode("utf-8"))
    make_trace.validate_metadata(metadata, data, records, assets)
    identity = {"trace_sha256": make_trace.sha256(data),
                "metadata_sha256": make_trace.sha256(metadata_bytes)}
    return records, identity


def replay_requests(records, callback=None, *, clock_ns=time.perf_counter_ns, sleep=time.sleep):
    """Release already validated requests in order, with injectable clock/wait functions.

    Use replay_trace for file input and full tokenizer/package validation. This
    low-level layer checks timing/identity before t0 and snapshots each request.
    Callbacks receive a fresh dict, cannot mutate the replay plan, and run once
    per request on normal completion. A callback exception aborts immediately;
    it is propagated, never retried. Overdue requests are dispatched in file
    order without extra waiting. Callback cost may delay subsequent releases.
    """
    make_trace.require(isinstance(records, (list, tuple)) and records, "empty replay")
    make_trace.require(callback is None or callable(callback), "callback must be callable")
    plan = []
    seen = set()
    previous = Decimal(-1)
    for row in records:
        make_trace.require(isinstance(row, dict), "request must be an object")
        request_id = row.get("request_id")
        make_trace.require(isinstance(request_id, str) and request_id and request_id not in seen,
                           "invalid/duplicate replay request ID")
        seen.add(request_id)
        arrival = row.get("arrival_s")
        make_trace.require(type(arrival) in (int, Decimal), "arrival must be a JSON decimal or integer")
        arrival = Decimal(arrival)
        make_trace.require(arrival.is_finite() and arrival >= 0 and not arrival.is_signed(),
                           "invalid replay arrival")
        make_trace.require(arrival.as_tuple().exponent >= -6 and arrival >= previous,
                           "arrival precision/order invalid")
        previous = arrival
        # The schema has microsecond precision. Integer nanosecond arithmetic
        # avoids float cancellation between a large clock epoch and small offsets.
        offset_ns = int(arrival * 1_000_000_000)
        plan.append((dict(row), request_id, offset_ns))

    timings = []
    t0 = clock_ns()
    for request, request_id, offset_ns in plan:
        target_arrival = t0 + offset_ns
        now = clock_ns()
        while now < target_arrival:
            sleep((target_arrival - now) / 1_000_000_000)
            now = clock_ns()  # Recheck after early wakeup; never release early.
        if callback is not None:
            callback(request)
        elapsed_ns = now - t0
        timings.append({"request_id": request_id, "arrival_s": offset_ns / 1_000_000_000,
                        "actual_release_s": elapsed_ns / 1_000_000_000,
                        "release_error_ms": (elapsed_ns - offset_ns) / 1_000_000})
    return timings


def replay_trace(trace_path, callback=None, *, model_dir=ROOT / "models/Qwen3-0.6B",
                 clock_ns=time.perf_counter_ns, sleep=time.sleep):
    """Validate a local trace package, then release its requests on CPU."""
    records, _ = load_validated_trace(trace_path, model_dir)
    return replay_requests(records, callback, clock_ns=clock_ns, sleep=sleep)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, default=ROOT / "workloads/dev_trace.jsonl")
    parser.add_argument("--model", type=Path, default=ROOT / "models/Qwen3-0.6B",
                        help="local tokenizer snapshot for CPU validation only")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/replay/dev_replay_timing.jsonl")
    args = parser.parse_args()
    try:
        make_trace.require(not args.output.exists() and not args.output.is_symlink(),
                           f"refusing to overwrite: {args.output}")
        requests, identity = load_validated_trace(args.trace, args.model)
        # Buffer diagnostics in memory; disk serialization happens after replay.
        # There is no engine initialization or GPU work in this task.
        timings = replay_requests(requests)
        payload = "".join(json.dumps({**row, **identity}, sort_keys=True, allow_nan=False) + "\n"
                          for row in timings)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
        errors = [abs(row["release_error_ms"]) for row in timings]
        print(json.dumps({"mode": "cpu-dry-run", "clock": "time.perf_counter_ns",
                          "request_count": len(timings), "output": str(args.output),
                          "mean_absolute_release_error_ms": fmean(errors),
                          "max_absolute_release_error_ms": max(errors), **identity}, sort_keys=True))
    except (ValueError, OSError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()
