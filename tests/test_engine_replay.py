"""CPU concurrency/joins; fake engine asserts exclusive coordinator ownership."""
import copy
from decimal import Decimal
import importlib
import json
from pathlib import Path
from queue import Queue
import sys
from threading import Event, get_ident
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


def requests():
    return [dict(request_id=name, arrival_s=Decimal(arrival), prompt_text='test',
                 prompt_class='short', num_prompt_tokens=32, max_new_tokens=2)
            for name,arrival in [('later-id','0'),('earlier-id','0.05'),('tie-id','0.05')]]


class FakeEngine:
    def __init__(self, later_released=None, fail=False):
        self.owner = get_ident()
        self.later_released = later_released
        self.fail = fail
        self.pending = []
        self.rows = {}
        self.admission_order = []
        self.block_started = Event()
    def check(self):
        if get_ident() != self.owner:
            raise AssertionError('engine accessed outside coordinator')
    def is_finished(self):
        self.check(); return not self.pending
    def enable_telemetry(self, t0_ns, *, clock_ns):
        self.check(); self.t0_ns=t0_ns; self.clock=clock_ns
    def now(self):
        return (self.clock()-self.t0_ns)/1e9
    def add_request(self, tokens, sampling, *, request_id):
        self.check()
        if request_id in self.rows:
            raise AssertionError('duplicate admission')
        self.admission_order.append(request_id)
        row=dict(request_id=request_id, engine_seq_id=900-len(self.rows),
                 t0_ns=self.t0_ns, status='incomplete', num_prompt_tokens=32,
                 max_new_tokens=2, admitted_s=self.now())
        self.rows[request_id]=row
        self.pending.append(row)
    def step(self):
        self.check()
        if self.fail:
            raise RuntimeError('fake step failure')
        row=self.pending.pop(0)
        row['first_scheduled_s']=self.now()
        row['first_prefill_dispatch_s']=self.now()
        if self.later_released and len(self.admission_order)==1:
            self.block_started.set()
            if not self.later_released.wait(3):
                raise AssertionError('producer could not release while step blocked')
        row['first_token_s']=self.now()
        row['token_times_s']=[row['first_token_s'],self.now()]
        row['observed_output_tokens']=2
        row['finished_s']=self.now()
        row['status']='completed'
        return [(row['engine_seq_id'], [7,9])], -1
    def get_telemetry(self, *, completed_only=False):
        self.check()
        return copy.deepcopy(self.rows)


class EngineReplayTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT/'scripts/run_replay.py').exists(), 'engine replay not implemented')
        self.runner=importlib.import_module('run_replay')

    def run_fake(self, engine, rows=None, queue_factory=Queue):
        rows=rows or requests()
        return self.runner.run_replay(engine,rows,{r['request_id']:[1]*32 for r in rows},
                                      {r['request_id']:object() for r in rows},queue_factory=queue_factory)

    def test_producer_releases_during_blocking_step_and_engine_is_exclusively_owned(self):
        later_released=Event()
        engine=FakeEngine(later_released)
        class ObservedQueue(Queue):
            def put(self, item, *args, **kwargs):
                super().put(item,*args,**kwargs)
                if item[0]=='request' and item[1]['request_id']=='earlier-id':
                    if not engine.block_started.is_set():
                        raise AssertionError('test did not exercise a blocked step')
                    later_released.set()
        result=self.run_fake(engine, queue_factory=ObservedQueue)
        self.assertTrue(later_released.is_set())
        self.assertEqual(engine.admission_order,['later-id','earlier-id','tie-id'])
        self.assertEqual(len(result['outputs']),3)
        self.assertEqual(list(result['releases']),engine.admission_order)
        self.assertTrue(all(r['t0_ns']==result['t0_ns'] for r in result['telemetry'].values()))
        for key,row in result['telemetry'].items():
            self.assertLessEqual(result['releases'][key]['actual_release_s'],row['admitted_s'])

    def test_join_uses_request_id_not_sequence_or_completion_order(self):
        rows=requests(); engine=FakeEngine(); result=self.run_fake(engine,rows)
        joined=self.runner.join_records(rows,result,{'trace_sha256':'a'*64,'metadata_sha256':'b'*64},
                                        'cpu-test',9,lambda ids:'answer')
        self.assertEqual([r['request_id'] for r in joined], [r['request_id'] for r in rows])
        self.assertEqual([r['engine_seq_id'] for r in joined],[900,899,898])
        self.assertEqual([r['output_token_count'] for r in joined],[2]*3)
        self.assertEqual(len({r['request_id'] for r in joined}),3)
        self.assertEqual(json.loads(json.dumps(joined)),joined)
        self.assertTrue(all(r['release_s']<=r['admitted_s']<=r['first_scheduled_s']<=
                            r['first_prefill_dispatch_s']<=r['first_token_s']<=r['finished_s'] for r in joined))

    def test_metrics_use_release_not_planned_arrival(self):
        row={'planned_arrival_s':0.250,'release_s':0.252,'admitted_s':0.255,
             'first_scheduled_s':0.280,'first_token_s':0.330,'finished_s':0.361}
        self.assertEqual(self.runner.metrics(row),dict(replay_error_ms=2.0, admission_overhead_ms=3.0,
            queue_wait_ms=25.0,ttft_ms=78.0,engine_ttft_ms=75.0,e2e_latency_ms=109.0))

    def test_shared_origin_release_hook_preserves_legacy_callback(self):
        replay=importlib.import_module('replay_trace')
        now=[10_000_000_000]
        seen=[]; old=[]
        def sleep(seconds):
            now[0]+=round(seconds*1e9)
        records=[dict(request_id='a',arrival_s=Decimal('1'))]
        timings=replay.replay_requests(records,old.append,t0_ns=9_500_000_000,
            clock_ns=lambda:now[0],sleep=sleep,on_release=lambda request,timing:seen.append((request,timing)))
        self.assertEqual(now[0],10_500_000_000)
        self.assertEqual(timings[0]['actual_release_s'],1.0)
        self.assertEqual(old,records)
        self.assertEqual(seen[0][1],timings[0])

    def test_idle_wait_and_same_arrival_order(self):
        rows=requests()
        for row in rows: row['arrival_s']=Decimal('0.02')
        engine=FakeEngine(); result=self.run_fake(engine,rows)
        self.assertEqual(engine.admission_order,[r['request_id'] for r in rows])
        self.assertTrue(all(r['actual_release_s']>=0.02 for r in result['releases'].values()))

    def test_failure_stops_producer_without_waiting_for_distant_arrival(self):
        rows=requests(); rows[-1]['arrival_s']=Decimal('100')
        started=time.perf_counter()
        with self.assertRaisesRegex(RuntimeError,'fake step failure'):
            self.run_fake(FakeEngine(fail=True),rows)
        self.assertLess(time.perf_counter()-started,2)

    def test_invalid_producer_input_propagates_error_instead_of_deadlock(self):
        rows=requests();rows[-1]['arrival_s']=Decimal('-1')
        with self.assertRaises(ValueError):
            self.run_fake(FakeEngine(),rows)

    def test_join_rejects_missing_output_and_clock_mismatch(self):
        rows=requests();result=self.run_fake(FakeEngine(),rows)
        bad=copy.deepcopy(result);bad['outputs'].pop(900)
        with self.assertRaises(ValueError):
            self.runner.join_records(rows,bad,{},'test',9,str)
        bad=copy.deepcopy(result);bad['telemetry']['later-id']['t0_ns']+=1
        with self.assertRaises(ValueError):
            self.runner.join_records(rows,bad,{},'test',9,str)


if __name__=='__main__':
    unittest.main()
