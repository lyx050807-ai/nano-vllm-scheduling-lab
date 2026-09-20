"""Baseline-only capacity gate for the three frozen formal trace packages."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
from statistics import fmean, median
import subprocess
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
SEEDS = (101, 202, 303)
OUTPUT = ROOT / "artifacts/calibration/formal-mixed-v1"


def summarize(rows):
    waits = [r["queue_wait_ms"] for r in rows if r["queue_wait_ms"] is not None]
    def group(name):
        values = [r["queue_wait_ms"] for r in rows if r["prompt_class"] == name
                  and r["queue_wait_ms"] is not None]
        return dict(count=len(values), mean_ms=fmean(values) if values else None,
                    median_ms=median(values) if values else None,
                    max_ms=max(values) if values else None)
    return dict(positive_count=sum(value > 0 for value in waits),
                at_least_20_ms=sum(value >= 20 for value in waits),
                at_least_100_ms=sum(value >= 100 for value in waits),
                mean_ms=fmean(waits) if waits else None,
                median_ms=median(waits) if waits else None,
                max_ms=max(waits) if waits else None,
                by_prompt_class={name:group(name) for name in ("short", "medium", "long")})


def run_seed(seed):
    trace = ROOT / f"workloads/formal_trace_seed{seed}.jsonl"
    expected_hash = hashlib.sha256(trace.read_bytes()).hexdigest()
    run_id = "capacity-baseline-seed" + str(seed) + "-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    directory = OUTPUT / run_id
    directory.mkdir(parents=True, exist_ok=False)
    output = directory / "requests.jsonl"
    command = [sys.executable, str(ROOT / "scripts/run_replay.py"),
               "--trace", str(trace), "--output", str(output),
               "--run-id", run_id, "--mode", "capacity-calibration-only",
               "--timeout-s", "90", "--progress", str(directory / "progress.jsonl")]
    started = monotonic()
    with (directory / "runner.log").open("x") as log:
        log.write("Command: " + " ".join(command) + "\n")
        log.flush()
        process = subprocess.Popen(command, cwd=ROOT, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        hard_timeout = False
        try:
            code = process.wait(timeout=150)
        except subprocess.TimeoutExpired:
            hard_timeout = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            code = process.returncode
        log.write(f"\nExit code: {code}; hard_timeout: {hard_timeout}\n")
    wall_s = monotonic() - started
    rows = [json.loads(line) for line in output.read_text().splitlines()] if output.exists() else []
    meta_path = output.with_suffix(".meta.json")
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    diagnostics = summarize(rows)
    ids = [r["request_id"] for r in rows]
    passed = (code == 0 and not hard_timeout and len(rows) == 60 and
              len(set(ids)) == 60 and all(r["status"] == "completed" for r in rows) and
              meta.get("completion_count") == 60 and meta.get("capture_outcome") == "completed" and
              meta.get("lifecycle_invariants") == "passed" and
              meta.get("trace_sha256") == expected_hash and
              meta.get("mode") == "capacity-calibration-only" and
              meta.get("observation_end_s", float("inf")) < 90 and
              diagnostics["at_least_20_ms"] >= 15 and diagnostics["at_least_100_ms"] >= 1)
    return dict(seed=seed, run_id=run_id, directory=str(directory),
                trace_sha256=expected_hash, request_count=60, completion_count=len(rows),
                runner_exit_code=code, hard_timeout=hard_timeout, process_wall_s=wall_s,
                observation_end_s=meta.get("observation_end_s"),
                gpu_memory_bytes=meta.get("gpu_memory_bytes"),
                queue_wait=diagnostics, gate_passed=passed)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    results = []
    for seed in SEEDS:
        result = run_seed(seed)
        results.append(result)
        print(json.dumps(result, sort_keys=True), flush=True)
        if not result["gate_passed"]:
            break  # Frozen gate failed: preserve evidence, do not tune load.
    summary = dict(mode="capacity/calibration only; not formal benchmark measurements",
                   profile_id="formal-mixed-v1", generated_at_utc=datetime.now(timezone.utc).isoformat(),
                   all_seeds_passed=len(results) == 3 and all(r["gate_passed"] for r in results),
                   results=results)
    summary_path = OUTPUT / "capacity-summary.json"
    with summary_path.open("x") as output:
        json.dump(summary, output, indent=2, sort_keys=True, allow_nan=False)
        output.write("\n")
    if not summary["all_seeds_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
