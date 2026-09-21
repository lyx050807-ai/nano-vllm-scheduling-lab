#!/usr/bin/env python3
"""Read formal artifacts and retain per-run values for paired comparisons."""
import argparse
import json
import math
from pathlib import Path
import statistics

CLASSES = ("overall", "short", "medium", "long")
METRICS = ("ttft_ms", "queue_wait_ms", "e2e_latency_ms",
           "engine_ttft_ms", "admission_overhead_ms")


def distribution(values):
    values = sorted(values)
    if not values:
        return {"count": 0, "values": [], "mean": None, "median": None,
                "p95": None, "max": None}
    return {"count": len(values), "values": values,
            "mean": statistics.fmean(values), "median": statistics.median(values),
            "p95": values[math.ceil(.95 * len(values)) - 1], "max": values[-1]}


def cohort(rows, prompt_class):
    completed = [r for r in rows if r.get("status") == "completed"]
    return completed if prompt_class == "overall" else [
        r for r in completed if r.get("prompt_class") == prompt_class]


def summarize_run(rows, *, policy, trace_seed, repeat_index, run_id):
    metrics = {}
    itl = {}
    for prompt_class in CLASSES:
        selected = cohort(rows, prompt_class)
        metrics[prompt_class] = {
            name: distribution([r[name] for r in selected if r.get(name) is not None])
            for name in METRICS
        }
        request_means = []
        pooled = []
        for row in selected:
            times = row.get("token_times_s") or []
            pairs = [1000 * (b - a) for a, b in zip(times, times[1:])]
            if pairs:
                request_means.append(statistics.fmean(pairs))
                pooled.extend(pairs)
        itl[prompt_class] = {
            "per_request_mean_values": request_means,
            "median_per_request_mean_ms": (statistics.median(request_means)
                                               if request_means else None),
            "pooled_pair_count": len(pooled),
            "pooled_pair_mean_ms": statistics.fmean(pooled) if pooled else None,
        }
    completed = cohort(rows, "overall")
    releases = [r["release_s"] for r in completed if r.get("release_s") is not None]
    finishes = [r["finished_s"] for r in completed if r.get("finished_s") is not None]
    duration = max(finishes) - min(releases) if releases and finishes else None
    return {"run_id": run_id, "policy": policy, "trace_seed": trace_seed,
            "repeat_index": repeat_index, "paired_key": f"seed{trace_seed}-rep{repeat_index}",
            "request_count": len(rows), "completion_count": len(completed),
            "completion_rate": len(completed) / len(rows) if rows else None,
            "throughput_requests_per_second": (len(completed) / duration
                if len(completed) == len(rows) and duration and duration > 0 else None),
            "metrics": metrics, "itl_ms": itl}


def aggregate(manifest_path):
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    output_root = manifest_path.parent
    summaries = []
    outcomes = []
    for run in manifest["runs"]:
        completed = run.get("completion_count")
        outcomes.append({"run_id": run["run_id"], "policy": run["policy"],
                         "trace_seed": run["trace_seed"],
                         "repeat_index": run["repeat_index"],
                         "paired_key": run["paired_key"], "status": run["status"],
                         "completion_count": completed,
                         "completion_rate": completed / 60 if completed is not None else None})
        if run["status"] != "success":
            continue
        path = output_root / run["artifact_directory"] / "requests.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        summaries.append(summarize_run(rows, policy=run["policy"],
            trace_seed=run["trace_seed"], repeat_index=run["repeat_index"],
            run_id=run["run_id"]))
    paired = {}
    for summary in summaries:
        paired.setdefault(summary["paired_key"], {})[summary["policy"]] = summary["run_id"]
    return {"schema": "formal-benchmark-summary-v1", "runs": summaries,
            "outcomes": outcomes, "paired_runs": paired}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = aggregate(args.manifest)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(value, output, indent=2, sort_keys=True, allow_nan=False)
        output.write("\n")


if __name__ == "__main__":
    main()
