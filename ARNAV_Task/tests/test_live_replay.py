"""Isolated UI/service fixtures; actual browser evidence uses Alibaba and Kafka."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from streamlit.testing.v1 import AppTest
from ARNAV_Task.analysis.artifacts import ROOT
from ARNAV_Task.kafka.events import config,ReplayError
from ARNAV_Task.kafka.state import State,read_metrics,read_sessions
from ARNAV_Task.dashboard.replay_service import ReplayService,progress,freshness,utc
from ARNAV_Task.dashboard.components.replay_charts import replay_chart
from ARNAV_Task.tests.test_kafka_events import event

APP=ROOT/'ARNAV_Task/dashboard/app.py'


class ReplayServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.cfg=config();self.cfg['database']=str(Path(self.temp.name)/'state.db')
        self.service=ReplayService(self.cfg);self.addCleanup(self.service.close)
        self.sid=str(uuid.uuid4())
    def create(self,status='running'):
        with State(self.cfg['database']) as s:
            s.create(self.sid,250,'a'*64,2,300,self.cfg,0);s.update(self.sid,status=status)
    def test_missing_database_does_not_create_one(self):
        r=self.service.snapshot();self.assertFalse(r['database_available']);self.assertIsNone(r['metrics'])
        self.assertFalse(Path(self.cfg['database']).exists())
    def test_missing_end_timestamp_from_mixed_history_is_unavailable(self):
        for value in (None,float('nan'),float('inf')):self.assertEqual(utc(value),'Unavailable')
        self.assertTrue(utc(0).startswith('1970-01-01'))
    def test_empty_history(self):
        with State(self.cfg['database']):pass
        self.assertEqual(self.service.snapshot()['sessions'],[])
    def test_malformed_database_is_reported(self):
        Path(self.cfg['database']).write_bytes(b'not sqlite')
        self.assertTrue(self.service.snapshot()['error'])
    def test_history_is_bounded_and_paginated(self):
        with State(self.cfg['database']) as s:
            for n in range(31):
                sid=str(uuid.uuid4());s.create(sid,250,'a'*64,2,300,self.cfg,0);s.update(sid,status='cancelled',started_at=float(n))
        self.assertEqual(len(self.service.snapshot()['sessions']),25)
        self.assertEqual(len(self.service.snapshot(page=2)['sessions']),6)
    def test_snapshot_session_isolation_and_no_event_scan(self):
        self.create('complete')
        other=str(uuid.uuid4())
        with State(self.cfg['database']) as s:
            s.create(other,250,'a'*64,2,300,self.cfg,0);s.ingest(other,[(event(sid=other),0)])
        self.assertEqual(self.service.snapshot(self.sid)['metrics']['distinct_count'],0)
        self.assertEqual(self.service.snapshot(other)['metrics']['distinct_count'],1)
    def test_command_safe_validated_arguments(self):
        cmd=self.service.command('start',size=250,speed=300)
        self.assertEqual(cmd[-6:],['start','--size','250','--speed','300','--background'])
        for args in [dict(size='250; touch bad',speed=300),dict(size=2,speed=300),dict(size=250,speed='300; bad')]:
            with self.assertRaises(ReplayError):self.service.command('start',**args)
        with self.assertRaises(ReplayError):self.service.command('stop',sid='x; bad')
    def test_duplicate_start_rejected_before_subprocess(self):
        self.create()
        with patch.object(self.service,'runner') as runner:
            with self.assertRaisesRegex(ReplayError,'active'):self.service.action('start',size=250,speed=300)
            runner.assert_not_called()
    def test_start_missing_inputs(self):
        with patch.object(self.service,'inputs',return_value={'available':False}):
            with self.assertRaisesRegex(ReplayError,'inputs'):self.service.action('start',size=250,speed=300)
    def test_start_missing_broker(self):
        with patch.object(self.service,'inputs',return_value={'available':True,'replay_verified_sizes':[250]}),patch.object(self.service,'broker',return_value={'connected':False}):
            with self.assertRaisesRegex(ReplayError,'Kafka'):self.service.action('start',size=250,speed=300)
    def test_start_controller_command_and_response(self):
        with patch.object(self.service,'inputs',return_value={'available':True,'replay_verified_sizes':[250]}),patch.object(self.service,'broker',return_value={'connected':True}),patch.object(self.service,'runner',return_value=SimpleNamespace(returncode=0,stdout=json.dumps({'replay_id':self.sid}),stderr='')) as runner:
            self.assertEqual(self.service.action('start',size=250,speed=300)['replay_id'],self.sid)
            self.assertIsInstance(runner.call_args.args[0],list)
            self.assertEqual(runner.call_args.kwargs['cwd'],ROOT)
    def test_controller_errors_visible(self):
        self.create()
        with patch.object(self.service,'runner',return_value=SimpleNamespace(returncode=1,stdout='',stderr='fixture stop error')):
            with self.assertRaisesRegex(ReplayError,'fixture stop error'):self.service.action('stop',sid=self.sid)
    def test_broker_failure_graceful_and_not_per_refresh_client(self):
        with patch('ARNAV_Task.dashboard.replay_service.KafkaAdminClient',side_effect=RuntimeError('fixture unavailable')) as factory:
            a=self.service.broker();b=self.service.broker()
            self.assertFalse(a['connected']);self.assertEqual(a,b);self.assertEqual(factory.call_count,1)
    def test_recorded_workload_counts_with_validated_availability(self):
        recorded=json.loads((ROOT/'RAW_Alibaba/prepared/manifest.json').read_text())
        # Availability validation itself is covered by workload and real-broker tests.
        # This service unit test must run before any private inputs are restored.
        with patch('ARNAV_Task.dashboard.replay_service.availability',return_value={'available':True,'workloads':recorded['workloads'],'verified_sizes':[250,1000,4000]}):
            r=self.service.inputs()
        self.assertTrue(r['available'])
        self.assertEqual({w['task_groups']:w['instances'] for w in r['workloads']},{250:16534,1000:68457,4000:378285})
    def test_metric_history_bound_and_verification_receipt(self):
        self.create()
        with State(self.cfg['database']) as s:
            for n in range(20):s.db.execute('INSERT INTO throughput VALUES(?,?,?)',(self.sid,n,1))
            s.save_verification(self.sid,{'passed':True,'complete':False})
        m=read_metrics(self.cfg['database'],self.sid,history_limit=5)
        self.assertEqual(len(m['throughput']),5);self.assertEqual(m['throughput'][0]['wall_second'],15)
        self.assertTrue(m['verification']['passed'])
    def test_progress_uses_unique_count_not_deliveries(self):
        self.assertEqual(progress({'expected':10,'confirmed':10,'distinct_count':5,'consumed':20})['distinct_count'],.5)
        self.assertIsNone(progress({'expected':None,'confirmed':None,'distinct_count':None})['distinct_count'])
    def test_stale_and_recorded_freshness_are_distinct(self):
        m={'status':'running','workers':[{'worker':'consumer','at':1},{'worker':'controller','at':1}]}
        self.assertTrue(freshness(m,30)['consumer_stale']);m['status']='complete'
        self.assertFalse(freshness(m,30)['consumer_stale'])
    def test_offset_observations_are_recorded(self):
        self.create()
        with State(self.cfg['database']) as s:s.observe_offsets(self.sid,10)
        m=self.service.snapshot(self.sid)['metrics'];self.assertEqual(m['offset_history'][0]['topic_lag'],10)
    def test_export_preserves_session_and_definitions(self):
        self.create();m=self.service.snapshot(self.sid)['metrics'];r=self.service.summary(m)
        self.assertEqual(r['replay_id'],self.sid);self.assertNotIn('throughput',r);self.assertIn('metric_definitions',r)


class FakeService:
    def __init__(self,status='running',broker=True,inputs=True,stale=False,empty=False):
        self.cfg=config();self.calls=[];self.online=broker;self.valid=inputs
        self.sid=str(uuid.uuid4());now=time.time();self.now=now
        self.m={'replay_id':self.sid,'size':250,'speed':300,'status':status,'stop_requested':0,'expected':2,'confirmed':1,
                'consumed':3,'distinct_count':1,'duplicates':2,'invalid':0,'gaps':0,'groups_encountered':1,
                'recent_10s_instances_per_s':.1,'average_instances_per_s':.2,'session_lag':0,'observed_lag':9,
                'last_arrival':77,'elapsed_wall_s':5,'next_offset':10,'broker_end':19,'manifest':'a'*64,
                'producer_status':'running','consumer_status':'running','conflicting_duplicates':0,
                'started_at':now-5,'ended_at':None if status=='running' else now,'throughput':[{'wall_second':int(now),'count':1}],
                'demand':[{'logical_bucket':0,'count':1,'cpu':.5,'memory':.01}],
                'offset_history':[{'wall_second':int(now),'session_lag':0,'topic_lag':9}],
                'workers':[{'replay_id':self.sid,'worker':worker,'at':now-30 if stale else now,'status':'running'} for worker in ['consumer','controller']],
                'errors':[],'verification':None}
        if status=='complete':
            self.m.update(distinct_count=2,confirmed=2,verification={'verified_at':now,'passed':True,'complete':True,'input_manifest_sha256':'a'*64,'distinct_instances':2,'persisted_source_stream_sha256':'b'*64})
        self.empty=empty
    def snapshot(self,sid='latest',page=1):
        active=self.m if self.m['status']=='running' else None
        return {'read_at':time.time(),'sessions':[] if self.empty else [self.m], 'active':None if self.empty else active,
                'metrics':None if self.empty else self.m,'freshness':freshness(self.m),'error':None}
    def broker(self,**_):return {'connected':self.online,'endpoint':'fixture','topic':'fixture','partitions':1 if self.online else None,'checked_at':self.now,'error':'fixture broker offline'}
    def inputs(self,**_):return {'available':self.valid,'verified_sizes':[250,1000,4000] if self.valid else [],'replay_verified_sizes':[250] if self.valid else [],
                'workloads':[{'task_groups':250,'instances':2,'instance_resource_skew_counts':{'balanced':2}}] if self.valid else [],
                'arrival_windows':{250:{'logical_start_s':0,'last_observed_arrival_s':100}},'reason':'fixture inputs missing'}
    def action(self,op,**kw):self.calls.append((op,kw));return {'replay_id':self.sid}
    def summary(self,m):return m


class LiveReplayAppTests(unittest.TestCase):
    def app(self,fake):
        with patch('ARNAV_Task.dashboard.replay_service.get_replay_service',return_value=fake):
            app=AppTest.from_file(str(APP),default_timeout=30).run();app.switch_page('views/live_replay.py').run()
        self.assertFalse(app.exception,[e.message for e in app.exception]);return app
    def test_idle_config_defaults_no_workers(self):
        fake=FakeService(empty=True);app=self.app(fake)
        self.assertEqual(app.selectbox(key='live_size').value,250);self.assertEqual(app.selectbox(key='live_speed').value,300)
        self.assertFalse(app.button(key='live_start').disabled);self.assertTrue(app.button(key='live_stop').disabled);self.assertEqual(fake.calls,[])
    def test_active_buttons_and_distinct_progress(self):
        app=self.app(FakeService());self.assertTrue(app.button(key='live_start').disabled);self.assertFalse(app.button(key='live_stop').disabled)
        self.assertTrue(any('50.00%' in str(p.proto.text) for p in app.get('progress')))
        self.assertIn('Session lag',[m.label for m in app.metric]);self.assertIn('Topic lag',[m.label for m in app.metric])
    def test_complete_receipt_is_required(self):
        fake=FakeService('complete');app=self.app(fake)
        self.assertTrue(any('Complete event-level verification passed' in m.value for m in app.success))
        fake.m['verification']=None;app=self.app(fake)
        self.assertFalse(any('Complete event-level verification passed' in m.value for m in app.success))
    def test_failed_cancelled_partial(self):
        for status in ['failed','cancelled','partial']:
            with self.subTest(status=status):
                app=self.app(FakeService(status));self.assertFalse(app.button(key='live_start').disabled)
                self.assertFalse(any('Complete event-level verification passed' in m.value for m in app.success))
    def test_missing_broker_inputs_and_sqlite_views(self):
        for fake in [FakeService('complete',broker=False),FakeService('complete',inputs=False),FakeService(empty=True)]:
            app=self.app(fake)
            if not fake.online or not fake.valid:self.assertTrue(app.button(key='live_start').disabled)
    def test_stale_metric_values_unavailable(self):
        app=self.app(FakeService(stale=True));m={v.label:v.value for v in app.metric}
        self.assertEqual(m['Session lag'],'Unavailable');self.assertEqual(m['Recent throughput'],'Unavailable')
    def test_charts_dark_actual_values_and_downloads(self):
        fake=FakeService('complete');app=self.app(fake)
        self.assertEqual(len(app.get('plotly_chart')),5)
        self.assertTrue(any(x.label=='Download session JSON' for x in app.get('download_button')))
        for kind,field in [('throughput',None),('lag',None),('demand','cpu'),('demand','memory')]:
            fig=replay_chart(fake.m,kind,field=field);self.assertEqual(fig.layout.paper_bgcolor,'rgba(0,0,0,0)')
            self.assertEqual(fig.layout.uirevision,f'{fake.sid}-{kind}-{field}')
    def test_offline_navigation_without_kafka(self):
        fake=FakeService(broker=False)
        with patch('ARNAV_Task.dashboard.replay_service.get_replay_service',return_value=fake):
            app=AppTest.from_file(str(APP),default_timeout=30).run()
            from ARNAV_Task.dashboard.constants import PAGES
            self.assertEqual(len(PAGES),8)
            for name,_ in PAGES:
                if name!='overview':app.switch_page(f'views/{name}.py').run()
                self.assertFalse(app.exception)
