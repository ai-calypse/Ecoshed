from pathlib import Path
import tempfile
import unittest
import uuid
from kafka import TopicPartition
from ARNAV_Task.kafka.consumer import persist_then_commit,consume
from ARNAV_Task.kafka.state import State
from ARNAV_Task.kafka.events import config
from ARNAV_Task.tests.test_kafka_events import event


class KafkaConsumerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.cfg=config();self.path=Path(self.temp.name)/'state.db'
        self.cfg['database']=str(self.path)
        self.sid=str(uuid.uuid4());self.state=State(self.path);self.addCleanup(self.state.close)
        self.state.create(self.sid,250,'a'*64,1,0,self.cfg,0)
    def test_manual_commit_happens_after_durable_db_commit(self):
        called=[];test=self
        class Consumer:
            def commit(self,offsets):
                with State(test.path,readonly=True) as reader:
                    test.assertEqual(reader.session(test.sid)['distinct_count'],1)
                    test.assertEqual(reader.session(test.sid)['next_offset'],1)
                called.append(offsets)
        tp=TopicPartition(self.cfg['topic'],0)
        persist_then_commit(self.state,self.sid,[(event(sid=self.sid),0)],Consumer(),tp,self.cfg)
        self.assertEqual(called[0][tp].offset,1)
    def test_failure_before_kafka_commit_is_restart_safe(self):
        class Failure:
            def commit(self,_):raise RuntimeError('fixture crash before Kafka commit')
        tp=TopicPartition(self.cfg['topic'],0);e=event(sid=self.sid)
        with self.assertRaises(RuntimeError):persist_then_commit(self.state,self.sid,[(e,0)],Failure(),tp,self.cfg)
        self.state.ingest(self.sid,[(e,0)])
        s=self.state.metrics(self.sid);self.assertEqual(s['distinct_count'],1);self.assertEqual(s['duplicates'],1)
    def test_invalid_batch_is_not_committed(self):
        class Consumer:
            def commit(self,_):raise AssertionError('must not commit invalid data')
        with self.assertRaises(Exception):persist_then_commit(self.state,self.sid,[(event(sequence=2,sid=self.sid),0)],Consumer(),TopicPartition(self.cfg['topic'],0),self.cfg)

    def test_redelivery_reads_to_cursor_boundary_not_durable_high_watermark(self):
        from types import SimpleNamespace
        import threading
        from ARNAV_Task.kafka.events import encode
        tp=TopicPartition(self.cfg['topic'],0)
        records=[event(sequence=i,sid=self.sid) for i in range(1,4)]
        self.state.update(self.sid,expected=3)
        self.state.ingest(self.sid,[(e,i) for i,e in enumerate(records)])
        self.state.update(self.sid,confirmed=3,producer_status='completed',end_offset=3,status='complete')
        class Reader:
            def assign(self,_):pass
            def committed(self,_):return 3
            def seek(self,_,offset):self.cursor=offset
            def position(self,_):return self.cursor
            def end_offsets(self,_):return {tp:3}
            def poll(self,**_):
                offset=self.cursor;self.cursor+=1
                return {tp:[SimpleNamespace(offset=offset,value=encode(records[offset]))]}
            def commit(self,_):pass
            def close(self,**_):pass
        consume(self.cfg,self.sid,threading.Event(),from_start=True,consumer=Reader())
        self.assertEqual(self.state.session(self.sid)['duplicates'],3)
        self.assertEqual(self.state.session(self.sid)['consumed'],6)
