"""Opt-in real broker tests. All published arrivals come from validated Alibaba inputs.

Run with ECOSCHED_KAFKA_INTEGRATION=1. This temporarily stops/restarts ONLY the
EcoSched Compose broker for connectivity testing; unrelated containers are untouched.
"""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
import uuid
from kafka import KafkaConsumer,TopicPartition
from ARNAV_Task.analysis.artifacts import ROOT
from ARNAV_Task.kafka.admin import ensure_topic,client_options
from ARNAV_Task.kafka.controller import run,main
from ARNAV_Task.kafka.consumer import consume
from ARNAV_Task.kafka.producer import publish
from ARNAV_Task.kafka.events import config,ReplayError,decode
from ARNAV_Task.kafka.state import State,ACTIVE
from ARNAV_Task.scripts.verify_replay import verify
from ARNAV_Task.workload.source import WorkloadSource

ENABLED=os.environ.get('ECOSCHED_KAFKA_INTEGRATION')=='1'


@unittest.skipUnless(ENABLED,'Real Kafka integration requires explicit ECOSCHED_KAFKA_INTEGRATION=1')
class KafkaIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=config();cls.token=str(uuid.uuid4())
        cls.cfg['database']=str(ROOT/f'ARNAV_Task/.runtime/kafka/integration-{cls.token}.sqlite3')
        cls.cfg['group_prefix']+='-integration'
        cls.config_path=ROOT/f'ARNAV_Task/.runtime/kafka/integration-{cls.token}.json'
        cls.config_path.write_text(json.dumps(cls.cfg))
        cls.evidence={'database':f'ARNAV_Task/.runtime/kafka/integration-{cls.token}.sqlite3','tests':{},'workloads':[]}
        ensure_topic(cls.cfg)

    @classmethod
    def tearDownClass(cls):
        (ROOT/'ARNAV_Task/.runtime/kafka/integration_evidence.json').write_text(json.dumps(cls.evidence,indent=2))

    def save(self,key,value):self.evidence['tests'][key]=value

    def complete(self,size):
        with redirect_stdout(io.StringIO()):r=run(self.cfg,size,0)
        self.assertTrue(r['passed']);self.assertTrue(r['complete']);self.assertEqual(r['invalid_messages'],0)
        with State(self.cfg['database']) as s:m=s.metrics(r['replay_id'])
        self.evidence['workloads'].append({'verification':r,'metrics':m})
        return r,m

    def test_01_broker_arm64_topic_and_actual_message(self):
        inspect=json.loads(subprocess.check_output(['docker','inspect','ecosched-d6-kafka-1']))[0]
        image=json.loads(subprocess.check_output(['docker','image','inspect',inspect['Image']]))[0]
        self.assertEqual(image['Architecture'],'arm64');self.assertEqual(inspect['State']['Health']['Status'],'healthy')
        topic=ensure_topic(self.cfg);self.assertEqual(topic['partitions'],1)
        self.assertEqual(ensure_topic(self.cfg),topic)
        doc=json.loads(subprocess.check_output(['docker','compose','-f','ARNAV_Task/docker-compose.yml','config','--format','json'],cwd=ROOT))
        self.assertEqual(doc['services']['kafka']['ports'][0]['host_ip'],'127.0.0.1')
        self.evidence['broker']={'image':inspect['Config']['Image'],'architecture':image['Architecture'],
                                 'health':inspect['State']['Health']['Status'],'topic':topic,
                                 'memory_limit_bytes':inspect['HostConfig']['Memory']}
        self.save('broker_health_arm64_and_idempotent_admin',True)

    def test_02_full_250(self):
        r,m=self.complete(250);self.assertEqual(r['distinct_instances'],16534);self.assertEqual(r['groups'],250)
        # Read an actual record back from Kafka, independent of SQLite's copy.
        c=KafkaConsumer(**client_options(self.cfg),enable_auto_commit=False)
        tp=TopicPartition(self.cfg['topic'],0)
        try:
            c.assign([tp]);c.seek(tp,m['start_offset']);batch={}
            for _ in range(10):
                batch=c.poll(timeout_ms=500)
                if batch.get(tp):break
            actual=decode(batch[tp][0].value);self.assertEqual(actual['replay_id'],r['replay_id'])
            self.evidence['actual_kafka_message']=actual
        finally:c.close()
        self.save('full_250_verified',True)

    def test_03_full_1000(self):
        r,_=self.complete(1000);self.assertEqual(r['distinct_instances'],68457);self.assertEqual(r['groups'],1000)
        self.save('full_1000_verified',True)

    def test_04_full_4000(self):
        r,_=self.complete(4000);self.assertEqual(r['distinct_instances'],378285);self.assertEqual(r['groups'],4000)
        self.save('full_4000_verified',True)

    def test_05_real_duplicate_redelivery(self):
        sid=self.evidence['workloads'][0]['verification']['replay_id']
        consume(self.cfg,sid,threading.Event(),from_start=True)
        with State(self.cfg['database']) as s:
            r=verify(s,sid);m=s.metrics(sid)
        self.assertTrue(r['passed']);self.assertEqual(r['distinct_instances'],16534)
        self.assertEqual(r['duplicate_deliveries'],16534);self.assertEqual(r['consumed_deliveries'],33068)
        self.save('duplicate_redelivery',{'verification':r,'next_offset':m['next_offset']})

    def test_06_consumer_interruption_and_restart(self):
        source=WorkloadSource();sid=str(uuid.uuid4());tp=TopicPartition(self.cfg['topic'],0)
        c=KafkaConsumer(**client_options(self.cfg),enable_auto_commit=False)
        try:start=c.end_offsets([tp])[tp]
        finally:c.close()
        with State(self.cfg['database']) as s:
            s.create(sid,250,source.manifest_sha256,source.select(250)['instances'],0,self.cfg,start)
            s.update(sid,status='running')
        stop=threading.Event();interrupt=threading.Event();ready=threading.Event();failures=[]
        def reader():
            try:consume(self.cfg,sid,stop,ready=ready,interrupt=interrupt)
            except Exception as exc:failures.append(str(exc))
        def writer():
            try:publish(self.cfg,sid,stop,source=source)
            except Exception as exc:failures.append(str(exc))
        reader_thread=threading.Thread(target=reader);reader_thread.start();self.assertTrue(ready.wait(10))
        writer_thread=threading.Thread(target=writer);writer_thread.start()
        deadline=time.monotonic()+20;mid=0
        while time.monotonic()<deadline:
            with State(self.cfg['database'],readonly=True) as s:mid=s.session(sid)['distinct_count']
            if mid>=250:break
            time.sleep(.01)
        interrupt.set();reader_thread.join(15);writer_thread.join(30)
        self.assertFalse(reader_thread.is_alive());self.assertFalse(writer_thread.is_alive());self.assertFalse(failures)
        with State(self.cfg['database']) as s:
            interrupted=s.session(sid);self.assertEqual(interrupted['consumer_status'],'interrupted')
            self.assertGreater(interrupted['distinct_count'],0);self.assertLess(interrupted['distinct_count'],16534)
        consume(self.cfg,sid,stop)
        with State(self.cfg['database']) as s:r=verify(s,sid)
        self.assertTrue(r['complete'])
        self.save('consumer_restart',{'persisted_before_restart':interrupted['distinct_count'],
                                     'offset_before_restart':interrupted['next_offset'],'verification':r})

    def test_07_bounded_timed_replay(self):
        began=time.monotonic()
        with redirect_stdout(io.StringIO()):r=run(self.cfg,250,600,limit=250)
        with State(self.cfg['database']) as s:m=s.metrics(r['replay_id'])
        self.assertTrue(r['passed']);self.assertFalse(r['complete']);self.assertEqual(r['distinct_instances'],250)
        self.assertEqual(m['status'],'partial');self.assertGreater(m['producer_elapsed'],0)
        self.save('bounded_timed_replay',{'verification':r,'metrics':m,'test_elapsed_s':time.monotonic()-began})

    def test_08_controller_duplicate_start_stop_no_orphan(self):
        sid=str(uuid.uuid4())
        with redirect_stdout(io.StringIO()):
            rc=main(['--config',str(self.config_path),'start','--size','250','--speed','60','--background','--replay-id',sid])
        self.assertEqual(rc,0)
        try:
            with self.assertRaisesRegex(ReplayError,'active'):run(self.cfg,250,0)
            # Let authentic source arrivals begin before requesting cancellation.
            time.sleep(2)
            with redirect_stdout(io.StringIO()):self.assertEqual(main(['--config',str(self.config_path),'stop','--replay-id',sid]),0)
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                with State(self.cfg['database']) as s:session=s.session(sid)
                if session['status']=='cancelled':break
                time.sleep(.1)
            self.assertEqual(session['status'],'cancelled');self.assertEqual(session['producer_status'],'cancelled')
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                listing=subprocess.run(['ps','-p',str(session['controller_pid']),'-o','stat='],capture_output=True,text=True)
                if not listing.stdout.strip() or listing.stdout.strip().startswith('Z'):break
                time.sleep(.1)
            self.assertTrue(not listing.stdout.strip() or listing.stdout.strip().startswith('Z'),'Controller worker remained running')
            self.save('controller_stop_and_duplicate_rejection',{'status':session['status'],'confirmed':session['confirmed'],
                                                                'distinct':session['distinct_count'],'worker_running':False})
        finally:
            with State(self.cfg['database']) as s:s.update(sid,stop_requested=1)

    def test_09_session_isolation(self):
        with State(self.cfg['database']) as s:
            for evidence in self.evidence['workloads']:
                r=evidence['verification'];session=s.session(r['replay_id'])
                self.assertEqual(session['distinct_count'],r['expected_instances'])
                self.assertEqual(s.db.execute('SELECT COUNT(*) FROM events WHERE replay_id=?',(r['replay_id'],)).fetchone()[0],r['expected_instances'])
            self.assertFalse([row for row in s.sessions() if row['status'] in ACTIVE])
        self.save('session_isolation',True)

    def test_10_real_broker_unavailability_and_restart(self):
        compose=['docker','compose','-f','ARNAV_Task/docker-compose.yml']
        subprocess.run(compose+['stop','kafka'],cwd=ROOT,check=True,capture_output=True)
        try:
            with self.assertRaises(ReplayError):ensure_topic(self.cfg,create=False)
            with self.assertRaises(ReplayError):run(self.cfg,250,0)
        finally:
            subprocess.run(compose+['up','-d','--wait'],cwd=ROOT,check=True,capture_output=True,timeout=90)
        self.assertTrue(ensure_topic(self.cfg,create=False)['connected'])
        self.save('broker_unavailable_then_restarted',True)


if __name__=='__main__':unittest.main()
