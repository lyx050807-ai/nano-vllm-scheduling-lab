"""Baseline development integration: producer replay + coordinator-owned engine.

Run: .venv/bin/python scripts/run_replay.py
Only the main/coordinator thread calls engine methods. No policy changes.
The 12-request run is an integration diagnostic, not a performance benchmark.
"""
import argparse
import atexit
from decimal import Decimal
import json
import math
import os
from pathlib import Path
from queue import Queue, Empty
from statistics import fmean
from threading import Event, Thread
from time import perf_counter_ns

if __package__:
    from . import make_trace, replay_trace
else:
    import make_trace
    import replay_trace

ROOT = Path(__file__).resolve().parents[1]
OPTIONS = dict(enforce_eager=True, tensor_parallel_size=1, max_model_len=256,
               max_num_batched_tokens=256, max_num_seqs=1, gpu_memory_utilization=0.6)


def run_replay(engine, requests, token_ids, sampling, *, clock_ns=perf_counter_ns, queue_factory=Queue):
    """Run prevalidated, pretokenized requests after warmup; all engine access is here.

    Unbounded FIFO queue prevents engine service time from backpressuring release.
    Queue residence appears in admission_overhead_ms. Python/OS scheduling can
    still delay producer execution; this is not a real-time arrival guarantee.
    """
    ids = [r['request_id'] for r in requests]
    make_trace.require(ids and len(set(ids)) == len(ids), 'empty/duplicate request IDs')
    make_trace.require(set(ids) == set(token_ids) == set(sampling), 'input ID mismatch')
    make_trace.require(engine.is_finished(), 'engine must be idle after warmup')
    admission_queue = queue_factory()
    stop = Event()
    releases, outputs = {}, {}
    t0_ns = clock_ns()
    engine.enable_telemetry(t0_ns, clock_ns=clock_ns)

    def produce():
        error = None
        try:
            replay_trace.replay_requests(
                requests, t0_ns=t0_ns, clock_ns=clock_ns, sleep=stop.wait, stop_event=stop,
                on_release=lambda request, timing: admission_queue.put(('request', request, timing)))
        except BaseException as exc:
            error = exc
        finally:
            admission_queue.put(('done', error))

    producer = Thread(target=produce, name='trace-replay-producer')
    producer.start()
    producer_done = False

    def accept(item):
        nonlocal producer_done
        if item[0] == 'done':
            producer_done = True
            if item[1] is not None:
                raise item[1]
            return
        _, request, timing = item
        request_id = request['request_id']
        make_trace.require(request_id not in releases, 'duplicate release')
        releases[request_id] = timing
        engine.add_request(token_ids[request_id], sampling[request_id], request_id=request_id)

    try:
        while True:
            if engine.is_finished() and not producer_done:
                accept(admission_queue.get())  # Block when idle; no polling spin.
            while True:
                try:
                    accept(admission_queue.get_nowait())
                except Empty:
                    break
            if not engine.is_finished():
                completed, _ = engine.step()
                for seq_id, tokens in completed:
                    make_trace.require(seq_id not in outputs, 'duplicate completed sequence')
                    outputs[seq_id] = list(tokens)
            elif producer_done:
                break
        end_s = (clock_ns() - t0_ns) / 1_000_000_000
        telemetry = engine.get_telemetry(completed_only=True)
        make_trace.require(list(releases) == ids, 'lost or reordered releases')
        make_trace.require(set(telemetry) == set(ids) and len(outputs) == len(ids),
                           'missing/extra completed requests')
        return dict(t0_ns=t0_ns, observation_end_s=end_s, releases=releases,
                    telemetry=telemetry, outputs=outputs)
    finally:
        stop.set()
        producer.join()  # Cooperative wait wakes promptly even for distant arrivals.


def metrics(row):
    pairs = dict(replay_error_ms=('release_s','planned_arrival_s'),
                 admission_overhead_ms=('admitted_s','release_s'),
                 queue_wait_ms=('first_scheduled_s','admitted_s'),
                 ttft_ms=('first_token_s','release_s'),
                 engine_ttft_ms=('first_token_s','admitted_s'),
                 e2e_latency_ms=('finished_s','release_s'))
    return {name: float((Decimal(str(row[end]))-Decimal(str(row[start])))*1000)
            for name,(end,start) in pairs.items()}


def join_records(requests, result, identity, run_id, eos_token_id, decode):
    """Join complete records by request ID, then engine seq ID; reject bad captures."""
    ids = [r['request_id'] for r in requests]
    make_trace.require(len(set(ids)) == len(ids) and
                       set(ids) == set(result['releases']) == set(result['telemetry']),
                       'request identity mismatch')
    used_sequences = set()
    joined = []
    for request in requests:
        request_id = request['request_id']
        event = result['telemetry'][request_id]
        release = result['releases'][request_id]
        make_trace.require(event['t0_ns'] == result['t0_ns'], 'clock origin mismatch')
        make_trace.require(event['request_id'] == request_id == release['request_id'], 'join ID mismatch')
        make_trace.require(event['status'] == 'completed', 'incomplete telemetry')
        seq_id = event['engine_seq_id']
        make_trace.require(seq_id in result['outputs'] and seq_id not in used_sequences, 'output ID mismatch')
        used_sequences.add(seq_id)
        tokens = result['outputs'][seq_id]
        times = event['token_times_s']
        make_trace.require(len(tokens) == event['observed_output_tokens'] == len(times) and
                           0 < len(tokens) <= request['max_new_tokens'], 'output/token-time count mismatch')
        row = {key: event[key] for key in ('engine_seq_id','admitted_s','first_scheduled_s',
               'first_prefill_dispatch_s','first_token_s','finished_s','token_times_s','observed_output_tokens')}
        for key in ('num_prompt_tokens','max_new_tokens'):
            make_trace.require(event[key] == request[key], 'trace/engine token-limit mismatch')
            row[key] = request[key]
        eos = tokens[-1] == eos_token_id
        capped = len(tokens) == request['max_new_tokens']
        make_trace.require(eos or capped, 'completion lacks EOS/cap stopping condition')
        row.update(schema_version='request-telemetry-v1', run_id=run_id, request_id=request_id,
                   policy='baseline', prompt_class=request['prompt_class'], **identity,
                   planned_arrival_s=float(request['arrival_s']), release_s=release['actual_release_s'],
                   status='completed', reason='eos_and_max_new_tokens' if eos and capped else
                   ('eos' if eos else 'max_new_tokens'), terminal_s=event['finished_s'],
                   observation_end_s=result['observation_end_s'], capture_complete=True, missing_reasons={},
                   output_token_count=len(tokens), output_token_ids=tokens, generated_text=decode(tokens))
        make_trace.require(release['arrival_s'] == row['planned_arrival_s'], 'planned arrival changed')
        chain = [row[key] for key in ('planned_arrival_s','release_s','admitted_s','first_scheduled_s',
                 'first_prefill_dispatch_s','first_token_s')] + times + [row['finished_s'],row['observation_end_s']]
        make_trace.require(all(type(t) in (int,float) and math.isfinite(t) and t >= 0 for t in chain),
                           'missing/invalid lifecycle timestamp')
        make_trace.require(chain == sorted(chain) and row['first_token_s'] == times[0],
                           'lifecycle/token ordering violated')
        row.update(metrics(row))
        joined.append(row)
    make_trace.require(used_sequences == set(result['outputs']), 'extra/warmup output in trace results')
    return joined


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, default=ROOT/'workloads/dev_trace.jsonl')
    parser.add_argument('--model', type=Path, default=ROOT/'models/Qwen3-0.6B')
    parser.add_argument('--output', type=Path, default=ROOT/'artifacts/replay/dev_engine_replay.jsonl')
    args = parser.parse_args()
    sidecar = args.output.with_suffix('.meta.json')
    for path in (args.output,sidecar):
        if path.exists() or path.is_symlink():
            parser.error(f'refusing to overwrite: {path}')
    os.environ['HF_HUB_OFFLINE']='1'
    os.environ['TRANSFORMERS_OFFLINE']='1'
    # Import the existing inference backend before the tokenizer-only validator
    # sets backend-disabling environment flags. No engine is constructed yet.
    import torch
    from nanovllm import LLM, SamplingParams
    requests, identity = replay_trace.load_validated_trace(args.trace,args.model)
    meta = make_trace.strict_json(args.trace.with_suffix('.meta.json').read_text())
    torch.manual_seed(meta['sampling']['inference_seed'])
    engine = LLM(str(args.model.resolve()), **OPTIONS)
    try:
        token_ids = {r['request_id']:engine.tokenizer.encode(r['prompt_text'],
                     add_special_tokens=False,truncation=False) for r in requests}
        for row in requests:
            make_trace.require(len(token_ids[row['request_id']]) == row['num_prompt_tokens'] and
                               row['num_prompt_tokens']+row['max_new_tokens'] <= OPTIONS['max_model_len'],
                               'engine tokenizer/context mismatch')
        sampling = {r['request_id']:SamplingParams(temperature=float(meta['sampling']['temperature']),
                     max_tokens=r['max_new_tokens'],ignore_eos=meta['sampling']['ignore_eos']) for r in requests}
        warmup_tokens = engine.tokenizer.encode('Say hello.',add_special_tokens=False)
        warmup = engine.generate([warmup_tokens],SamplingParams(temperature=0.6,max_tokens=4),use_tqdm=False)
        make_trace.require(engine.is_finished() and not engine.get_telemetry(), 'warmup not idle/untracked')
        torch.manual_seed(meta['sampling']['inference_seed'])
        result = run_replay(engine,requests,token_ids,sampling)
        run_id = 'dev-baseline-' + str(result['t0_ns'])
        joined = join_records(requests,result,identity,run_id,engine.tokenizer.eos_token_id,
                              engine.tokenizer.decode)
        diagnostic = {key:dict(mean=fmean(row[key] for row in joined),max=max(row[key] for row in joined))
                      for key in metrics(joined[0])}
        summary = dict(run_id=run_id,mode='development-integration-only',policy='baseline',
                       request_count=len(requests),completion_count=len(joined),
                       lifecycle_invariants='passed',latency_diagnostics_ms=diagnostic,**identity)
        manifest = dict(summary,clock='time.perf_counter_ns',t0_ns=result['t0_ns'],
                        observation_end_s=result['observation_end_s'],engine_config=OPTIONS,
                        model=meta['model'],tokenizer=meta['tokenizer'],sampling=meta['sampling'],
                        warmup=dict(requests=1,max_new_tokens=4,output_tokens=len(warmup[0]['token_ids']),
                                    telemetry_enabled=False,cache_state='engine constructor plus one request warmup'),
                        project_commit=make_trace.git_output('rev-parse','HEAD').decode().strip(),
                        upstream_commit=(ROOT/'artifacts/environment/upstream-commit.txt').read_text().strip(),
                        dirty=bool(make_trace.git_output('status','--porcelain')),
                        source_sha256={name:make_trace.file_hash(ROOT/name) for name in
                                       ('scripts/run_replay.py','scripts/replay_trace.py','nanovllm/telemetry.py')},
                        tracked_diff_sha256=make_trace.sha256(make_trace.git_output('diff','--binary','HEAD')),
                        timeout_s=None,capture_outcome='completed',
                        timing_note='Host/OS and GIL scheduling affect release; no real-time or benchmark claim.')
        make_trace.write_package(args.output,
            ''.join(json.dumps(row,sort_keys=True,allow_nan=False)+'\n' for row in joined).encode(),
            (json.dumps(manifest,sort_keys=True,indent=2,default=float,allow_nan=False)+'\n').encode())
        print(json.dumps(summary,sort_keys=True,allow_nan=False),flush=True)
    finally:
        atexit.unregister(engine.exit)
        engine.exit()


if __name__=='__main__':
    main()
