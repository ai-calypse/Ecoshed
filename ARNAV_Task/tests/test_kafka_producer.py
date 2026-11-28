from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
import uuid
from ARNAV_Task.kafka.producer import ReplayClock,publish
from ARNAV_Task.kafka.state import State
from ARNAV_Task.tests.test_kafka_events import event
from ARNAV_Task.kafka.events import source_event,config


class FakeStop:
    def __init__(self):self.now=0.;self.waits=[];self.stopped=False
    def is_set(self):return self.stopped
    def wait(self,t):self.waits.append(t);self.now+=t


class FakeSource:
    def __init__(self,n=3):self.n=n
    def events(self,size):
        for i in range(1,self.n+1):yield source_event(event(sequence=i))


class FakeProducer:
    def __init__(self,fail=False,stop=None):self.values=[];self.flushed=False;self.closed=False;self.fail=fail;self.stop=stop
    def send(self,topic,**kwargs):
        offset=len(self.values);self.values.append(kwargs)
        if self.stop:self.stop.set()
        def get(**_):
            if self.fail:raise RuntimeError('fixture delivery failure')
            return SimpleNamespace(partition=0,offset=offset)
        return SimpleNamespace(get=get)
    def flush(self,**kwargs):self.flushed=True
    def close(self,**kwargs):self.closed=True


class KafkaProducerTests(unittest.TestCase):
    def cfg(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);cfg=config();cfg['database']=str(Path(tmp.name)/'state.db');cfg['max_pending']=2
        sid=str(uuid.uuid4())
        with State(cfg['database']) as s:s.create(sid,250,'a'*64,3,0,cfg,0)
        return cfg,sid
    def test_replay_clock_uses_absolute_trace_time(self):
        stop=FakeStop();clock=ReplayClock(120,stop,monotonic=lambda:stop.now)
        self.assertTrue(clock.wait(120));self.assertAlmostEqual(stop.now,1)
        self.assertTrue(clock.wait(360));self.assertAlmostEqual(stop.now,3)
    def test_equal_time_arrivals_do_not_sleep_per_event(self):
        stop=FakeStop();clock=ReplayClock(60,stop,monotonic=lambda:stop.now);clock.wait(120);n=len(stop.waits)
        for _ in range(50):clock.wait(120)
        self.assertEqual(len(stop.waits),n)
    def test_fast_clock_and_drift(self):
        stop=FakeStop();clock=ReplayClock(0,stop,monotonic=lambda:stop.now);clock.wait(50000);self.assertEqual(stop.waits,[])
        clock=ReplayClock(60,stop,monotonic=lambda:stop.now);stop.now=10;clock.wait(60);self.assertEqual(clock.max_drift,9)
    def test_clock_cancellation(self):
        stop=FakeStop();stop.stopped=True
        self.assertFalse(ReplayClock(120,stop,monotonic=lambda:stop.now).wait(100))
    def test_producer_order_and_confirmed_delivery(self):
        cfg,sid=self.cfg();producer=FakeProducer();r=publish(cfg,sid,threading.Event(),source=FakeSource(),producer=producer)
        self.assertEqual(r['confirmed'],3);self.assertEqual(r['status'],'completed');self.assertTrue(producer.flushed);self.assertTrue(producer.closed)
        from ARNAV_Task.kafka.events import decode
        self.assertEqual([decode(v['value'])['sequence'] for v in producer.values],[1,2,3])
        self.assertTrue(all(v['partition']==0 for v in producer.values))
    def test_failed_delivery_not_counted_as_confirmed(self):
        cfg,sid=self.cfg();producer=FakeProducer(fail=True)
        with self.assertRaises(Exception):publish(cfg,sid,threading.Event(),source=FakeSource(),producer=producer)
        with State(cfg['database']) as s:
            self.assertEqual(s.session(sid)['confirmed'],0);self.assertEqual(s.session(sid)['status'],'failed')
    def test_send_failure_still_counts_the_attempt(self):
        cfg,sid=self.cfg()
        class FailedSend(FakeProducer):
            def send(self,*args,**kwargs):raise RuntimeError('fixture send rejected')
        with self.assertRaises(Exception):publish(cfg,sid,threading.Event(),source=FakeSource(),producer=FailedSend())
        with State(cfg['database']) as s:
            self.assertEqual(s.session(sid)['attempted'],1);self.assertEqual(s.session(sid)['confirmed'],0)
    def test_cooperative_cancel_flushes_known_deliveries(self):
        cfg,sid=self.cfg();stop=threading.Event();producer=FakeProducer(stop=stop)
        r=publish(cfg,sid,stop,source=FakeSource(),producer=producer)
        self.assertEqual(r['status'],'cancelled');self.assertEqual(r['confirmed'],1);self.assertTrue(producer.flushed)
    def test_partial_limit_is_not_completion(self):
        cfg,sid=self.cfg()
        with State(cfg['database']) as s:s.update(sid,limit_events=1)
        r=publish(cfg,sid,threading.Event(),source=FakeSource(),producer=FakeProducer())
        self.assertEqual(r['status'],'partial');self.assertEqual(r['confirmed'],1)
    def test_producer_resend_rejected(self):
        cfg,sid=self.cfg()
        publish(cfg,sid,threading.Event(),source=FakeSource(),producer=FakeProducer())
        with self.assertRaisesRegex(Exception,'restart/resend'):publish(cfg,sid,threading.Event(),source=FakeSource(),producer=FakeProducer())
