"""Three isolated development baseline trials with a hard process watchdog."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
from statistics import fmean, median
import subprocess
import sys
from uuid import uuid4

import run_replay

ROOT = Path(__file__).resolve().parents[1]
METRICS = run_replay.METRIC_NAMES


def validate_trial(rows, manifest, trace_rows, trace_hash):
    expected = {r['request_id']:r for r in trace_rows}
    assert len(rows)==len(expected)==12
    assert {r['request_id'] for r in rows}==set(expected)
    assert manifest['trace_sha256']==trace_hash and manifest['policy']=='baseline'
    assert manifest['completion_count']==12 and manifest['capture_outcome']=='completed'
    for row in rows:
        ref=expected[row['request_id']]
        assert row['status']=='completed' and row['capture_complete']
        assert row['trace_sha256']==trace_hash
        assert all(row[key]==ref[key] for key in ('num_prompt_tokens','max_new_tokens','prompt_class'))
        assert row['planned_arrival_s']==ref['arrival_s']
        assert row['output_token_count']==len(row['token_times_s'])==len(row['output_token_ids'])
        chain=[row[key] for key in ('planned_arrival_s','release_s','admitted_s','first_scheduled_s',
                'first_prefill_dispatch_s','first_token_s')]+row['token_times_s']+[row['finished_s'],row['observation_end_s']]
        assert chain==sorted(chain)
        assert row['first_token_s']==row['token_times_s'][0]
        for metric,end,start in (('replay_error_ms','release_s','planned_arrival_s'),
                  ('admission_overhead_ms','admitted_s','release_s'),('queue_wait_ms','first_scheduled_s','admitted_s'),
                  ('ttft_ms','first_token_s','release_s'),('engine_ttft_ms','first_token_s','admitted_s'),
                  ('e2e_latency_ms','finished_s','release_s')):
            assert abs(row[metric]-1000*(row[end]-row[start]))<1e-8
    return True


def run_trial(run_id, run_dir, timeout_s, hard_timeout_s, trace_rows, trace_hash):
    run_dir.mkdir(parents=True,exist_ok=False)
    output=run_dir/'requests.jsonl'; progress=run_dir/'progress.jsonl'; log=run_dir/'runner.log'
    command=[sys.executable,str(ROOT/'scripts/run_replay.py'),'--output',str(output),
             '--run-id',run_id,'--timeout-s',str(timeout_s),'--progress',str(progress)]
    with log.open('x') as stream:
        stream.write('Command: '+' '.join(command)+'\n');stream.flush()
        process=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True,cwd=ROOT)
        hard_timeout=False
        try:
            code=process.wait(timeout=hard_timeout_s)
        except subprocess.TimeoutExpired:
            hard_timeout=True
            os.killpg(process.pid,signal.SIGTERM)
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL);process.wait()
            code=process.returncode
        stream.write(f'\nExit code: {code}; hard_timeout: {hard_timeout}\n')
    metadata=output.with_suffix('.meta.json')
    if output.exists() and metadata.exists():
        rows=[json.loads(line) for line in output.read_text().splitlines()]
        manifest=json.loads(metadata.read_text())
    else:
        # A process killed inside an engine step cannot provide current telemetry.
        # Recover only the last durable coordinator snapshot and mark the rest aborted.
        snapshot=json.loads(progress.read_text().splitlines()[-1]) if progress.exists() else dict(
            t0_ns=None,observation_end_s=0.0,releases={},telemetry={},outputs={})
        rows=run_replay.partial_records(trace_rows,snapshot,dict(trace_sha256=trace_hash,
                metadata_sha256=hashlib.sha256((ROOT/'workloads/dev_trace.meta.json').read_bytes()).hexdigest()),
                run_id,None,lambda tokens:'', 'failed')
        manifest=dict(run_id=run_id,mode='development-baseline-only',policy='baseline',
                      trace_sha256=trace_hash,request_count=len(trace_rows),
                      completion_count=sum(r['status']=='completed' for r in rows),
                      incomplete_request_ids=[r['request_id'] for r in rows if r['status']!='completed'],
                      capture_outcome='hard_timeout' if hard_timeout else 'process_failed',
                      timeout_s=timeout_s,hard_timeout_s=hard_timeout_s,
                      observation_end_s=snapshot['observation_end_s'],t0_ns=snapshot['t0_ns'],
                      error='Engine process stopped before a final manifest; only durable progress is trusted.')
        with output.open('x') as dest:
            for row in rows: dest.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n')
        run_replay.write_json(metadata,manifest)
    manifest['runner_exit_code']=code
    manifest['hard_timeout_s']=hard_timeout_s
    manifest['hard_timeout']=hard_timeout
    # Rewrite only the newly created run's metadata to include watchdog outcome.
    metadata.write_text(json.dumps(manifest,sort_keys=True,indent=2,allow_nan=False)+'\n')
    return rows,manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout-s',type=float,default=90)
    parser.add_argument('--hard-timeout-s',type=float,default=150)
    args=parser.parse_args()
    if not 0<args.timeout_s<args.hard_timeout_s:
        parser.error('require 0 < timeout-s < hard-timeout-s')
    root=ROOT/'artifacts/baseline'
    summary_path=root/'dev-baseline-summary.json'
    if summary_path.exists(): parser.error(f'refusing to overwrite {summary_path}')
    root.mkdir(parents=True,exist_ok=True)
    trace_path=ROOT/'workloads/dev_trace.jsonl'
    trace_hash=hashlib.sha256(trace_path.read_bytes()).hexdigest()
    trace_rows=[json.loads(line) for line in trace_path.read_text().splitlines()]
    runs=[]
    for index in range(3):
        run_id='dev-baseline-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+uuid4().hex[:8]
        rows,manifest=run_trial(run_id,root/run_id,args.timeout_s,args.hard_timeout_s,trace_rows,trace_hash)
        valid=False
        if manifest['runner_exit_code']==0:
            valid=validate_trial(rows,manifest,trace_rows,trace_hash)
        runs.append(dict(run_id=run_id,request_count=len(trace_rows),completion_count=manifest['completion_count'],
                         trace_sha256=manifest['trace_sha256'],capture_outcome=manifest['capture_outcome'],
                         valid=valid,runner_exit_code=manifest['runner_exit_code'],
                         diagnostics=run_replay.diagnostics(rows),artifact_dir=str(root/run_id)))
        print(f'{run_id}: {manifest["completion_count"]}/{len(trace_rows)}; {manifest["capture_outcome"]}; exit={manifest["runner_exit_code"]}',flush=True)
    good=all(r['valid'] for r in runs)
    if good:
        manifests=[json.loads((root/r['run_id']/'requests.meta.json').read_text()) for r in runs]
        stable_fields=('trace_sha256','metadata_sha256','model','tokenizer','sampling','engine_config','policy','project_commit','upstream_commit')
        for key in stable_fields:
            assert all(m[key]==manifests[0][key] for m in manifests),f'changed run invariant: {key}'
        request_metadata=[{k:row[k] for k in ('request_id','prompt_class','num_prompt_tokens','max_new_tokens','planned_arrival_s')}
                          for row in [json.loads(line) for line in (root/runs[0]['run_id']/'requests.jsonl').read_text().splitlines()]]
        for run in runs[1:]:
            other=[{k:row[k] for k in ('request_id','prompt_class','num_prompt_tokens','max_new_tokens','planned_arrival_s')}
                   for row in [json.loads(line) for line in (root/run['run_id']/'requests.jsonl').read_text().splitlines()]]
            assert other==request_metadata
    variation={}
    if good:
        for metric in METRICS:
            means=[r['diagnostics']['overall'][metric]['mean'] for r in runs]
            variation[metric]=dict(run_means_ms=means,min_mean_ms=min(means),max_mean_ms=max(means),
                                   range_of_means_ms=max(means)-min(means),mean_of_run_means_ms=fmean(means))
    summary=dict(mode='development baseline only; not final benchmark data',
                 generated_at_utc=datetime.now(timezone.utc).isoformat(),policy='baseline',
                 trace_sha256=trace_hash,trial_count=3,all_passed=good,runs=runs,
                 cross_run_variation=variation,
                 warning='Four requests per class; diagnostics do not establish statistical performance claims.')
    run_replay.write_json(summary_path,summary)
    print('Summary: '+str(summary_path),flush=True)
    if not good: raise SystemExit(2)

if __name__=='__main__': main()
