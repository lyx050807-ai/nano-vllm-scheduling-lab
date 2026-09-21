#!/usr/bin/env python3
"""Freeze, list, resume, and execute the formal-mixed-v1 benchmark matrix."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PROFILE_ID = "formal-mixed-v1"
POLICIES = ("baseline", "short_prompt", "aged_short_prompt")
TRACE_SEEDS = (101, 202, 303)
REPETITIONS = 5
AGING_RATE = 320
COOLDOWN_SECONDS = 30
PROCESS_WATCHDOG_SECONDS = 150
ENGINE_CONFIGURATION = {
    "enforce_eager": True, "tensor_parallel_size": 1,
    "max_model_len": 256, "max_num_batched_tokens": 256,
    "max_num_seqs": 1, "gpu_memory_utilization": 0.6,
}
GENERATION_CONFIGURATION = {
    "temperature": 0.6, "ignore_eos": False,
    "max_new_tokens": 16, "inference_seed": 42,
}
TRACE_HASHES = {
    101: "ff3acfd57a153030e76d06af491fed20bd1498db7e12580db345c8bb1ff92ac8",
    202: "e3c82a96d5b7295b7e98d4d4884476ddd9cc5ee1701831f4d5e63e8872e94078",
    303: "8721930601de3f96d23287cef9038a0967f653133987a154ca18ae8e5b4d6866",
}
SIDECAR_HASHES = {
    101: "fb298e8ba8019d86e54c62487eb5906e0a59d9889ca5ca73881560f53e0b1476",
    202: "8603718474005a5dc3f18fac2b76cd4e37d23252dd19ea124c5f34734d95ebfc",
    303: "af6d5affaf40cbd7e72a0961d37d10dcdbe59664ce8a563e954ec844862d4526",
}
TERMINAL_STATUSES = {"success", "timeout", "oom", "runner_failure",
                     "lifecycle_failure"}


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def strict_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ValueError(f"non-finite JSON value {value}")))


def trace_identity(root, seed):
    trace = root / f"workloads/formal_trace_seed{seed}.jsonl"
    sidecar = trace.with_suffix(".meta.json")
    meta = strict_json(sidecar)
    actual = file_hash(trace)
    expected = TRACE_HASHES[seed]
    if meta.get("profile_id") != PROFILE_ID or meta.get("seed") != seed:
        raise ValueError(f"formal trace identity mismatch for seed {seed}")
    if meta.get("trace_sha256") != expected or actual != expected:
        raise ValueError(f"formal trace SHA256 mismatch for seed {seed}")
    if file_hash(sidecar) != SIDECAR_HASHES[seed]:
        raise ValueError(f"formal sidecar SHA256 mismatch for seed {seed}")
    return trace, sidecar, meta


def build_plan(root=ROOT):
    root = Path(root)
    project_commit = git_output(root, "rev-parse", "HEAD")
    upstream_commit = (root / "artifacts/environment/upstream-commit.txt").read_text().strip()
    plan = []
    order_index = 0
    for repeat_index in range(REPETITIONS):
        for seed_index, seed in enumerate(TRACE_SEEDS):
            rotation = (repeat_index + seed_index) % len(POLICIES)
            policy_order = POLICIES[rotation:] + POLICIES[:rotation]
            trace, sidecar, meta = trace_identity(root, seed)
            for block_position, policy in enumerate(policy_order):
                run_id = f"{PROFILE_ID}-seed{seed}-rep{repeat_index}-{policy}"
                plan.append({
                    "run_order_index": order_index,
                    "block_index": repeat_index * len(TRACE_SEEDS) + seed_index,
                    "block_position": block_position,
                    "policy": policy,
                    "trace_seed": seed,
                    "repeat_index": repeat_index,
                    "paired_key": f"seed{seed}-rep{repeat_index}",
                    "run_id": run_id,
                    "trace_path": str(trace.relative_to(root)),
                    "trace_metadata_path": str(sidecar.relative_to(root)),
                    "trace_sha256": TRACE_HASHES[seed],
                    "trace_metadata_sha256": SIDECAR_HASHES[seed],
                    "project_git_commit": project_commit,
                    "upstream_commit": upstream_commit,
                    "model_revision": meta["model"]["revision"],
                    "engine_configuration": ENGINE_CONFIGURATION,
                    "generation_configuration": GENERATION_CONFIGURATION,
                    "aging_rate_tokens_per_second": (AGING_RATE
                        if policy == "aged_short_prompt" else None),
                    "completion_count": None,
                    "artifact_directory": f"runs/{run_id}",
                    "status": "pending",
                    "attempts": [],
                })
                order_index += 1
    return plan


def git_output(root, *args):
    return subprocess.check_output(["git", *args], cwd=root).decode().strip()


def manifest_value(root=ROOT):
    root = Path(root)
    _, _, meta = trace_identity(root, TRACE_SEEDS[0])
    return {
        "schema": "formal-benchmark-plan-v1",
        "profile_id": PROFILE_ID,
        "project_git_commit": git_output(root, "rev-parse", "HEAD"),
        "upstream_commit": (root / "artifacts/environment/upstream-commit.txt").read_text().strip(),
        "model_revision": meta["model"]["revision"],
        "engine_configuration": ENGINE_CONFIGURATION,
        "generation_configuration": GENERATION_CONFIGURATION,
        "aging_rate_tokens_per_second": AGING_RATE,
        "coordinator_timeout_seconds": 90,
        "process_watchdog_seconds": PROCESS_WATCHDOG_SECONDS,
        "cooldown_seconds": COOLDOWN_SECONDS,
        "order_rule": "repetition-major, seed 101/202/303; rotate policies by (repeat+seed_index) mod 3",
        "runs": build_plan(root),
    }


def write_manifest(path, value, *, replace=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if not replace:
        with path.open("x", encoding="utf-8") as output:
            output.write(data)
        return
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("x", encoding="utf-8") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def validate_manifest(value, root=ROOT):
    expected = manifest_value(root)
    immutable = ("schema", "profile_id", "upstream_commit",
                 "model_revision", "engine_configuration", "generation_configuration",
                 "aging_rate_tokens_per_second", "coordinator_timeout_seconds",
                 "process_watchdog_seconds", "cooldown_seconds", "order_rule")
    for key in immutable:
        if value.get(key) != expected[key]:
            raise ValueError(f"manifest {key} differs from frozen plan")
    expected_runs = expected["runs"]
    if len(value.get("runs", [])) != 45:
        raise ValueError("manifest must contain exactly 45 runs")
    identity_keys = ("run_order_index", "block_index", "block_position", "policy",
                     "trace_seed", "repeat_index", "paired_key", "run_id", "trace_path",
                     "trace_metadata_path", "trace_sha256", "trace_metadata_sha256",
                     "upstream_commit", "model_revision", "engine_configuration",
                     "generation_configuration", "aging_rate_tokens_per_second",
                     "artifact_directory")
    for actual, planned in zip(value["runs"], expected_runs):
        if any(actual.get(key) != planned[key] for key in identity_keys):
            raise ValueError(f"run identity differs from frozen plan at {planned['run_id']}")
        if actual.get("project_git_commit") != value.get("project_git_commit"):
            raise ValueError("run project Git commit differs from frozen manifest")
        if actual.get("status") not in {"pending", "running", *TERMINAL_STATUSES}:
            raise ValueError(f"invalid run status {actual.get('status')!r}")
    return value


def create_manifest(output_root, project_root=ROOT):
    output_root = Path(output_root)
    value = manifest_value(project_root)
    write_manifest(output_root / "manifest.json", value)
    return value


def load_manifest(path, project_root=ROOT):
    return validate_manifest(strict_json(path), project_root)


def reconcile_interrupted(manifest_path, project_root=ROOT):
    manifest_path = Path(manifest_path)
    manifest = load_manifest(manifest_path, project_root)
    changed = False
    for run in manifest["runs"]:
        if run["status"] == "running":
            run["status"] = "runner_failure"
            run["attempts"].append({
                "attempt": len(run["attempts"]) + 1,
                "status": "runner_failure",
                "reason": "orchestrator_interrupted",
                "artifact_directory": str(manifest_path.parent / run["artifact_directory"]),
                "completion_count": None,
            })
            changed = True
    if changed:
        write_manifest(manifest_path, manifest, replace=True)
    return manifest


def pending_runs(manifest):
    return [row for row in manifest["runs"] if row["status"] == "pending"]


def wait_cooldown(previous_exit_utc, *, clock=None, sleep=time.sleep):
    if previous_exit_utc is None:
        return None
    clock = clock or (lambda: datetime.now(timezone.utc))
    previous = datetime.fromisoformat(previous_exit_utc)
    elapsed = (clock() - previous).total_seconds()
    if elapsed < COOLDOWN_SECONDS:
        sleep(COOLDOWN_SECONDS - elapsed)
    return (clock() - previous).total_seconds()


def create_run_directory(output_root, run):
    path = Path(output_root) / run["artifact_directory"]
    path.mkdir(parents=True, exist_ok=False)
    return path


def create_retry_directory(run_directory, reason, retry_of):
    run_directory = Path(run_directory)
    index = 1
    while (run_directory / f"attempt-{index:03d}").exists():
        index += 1
    path = run_directory / f"attempt-{index:03d}"
    path.mkdir(parents=False, exist_ok=False)
    record = {"reason": reason, "retry_of": retry_of,
              "created_at_utc": datetime.now(timezone.utc).isoformat()}
    (path / "retry.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    return path


def classify_result(exit_code, capture_outcome, lifecycle, log_text):
    if "out of memory" in log_text.lower() or "cuda error: out of memory" in log_text.lower():
        return "oom"
    if capture_outcome == "timed_out":
        return "timeout"
    if lifecycle == "failed":
        return "lifecycle_failure"
    if exit_code == 0 and capture_outcome == "completed":
        return "success"
    return "runner_failure"


def validate_success(run, meta, rows):
    if (meta.get("policy") != run["policy"] or
            meta.get("trace_sha256") != run["trace_sha256"] or
            meta.get("metadata_sha256") != run["trace_metadata_sha256"] or
            meta.get("request_count") != 60 or meta.get("completion_count") != 60 or
            meta.get("aging_rate_tokens_per_second") != AGING_RATE or
            meta.get("engine_config", {}).get("scheduling_policy") != run["policy"]):
        raise ValueError("successful run metadata differs from frozen identity")
    expected_ids = {f"formal-{run['trace_seed']}-{i:06d}" for i in range(1, 61)}
    if (len(rows) != 60 or {row.get("request_id") for row in rows} != expected_ids or
            any(row.get("policy") != run["policy"] or
                row.get("trace_sha256") != run["trace_sha256"] or
                row.get("status") != "completed" for row in rows)):
        raise ValueError("successful run records are incomplete or mismatched")
    return True


def execute_run(run, output_root, project_root=ROOT, previous_exit_utc=None):
    directory = create_run_directory(output_root, run)
    output = directory / "requests.jsonl"
    progress = directory / "progress.jsonl"
    log_path = directory / "runner.log"
    command = [str(Path(project_root) / ".venv/bin/python"), "scripts/run_replay.py",
               "--mode", "formal-measurement", "--trace", run["trace_path"],
               "--policy", run["policy"], "--run-id", run["run_id"],
               "--output", str(output), "--progress", str(progress),
               "--timeout-s", "90"]
    started = datetime.now(timezone.utc).isoformat()
    actual_gap = ((datetime.fromisoformat(started) -
                   datetime.fromisoformat(previous_exit_utc)).total_seconds()
                  if previous_exit_utc is not None else None)
    process_timed_out = False
    with log_path.open("x", encoding="utf-8") as log:
        process = subprocess.Popen(command, cwd=project_root, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            exit_code = process.wait(timeout=PROCESS_WATCHDOG_SECONDS)
        except subprocess.TimeoutExpired:
            process_timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                exit_code = process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                exit_code = process.wait()
    process_exited_at = datetime.now(timezone.utc).isoformat()
    meta_path = output.with_suffix(".meta.json")
    meta = strict_json(meta_path) if meta_path.exists() else {}
    capture = "timed_out" if process_timed_out else meta.get("capture_outcome", "failed")
    lifecycle = meta.get("lifecycle_invariants", "partial")
    status = classify_result(exit_code, capture, lifecycle, log_path.read_text(errors="replace"))
    audit_error = None
    if status == "success":
        try:
            records = [json.loads(line) for line in output.read_text().splitlines()]
            validate_success(run, meta, records)
        except (OSError, ValueError, KeyError) as error:
            status = "lifecycle_failure"
            audit_error = f"{type(error).__name__}: {error}"
    return {"attempt": 1, "status": status, "started_at_utc": started,
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "exit_code": exit_code, "process_watchdog_timeout": process_timed_out,
            "process_exited_at_utc": process_exited_at,
            "gap_from_previous_process_exit_s": actual_gap,
            "capture_outcome": capture, "lifecycle_invariants": lifecycle,
            "completion_count": meta.get("completion_count"),
            "executed_project_git_commit": meta.get("project_commit"),
            "audit_error": audit_error,
            "artifact_directory": str(directory)}


def execute_pending(manifest_path, project_root=ROOT):
    manifest_path = Path(manifest_path)
    output_root = manifest_path.parent
    before = load_manifest(manifest_path, project_root)
    interrupted = any(run["status"] == "running" for run in before["runs"])
    manifest = reconcile_interrupted(manifest_path, project_root)
    if interrupted:
        raise RuntimeError("interrupted run recorded; inspect child processes and partial artifacts before resume")
    pending = pending_runs(manifest)
    previous_exit = None
    if pending:
        for earlier in manifest["runs"][:pending[0]["run_order_index"]]:
            if earlier["attempts"] and earlier["attempts"][-1].get("process_exited_at_utc"):
                previous_exit = earlier["attempts"][-1]["process_exited_at_utc"]
    for run in pending:
        wait_cooldown(previous_exit)
        run["status"] = "running"
        write_manifest(manifest_path, manifest, replace=True)
        try:
            result = execute_run(run, output_root, project_root, previous_exit)
        except Exception as error:
            result = {"attempt": 1, "status": "runner_failure",
                      "reason": f"{type(error).__name__}: {error}",
                      "completion_count": None,
                      "artifact_directory": str(output_root / run["artifact_directory"])}
        run["attempts"].append(result)
        run["status"] = result["status"]
        run["completion_count"] = result["completion_count"]
        write_manifest(manifest_path, manifest, replace=True)
        previous_exit = result.get("process_exited_at_utc")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path,
                        default=ROOT / "artifacts/formal-benchmark")
    parser.add_argument("--dry-run", "--list", action="store_true")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    args.output_root = args.output_root.resolve()
    if args.execute and args.dry_run:
        parser.error("choose either --execute or --dry-run")
    manifest_path = args.output_root / "manifest.json"
    manifest = (load_manifest(manifest_path, ROOT) if manifest_path.exists()
                else create_manifest(args.output_root, ROOT))
    if args.execute:
        execute_pending(manifest_path, ROOT)
        return
    plan = {"manifest": str(manifest_path), "total_runs": len(manifest["runs"]),
            "pending_runs": len(pending_runs(manifest)), "runs": manifest["runs"]}
    print(json.dumps(plan, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
