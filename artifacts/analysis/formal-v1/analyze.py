#!/usr/bin/env python3
"""Reproduce ANALYSIS-001 from immutable formal-mixed-v1 artifacts (stdlib only)."""

from __future__ import annotations

import collections
import csv
import datetime as dt
import hashlib
import html
import json
import math
from pathlib import Path
import random
import statistics as stats


ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "artifacts/formal-benchmark"
OUT = Path(__file__).resolve().parent
POLICIES = ("baseline", "short_prompt", "aged_short_prompt")
CLASSES = ("overall", "short", "medium", "long")
METRICS = ("ttft_ms", "queue_wait_ms", "e2e_latency_ms")
COMPARISONS = (("short_prompt", "baseline"),
               ("aged_short_prompt", "baseline"),
               ("aged_short_prompt", "short_prompt"))
COLORS = {"baseline": "#305b9a", "short_prompt": "#c45a37",
          "aged_short_prompt": "#238469"}
ANOMALY_KEY = "seed303-rep4"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def q(values, probability):
    values = sorted(values)
    if not values:
        return None
    pos = (len(values) - 1) * probability
    lo, hi = math.floor(pos), math.ceil(pos)
    return values[lo] * (hi - pos) + values[hi] * (pos - lo) if lo != hi else values[lo]


def nearest_rank(values, probability):
    values = sorted(values)
    return values[math.ceil(probability * len(values)) - 1] if values else None


def describe(values, *, tail=False):
    values = list(values)
    if not values:
        return {"n": 0}
    out = {"n": len(values), "mean": stats.fmean(values),
           "median": stats.median(values),
           "sd": stats.stdev(values) if len(values) > 1 else None,
           "min": min(values), "max": max(values)}
    if tail:
        out.update(p90_nearest_rank=nearest_rank(values, .9),
                   p95_nearest_rank=nearest_rank(values, .95))
    return out


def bootstrap_mean_ci(values, seed):
    """Descriptive percentile bootstrap over paired blocks; no p-value."""
    rng = random.Random(seed)
    values = tuple(values)
    n = len(values)
    samples = [stats.fmean(values[rng.randrange(n)] for _ in range(n))
               for _ in range(10000)]
    return [q(samples, .025), q(samples, .975)]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True,
                               allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path, rows, columns):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def load_and_validate():
    manifest = read_json(RAW / "manifest.json")
    aggregate = read_json(RAW / "summary.json")
    aggregate_by_id = {entry["run_id"]: entry for entry in aggregate["runs"]}
    runs = manifest["runs"]
    assert len(runs) == 45
    assert len(aggregate_by_id) == 45 and len(aggregate["paired_runs"]) == 15
    assert [r["run_order_index"] for r in runs] == list(range(45))
    assert len({r["run_id"] for r in runs}) == 45
    assert len({r["artifact_directory"] for r in runs}) == 45
    assert {r["status"] for r in runs} == {"success"}
    assert len(list((RAW / "runs").iterdir())) == 45
    inputs = {"artifacts/formal-benchmark/manifest.json": sha(RAW / "manifest.json"),
              "artifacts/formal-benchmark/summary.json": sha(RAW / "summary.json")}
    data = {}
    for run in runs:
        key = (run["trace_seed"], run["repeat_index"])
        directory = RAW / run["artifact_directory"]
        paths = {name: directory / name for name in
                 ("requests.meta.json", "requests.jsonl", "progress.jsonl", "runner.log")}
        assert all(path.is_file() for path in paths.values())
        for path in paths.values():
            inputs[str(path.relative_to(ROOT)).replace("\\", "/")] = sha(path)
        meta = read_json(paths["requests.meta.json"])
        rows = [json.loads(line) for line in paths["requests.jsonl"].read_text(
            encoding="utf-8").splitlines()]
        trace_path = ROOT / run["trace_path"]
        sidecar_path = ROOT / run["trace_metadata_path"]
        trace = [json.loads(line) for line in trace_path.read_text(
            encoding="utf-8").splitlines()]
        for path in (trace_path, sidecar_path):
            inputs[str(path.relative_to(ROOT)).replace("\\", "/")] = sha(path)
        assert sha(trace_path) == run["trace_sha256"] == meta["trace_sha256"]
        assert sha(sidecar_path) == run["trace_metadata_sha256"] == meta["metadata_sha256"]
        assert len(rows) == meta["request_count"] == meta["completion_count"] == 60
        assert run["completion_count"] == 60 and len(run["attempts"]) == 1
        assert run["attempts"][0]["status"] == "success"
        assert meta["run_id"] == run["run_id"] and meta["policy"] == run["policy"]
        assert meta["mode"] == "formal-measurement" and meta["lifecycle_invariants"] == "passed"
        assert meta["capture_outcome"] == "completed" and meta["incomplete_request_ids"] == []
        assert meta["warmup"]["requests"] == 1 and not meta["warmup"]["telemetry_enabled"]
        assert meta["engine_config"]["scheduling_policy"] == run["policy"]
        assert meta["aging_rate_tokens_per_second"] == 320
        assert run["aging_rate_tokens_per_second"] == (320 if run["policy"] == "aged_short_prompt" else None)
        ids = [row["request_id"] for row in rows]
        assert len(set(ids)) == 60 == len({row["request_id"] for row in trace})
        assert set(ids) == {row["request_id"] for row in trace}
        assert collections.Counter(row["prompt_class"] for row in rows) == {
            "short": 20, "medium": 20, "long": 20}
        assert all(row["status"] == "completed" and row["policy"] == run["policy"]
                   and row["run_id"] == run["run_id"] for row in rows)
        assert all(row["trace_sha256"] == run["trace_sha256"] and
                   row["metadata_sha256"] == run["trace_metadata_sha256"] for row in rows)
        for row in rows:
            assert abs(row["ttft_ms"] - 1000 * (row["first_token_s"] - row["release_s"])) < .001
            assert abs(row["queue_wait_ms"] - 1000 * (row["first_scheduled_s"] - row["admitted_s"])) < .001
            assert abs(row["e2e_latency_ms"] - 1000 * (row["finished_s"] - row["release_s"])) < .001
        prior = aggregate_by_id[run["run_id"]]
        assert prior["policy"] == run["policy"] and prior["completion_count"] == 60
        for prompt_class in CLASSES:
            selected = rows if prompt_class == "overall" else [
                row for row in rows if row["prompt_class"] == prompt_class]
            for metric in METRICS:
                assert math.isclose(stats.fmean(row[metric] for row in selected),
                                    prior["metrics"][prompt_class][metric]["mean"],
                                    abs_tol=1e-9)
                assert math.isclose(stats.median(row[metric] for row in selected),
                                    prior["metrics"][prompt_class][metric]["median"],
                                    abs_tol=1e-9)
        if key not in data:
            data[key] = {}
        assert run["policy"] not in data[key]
        data[key][run["policy"]] = {"run": run, "meta": meta, "rows": rows,
                                    "paths": paths, "trace": trace}
    assert len(data) == 15 and all(set(block) == set(POLICIES) for block in data.values())
    for block in data.values():
        assert len({item["run"]["trace_sha256"] for item in block.values()}) == 1
        assert len({item["run"]["trace_metadata_sha256"] for item in block.values()}) == 1
        assert len({frozenset(row["request_id"] for row in item["rows"])
                    for item in block.values()}) == 1
    return manifest, data, inputs


def selected_rows(item, prompt_class):
    return item["rows"] if prompt_class == "overall" else [
        row for row in item["rows"] if row["prompt_class"] == prompt_class]


def run_stat(item, prompt_class, metric, statistic="mean"):
    values = [row[metric] for row in selected_rows(item, prompt_class)]
    if statistic == "mean":
        return stats.fmean(values)
    if statistic == "median":
        return stats.median(values)
    if statistic == "p90":
        return nearest_rank(values, .9)
    if statistic == "p95":
        return nearest_rank(values, .95)
    if statistic == "max":
        return max(values)
    raise ValueError(statistic)


def make_class_summaries(data):
    summary = {}
    rows = []
    for policy in POLICIES:
        summary[policy] = {}
        items = [block[policy] for block in data.values()]
        for prompt_class in CLASSES:
            summary[policy][prompt_class] = {}
            for metric in METRICS:
                pooled = [row[metric] for item in items
                          for row in selected_rows(item, prompt_class)]
                run_means = [run_stat(item, prompt_class, metric) for item in items]
                run_medians = [run_stat(item, prompt_class, metric, "median") for item in items]
                entry = {"pooled_requests": describe(pooled, tail=True),
                         "run_means": describe(run_means),
                         "run_medians": describe(run_medians)}
                summary[policy][prompt_class][metric] = entry
                row = {"policy": policy, "prompt_class": prompt_class,
                       "metric": metric}
                for prefix, value in (("pooled", entry["pooled_requests"]),
                                      ("run_mean", entry["run_means"]),
                                      ("run_median", entry["run_medians"])):
                    row.update({f"{prefix}_{k}": v for k, v in value.items()})
                rows.append(row)
    columns = ("policy", "prompt_class", "metric") + tuple(
        f"{prefix}_{field}" for prefix in ("pooled", "run_mean", "run_median")
        for field in ("n", "mean", "median", "sd", "min", "max",
                      "p90_nearest_rank", "p95_nearest_rank"))
    write_csv(OUT / "class-summary.csv", rows, columns)
    return summary


def make_pairs(data, exclude=None):
    rows = []
    for (seed, repetition), block in sorted(data.items()):
        key = f"seed{seed}-rep{repetition}"
        if key == exclude:
            continue
        for candidate, reference in COMPARISONS:
            for prompt_class in CLASSES:
                for metric in METRICS:
                    statistics_to_report = ("mean", "median", "p90", "p95", "max") if prompt_class == "long" else ("mean", "median")
                    for statistic in statistics_to_report:
                        a = run_stat(block[candidate], prompt_class, metric, statistic)
                        b = run_stat(block[reference], prompt_class, metric, statistic)
                        rows.append({"trace_seed": seed, "repeat_index": repetition,
                                     "paired_key": key, "candidate": candidate,
                                     "reference": reference, "prompt_class": prompt_class,
                                     "metric": metric, "run_statistic": statistic,
                                     "candidate_ms": a, "reference_ms": b,
                                     "delta_ms": a - b,
                                     "delta_percent": 100 * (a - b) / b if b else None})
    return rows


def summarize_pairs(rows):
    grouped = collections.defaultdict(list)
    for row in rows:
        grouped[(row["candidate"], row["reference"], row["prompt_class"],
                 row["metric"], row["run_statistic"])].append(row)
    output = {}
    for key, group in sorted(grouped.items()):
        candidate, reference, prompt_class, metric, statistic = key
        deltas = [r["delta_ms"] for r in group]
        percentages = [r["delta_percent"] for r in group]
        name = "/".join(key)
        output[name] = {
            "candidate": candidate, "reference": reference,
            "prompt_class": prompt_class, "metric": metric,
            "run_statistic": statistic,
            "delta_ms": describe(deltas),
            "delta_percent": describe(percentages),
            "mean_delta_ms_bootstrap_95_percentile_ci": bootstrap_mean_ci(
                deltas, int(hashlib.sha256(name.encode()).hexdigest()[:12], 16)),
            "direction_count": {"lower": sum(x < 0 for x in deltas),
                                "equal": sum(x == 0 for x in deltas),
                                "higher": sum(x > 0 for x in deltas)},
            "by_seed": {str(seed): describe(r["delta_ms"] for r in group
                                           if r["trace_seed"] == seed)
                        for seed in (101, 202, 303)},
            "paired_keys": [r["paired_key"] for r in group],
        }
    return output


def throughput(item):
    rows = item["rows"]
    return len(rows) / (max(r["finished_s"] for r in rows) -
                        min(r["release_s"] for r in rows))


def throughput_analysis(data):
    by_policy = {policy: describe(throughput(block[policy]) for block in data.values())
                 for policy in POLICIES}
    paired = {}
    for candidate, reference in COMPARISONS:
        values = [throughput(block[candidate]) - throughput(block[reference])
                  for block in data.values()]
        percentages = [100 * (throughput(block[candidate]) /
                              throughput(block[reference]) - 1)
                       for block in data.values()]
        paired[f"{candidate}-{reference}"] = {
            "delta_requests_per_second": describe(values),
            "delta_percent": describe(percentages),
            "direction_count": {"lower": sum(v < 0 for v in values),
                                "higher": sum(v > 0 for v in values)}}
    return {"denominator": "last_finished_s - first_release_s",
            "by_policy": by_policy, "paired": paired}


def fairness_analysis(data):
    result = {}
    order_rows = []
    worst = []
    for policy in POLICIES:
        items = [block[policy] for block in data.values()]
        long_rows = [r for item in items for r in item["rows"]
                     if r["prompt_class"] == "long"]
        waits = [r["queue_wait_ms"] for r in long_rows]
        ratios = {metric: [] for metric in ("queue_wait_ms", "ttft_ms")}
        for item in items:
            first_order = {r["request_id"]: i+1 for i, r in enumerate(
                sorted(item["rows"], key=lambda r: (r["first_scheduled_s"], r["request_id"])))}
            finish_order = {r["request_id"]: i+1 for i, r in enumerate(
                sorted(item["rows"], key=lambda r: (r["finished_s"], r["request_id"])))}
            long_first = {r["request_id"]: i+1 for i, r in enumerate(
                sorted(selected_rows(item, "long"), key=lambda r: (r["first_scheduled_s"], r["request_id"])))}
            long_finish = {r["request_id"]: i+1 for i, r in enumerate(
                sorted(selected_rows(item, "long"), key=lambda r: (r["finished_s"], r["request_id"])))}
            for r in selected_rows(item, "long"):
                order_rows.append({"run_id": item["run"]["run_id"],
                                   "policy": policy, "trace_seed": item["run"]["trace_seed"],
                                   "repeat_index": item["run"]["repeat_index"],
                                   "request_id": r["request_id"],
                                   "first_selection_order_all": first_order[r["request_id"]],
                                   "finish_order_all": finish_order[r["request_id"]],
                                   "first_selection_order_long": long_first[r["request_id"]],
                                   "finish_order_long": long_finish[r["request_id"]],
                                   "queue_wait_ms": r["queue_wait_ms"],
                                   "ttft_ms": r["ttft_ms"],
                                   "e2e_latency_ms": r["e2e_latency_ms"]})
            for metric in ratios:
                short = stats.median(r[metric] for r in selected_rows(item, "short"))
                long = stats.median(r[metric] for r in selected_rows(item, "long"))
                if short > 0:
                    ratios[metric].append(long / short)
        result[policy] = {
            "long_completion_count": len(long_rows),
            "long_completion_rate": len(long_rows) / 300,
            "long_queue_wait_ms": describe(waits, tail=True),
            "long_ttft_ms": describe((r["ttft_ms"] for r in long_rows), tail=True),
            "long_e2e_latency_ms": describe((r["e2e_latency_ms"] for r in long_rows), tail=True),
            "long_queue_wait_threshold_counts_strictly_greater": {
                str(t): sum(w > t for w in waits) for t in (100, 250, 500, 10000)},
            "unselected_long_count": 0, "unfinished_long_count": 0,
            "run_level_median_long_to_short_ratio": {
                metric: describe(values) for metric, values in ratios.items()},
        }
        worst.extend(sorted((r for r in order_rows if r["policy"] == policy),
                            key=lambda r: r["queue_wait_ms"], reverse=True)[:10])
    write_csv(OUT / "long-request-orders.csv", order_rows, tuple(order_rows[0]))
    result["worst_long_requests_top10_per_policy"] = worst
    return result


def service_order_analysis(data):
    blocks = []
    crossover = collections.Counter()
    overlaps = collections.defaultdict(list)
    thresholds = {("medium", "short"): .2, ("long", "medium"): .3,
                  ("long", "short"): .5}
    for (seed, repetition), block in sorted(data.items()):
        positions = {}
        for policy in ("short_prompt", "aged_short_prompt"):
            ordered = sorted(block[policy]["rows"],
                             key=lambda r: (r["first_scheduled_s"], r["request_id"]))
            positions[policy] = {r["request_id"]: i for i, r in enumerate(ordered)}
        ids = list(positions["short_prompt"])
        differing = sum(positions["short_prompt"][rid] !=
                        positions["aged_short_prompt"][rid] for rid in ids)
        inversions = sum((positions["short_prompt"][a] - positions["short_prompt"][b]) *
                         (positions["aged_short_prompt"][a] - positions["aged_short_prompt"][b]) < 0
                         for i, a in enumerate(ids) for b in ids[i+1:])
        blocks.append({"trace_seed": seed, "repeat_index": repetition,
                       "paired_key": f"seed{seed}-rep{repetition}",
                       "different_first_selection_positions": differing,
                       "discordant_request_pairs": inversions,
                       "total_request_pairs": 1770,
                       "median_absolute_first_selection_time_difference_ms": stats.median(
                           abs(next(r["first_scheduled_s"] for r in block["short_prompt"]["rows"]
                                    if r["request_id"] == rid) -
                               next(r["first_scheduled_s"] for r in block["aged_short_prompt"]["rows"]
                                    if r["request_id"] == rid)) * 1000 for rid in ids)})
        for policy in ("short_prompt", "aged_short_prompt"):
            for older in block[policy]["rows"]:
                for newer in block[policy]["rows"]:
                    threshold = thresholds.get((older["prompt_class"], newer["prompt_class"]))
                    if threshold is None:
                        continue
                    gap = newer["admitted_s"] - older["admitted_s"]
                    # Admission is only a proxy for the unrecorded first-enqueue clock.
                    if gap > 0 and older["first_scheduled_s"] > newer["admitted_s"]:
                        label = f"{policy}/{older['prompt_class']}_vs_{newer['prompt_class']}"
                        overlaps[label].append(gap)
                        if gap >= threshold:
                            crossover[label + "/initial_overlap"] += 1
                            if newer["first_scheduled_s"] < older["first_scheduled_s"]:
                                crossover[label + "/younger_first_selected"] += 1
    return {"observable_first_selection_order_by_block": blocks,
            "blocks_with_any_order_difference": sum(b["discordant_request_pairs"] > 0
                                                     for b in blocks),
            "observed_older_unselected_at_younger_admission_gaps_s": {
                f"{policy}/{older}_vs_{younger}": describe(
                    overlaps[f"{policy}/{older}_vs_{younger}"])
                for policy in ("short_prompt", "aged_short_prompt")
                for older, younger in thresholds},
            "admission_proxy_crossover_opportunities": dict(crossover),
            "crossover_proxy_definition": "Older request admitted at least the nominal threshold before a shorter request and still unselected at the younger admission; scheduler first-enqueue times and candidate decisions are unavailable."}


def anomaly_analysis(data):
    item = data[(303, 4)]["baseline"]
    meta, attempt = item["meta"], item["run"]["attempts"][0]
    start = dt.datetime.fromisoformat(attempt["started_at_utc"])
    finish = dt.datetime.fromisoformat(attempt["finished_at_utc"])
    rows = item["rows"]
    progress = [json.loads(line) for line in item["paths"]["progress.jsonl"].read_text(
        encoding="utf-8").splitlines()]
    times = [p["observation_end_s"] for p in progress]
    log = item["paths"]["runner.log"].read_text(encoding="utf-8", errors="replace")
    comparators = [data[(303, rep)]["baseline"] for rep in range(4)]
    metrics = {}
    for metric in METRICS:
        value = run_stat(item, "overall", metric)
        others = [run_stat(other, "overall", metric) for other in comparators]
        metrics[metric] = {"anomalous_run_mean": value,
                           "other_seed303_baseline_run_means": others,
                           "other_seed303_baseline_range": [min(others), max(others)]}
    return {
        "run_id": item["run"]["run_id"], "paired_key": ANOMALY_KEY,
        "utc_wall_seconds": (finish - start).total_seconds(),
        "runner_metadata_utc_seconds": (
            dt.datetime.fromisoformat(meta["finished_at_utc"]) -
            dt.datetime.fromisoformat(meta["started_at_utc"])).total_seconds(),
        "monotonic_observation_end_s": meta["observation_end_s"],
        "request_release_s_range": [min(r["release_s"] for r in rows),
                                     max(r["release_s"] for r in rows)],
        "request_first_scheduled_s_range": [min(r["first_scheduled_s"] for r in rows),
                                             max(r["first_scheduled_s"] for r in rows)],
        "request_finish_s_range": [min(r["finished_s"] for r in rows),
                                   max(r["finished_s"] for r in rows)],
        "progress_record_count": len(progress),
        "progress_observation_end_s_range": [min(times), max(times)],
        "progress_largest_monotonic_gap_s": max(b-a for a, b in zip(times, times[1:])),
        "runner_log_bytes": item["paths"]["runner.log"].stat().st_size,
        "runner_log_contains_traceback": "Traceback" in log,
        "runner_log_contains_error_marker": any(line.lstrip().lower().startswith(
            ("error:", "exception:", "traceback", "runtimeerror:"))
            for line in log.splitlines()),
        "status": item["run"]["status"],
        "completion_count": meta["completion_count"],
        "lifecycle_invariants": meta["lifecycle_invariants"],
        "overall_run_mean_comparison": metrics,
    }


def esc(value):
    return html.escape(str(value), quote=True)


def svg_header(width, height, title, subtitle):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
            '<rect width="100%" height="100%" fill="#ffffff"/>',
            '<style>text{font-family:Arial,sans-serif;fill:#27313b} .title{font-size:22px;font-weight:700} .sub{font-size:13px;fill:#586575} .axis{font-size:12px;fill:#586575} .tick{font-size:12px;fill:#586575}</style>',
            f'<text x="70" y="38" class="title">{esc(title)}</text>',
            f'<text x="70" y="60" class="sub">{esc(subtitle)}</text>']


def save_svg(name, lines):
    (OUT / "figures" / name).write_text("\n".join(lines + ["</svg>"]) + "\n",
                                         encoding="utf-8")


def metric_figure(summary, metric, name, title):
    width, height = 950, 520
    left, top, right, bottom = 95, 105, 910, 425
    classes = ("short", "medium", "long")
    values = [summary[p][c][metric]["run_means"]["mean"] for p in POLICIES for c in classes]
    spreads = [summary[p][c][metric]["run_means"]["sd"] for p in POLICIES for c in classes]
    ymax = max(a+b for a,b in zip(values,spreads)) * 1.18
    lines = svg_header(width,height,title,"Points: mean of 15 run means; whiskers: ±1 run-level SD")
    for i in range(6):
        value = ymax * i/5
        y = bottom - (bottom-top)*i/5
        lines += [f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="#e2e7eb"/>',
                  f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" class="tick">{value:.0f}</text>']
    lines.append(f'<text x="20" y="{(top+bottom)/2}" transform="rotate(-90 20 {(top+bottom)/2})" class="axis">{esc(title)} (ms)</text>')
    for ci, prompt_class in enumerate(classes):
        center = left + (ci+.5)*(right-left)/3
        lines.append(f'<text x="{center:.1f}" y="{bottom+31}" text-anchor="middle" class="axis">{prompt_class.title()}</text>')
        for pi, policy in enumerate(POLICIES):
            value = summary[policy][prompt_class][metric]["run_means"]["mean"]
            sd = summary[policy][prompt_class][metric]["run_means"]["sd"]
            x = center + (pi-1)*52
            y = bottom - (bottom-top)*value/ymax
            upper = bottom - (bottom-top)*(value+sd)/ymax
            lower = bottom - (bottom-top)*max(0,value-sd)/ymax
            color = COLORS[policy]
            lines += [f'<line x1="{x:.1f}" y1="{upper:.1f}" x2="{x:.1f}" y2="{lower:.1f}" stroke="{color}" stroke-width="2"/>',
                      f'<line x1="{x-7:.1f}" y1="{upper:.1f}" x2="{x+7:.1f}" y2="{upper:.1f}" stroke="{color}" stroke-width="2"/>',
                      f'<line x1="{x-7:.1f}" y1="{lower:.1f}" x2="{x+7:.1f}" y2="{lower:.1f}" stroke="{color}" stroke-width="2"/>',
                      f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{color}"/>']
    for pi, policy in enumerate(POLICIES):
        x = 250 + pi*220
        lines += [f'<circle cx="{x}" cy="480" r="6" fill="{COLORS[policy]}"/>',
                  f'<text x="{x+14}" y="484" class="axis">{policy}</text>']
    save_svg(name, lines)


def paired_ttft_figure(pairs):
    width,height = 1130,600
    left,right,top,bottom = 255,1070,100,515
    chosen = [r for r in pairs if r["metric"] == "ttft_ms" and
              r["run_statistic"] == "mean" and r["reference"] == "baseline"]
    bound = max(abs(r["delta_ms"]) for r in chosen) * 1.1
    lines = svg_header(width,height,"Paired TTFT change vs baseline",
                       "Each dot is one seed/repetition block; negative means lower TTFT (ms)")
    xscale = lambda v: left + (v+bound)/(2*bound)*(right-left)
    for value in (-bound,-bound/2,0,bound/2,bound):
        x=xscale(value)
        lines += [f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" stroke="{"#81909c" if value == 0 else "#e2e7eb"}"/>',
                  f'<text x="{x:.1f}" y="{bottom+22}" text-anchor="middle" class="tick">{value:.0f}</text>']
    for ci,prompt_class in enumerate(CLASSES):
        for pi,policy in enumerate(("short_prompt","aged_short_prompt")):
            group=[r for r in chosen if r["prompt_class"] == prompt_class and r["candidate"] == policy]
            center=top+42+ci*100+pi*38
            values=[r["delta_ms"] for r in group]
            for i,value in enumerate(values):
                jitter=((i*7)%5-2)*2
                lines.append(f'<circle cx="{xscale(value):.1f}" cy="{center+jitter:.1f}" r="3.2" fill="{COLORS[policy]}" fill-opacity=".5"/>')
            mean=stats.fmean(values)
            lines.append(f'<rect x="{xscale(mean)-5:.1f}" y="{center-5}" width="10" height="10" fill="{COLORS[policy]}" stroke="white"/>')
            lines.append(f'<text x="{left-12}" y="{center+4}" text-anchor="end" class="axis">{prompt_class} / {policy}</text>')
    lines.append(f'<text x="{(left+right)/2}" y="{bottom+50}" text-anchor="middle" class="axis">Paired change in run-mean TTFT (ms)</text>')
    save_svg("paired-ttft-change.svg",lines)


def fairness_figure(data):
    width,height=950,540
    left,right,top,bottom=100,900,110,445
    waits={p:sorted(r["queue_wait_ms"] for block in data.values()
                    for r in selected_rows(block[p],"long")) for p in POLICIES}
    xmax=max(550,max(v[-1] for v in waits.values())*1.05)
    lines=svg_header(width,height,"Long-request queue wait distribution",
                     "Empirical CDF of 300 long requests per policy; pooled requests are descriptive")
    for t in (100,250,500):
        x=left+(right-left)*t/xmax
        lines += [f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" stroke="#c7d0d8" stroke-dasharray="5 4"/>',
                  f'<text x="{x:.1f}" y="{top-8}" text-anchor="middle" class="tick">{t} ms</text>']
    for i in range(6):
        y=bottom-(bottom-top)*i/5
        lines += [f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="#e2e7eb"/>',
                  f'<text x="{left-10}" y="{y+4:.1f}" text-anchor="end" class="tick">{i*20}%</text>']
    for policy,values in waits.items():
        pts=[f'{left:.1f},{bottom:.1f}']
        for i,value in enumerate(values,1):
            x=left+(right-left)*value/xmax
            previous_y=bottom-(bottom-top)*(i-1)/len(values)
            y=bottom-(bottom-top)*i/len(values)
            pts += [f'{x:.1f},{previous_y:.1f}',f'{x:.1f},{y:.1f}']
        lines.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{COLORS[policy]}" stroke-width="2.5"/>')
    lines += [f'<text x="{left}" y="{bottom+18}" text-anchor="middle" class="tick">0</text>',
              f'<text x="{right}" y="{bottom+18}" text-anchor="middle" class="tick">{xmax:.0f}</text>']
    for pi,policy in enumerate(POLICIES):
        x=190+pi*230
        lines += [f'<line x1="{x}" y1="495" x2="{x+28}" y2="495" stroke="{COLORS[policy]}" stroke-width="3"/>',
                  f'<text x="{x+36}" y="499" class="axis">{policy}</text>']
    lines.append(f'<text x="{(left+right)/2}" y="{bottom+28}" text-anchor="middle" class="axis">Initial long-request queue wait (ms)</text>')
    save_svg("long-queue-fairness.svg",lines)


def main():
    (OUT/"figures").mkdir(parents=True,exist_ok=True)
    manifest,data,inputs=load_and_validate()
    write_json(OUT/"input-hashes.json",inputs)
    classes=make_class_summaries(data)
    pairs=make_pairs(data)
    write_csv(OUT/"paired-results.csv",pairs,tuple(pairs[0]))
    paired=summarize_pairs(pairs)
    sensitivity=summarize_pairs(make_pairs(data,exclude=ANOMALY_KEY))
    fairness=fairness_analysis(data)
    service=service_order_analysis(data)
    anomaly=anomaly_analysis(data)
    output_counts={p:describe((row["observed_output_tokens"] for block in data.values()
                               for row in block[p]["rows"]),tail=True) for p in POLICIES}
    analysis={"schema":"formal-analysis-v1", "profile_id":manifest["profile_id"],
              "method":{"comparison_unit":"15 (trace_seed, repeat_index) blocks",
                        "pooled_request_unit":"descriptive only; requests are not independent policy replicates",
                        "paired_delta":"candidate minus reference on each run-level mean or median, plus long-class p90/p95/max; percentage uses reference denominator",
                        "percentiles":"nearest rank for pooled request p90/p95",
                        "sd":"sample standard deviation",
                        "bootstrap":"10,000 fixed-seed percentile resamples of the 15 paired blocks; exploratory because three trace seeds repeat"},
              "validation":{"runs":45,"paired_blocks":15,"requests":2700,
                            "completed_requests":2700,"all_trace_and_sidecar_hashes_match":True,
                            "all_request_ids_match_within_blocks":True,
                            "all_metric_formulas_verified":True,
                            "frozen_aggregate_crosschecked":True},
              "classes":classes,"paired":paired,"throughput":throughput_analysis(data),
              "fairness":fairness,"service_order":service,"output_token_counts":output_counts,
              "anomaly":anomaly,
              "sensitivity_excluding_whole_block":{"excluded_paired_key":ANOMALY_KEY,
                                                   "remaining_blocks":14,
                                                   "paired":sensitivity}}
    write_json(OUT/"analysis-summary.json",analysis)
    for metric,name,title in (("ttft_ms","ttft-by-class.svg","TTFT"),
                              ("queue_wait_ms","queue-wait-by-class.svg","Queue wait"),
                              ("e2e_latency_ms","e2e-by-class.svg","E2E latency")):
        metric_figure(classes,metric,name,title)
    paired_ttft_figure(pairs)
    fairness_figure(data)
    anomaly_lines=["# Timing anomaly: seed303-rep4-baseline", "",
                   "The frozen primary dataset retains this completed run. The sensitivity view excludes the entire seed303-rep4 block to preserve pairing.", "",
                   f"- UTC orchestrator duration: {anomaly['utc_wall_seconds']:.3f} s.",
                   f"- Runner metadata UTC duration: {anomaly['runner_metadata_utc_seconds']:.3f} s.",
                   f"- Monotonic observation end: {anomaly['monotonic_observation_end_s']:.3f} s.",
                   f"- Request release range: {anomaly['request_release_s_range'][0]:.3f}–{anomaly['request_release_s_range'][1]:.3f} s; finish range: {anomaly['request_finish_s_range'][0]:.3f}–{anomaly['request_finish_s_range'][1]:.3f} s.",
                   f"- Progress snapshots: {anomaly['progress_record_count']}; largest adjacent monotonic observation gap: {anomaly['progress_largest_monotonic_gap_s']:.3f} s.",
                   f"- Runner log: {anomaly['runner_log_bytes']} bytes; traceback present: {anomaly['runner_log_contains_traceback']}; error marker present: {anomaly['runner_log_contains_error_marker']}.",
                   "- Outcome: 60/60 completed, lifecycle invariants passed.", "",
                   "The UTC and monotonic clocks disagree substantially during this run. The artifacts do not establish whether host suspension, clock behavior, or another cause produced the discrepancy. No request timestamp or measured latency was edited.", "",
                   "## Comparison to other seed303 baseline repetitions", "",
                   "| Run-mean metric | Anomalous run (ms) | Other four runs, range (ms) |", "| --- | ---: | ---: |"]
    for metric,entry in anomaly["overall_run_mean_comparison"].items():
        a,b=entry["other_seed303_baseline_range"]
        anomaly_lines.append(f"| {metric} | {entry['anomalous_run_mean']:.3f} | {a:.3f}–{b:.3f} |")
    (OUT/"anomaly-analysis.md").write_text("\n".join(anomaly_lines)+"\n",encoding="utf-8")
    # Re-read the inputs after all output writes to assert raw bytes were untouched.
    assert all(sha(ROOT/path)==digest for path,digest in inputs.items())
    print(json.dumps({"runs":45,"pairs":15,"requests":2700,"figures":5,
                      "raw_inputs_unchanged":True,"output":str(OUT)},indent=2))


if __name__ == "__main__":
    main()
