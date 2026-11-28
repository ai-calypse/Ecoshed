import json
from pathlib import Path
import tempfile
import unittest
import uuid
from ARNAV_Task.kafka.events import ReplayError
from ARNAV_Task.kafka.state import State,read_metrics,read_sessions
from ARNAV_Task.tests.test_kafka_events import event


class ReplayStateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'state.sqlite3';self.s=State(self.path);self.addCleanup(self.s.close)
        self.sid=str(uuid.uuid4());self.cfg={'topic':'fixture','bootstrap_servers':'fixture','group_prefix':'test'}
        self.s.create(self.sid,250,'a'*64,2,0,self.cfg,10)
    def test_wal_and_atomic_rollback(self):
        self.assertEqual(self.s.db.execute('PRAGMA journal_mode').fetchone()[0],'wal')
        with self.assertRaises(RuntimeError):
            with self.s.transaction():self.s.update(self.sid,confirmed=10);raise RuntimeError()
        self.assertEqual(self.s.session(self.sid)['confirmed'],0)
    def test_duplicate_does_not_inflate_distinct_metrics(self):
        e=event(sid=self.sid)
        self.s.ingest(self.sid,[(e,10),(e,11)])
        s=self.s.metrics(self.sid);self.assertEqual(s['distinct_count'],1);self.assertEqual(s['consumed'],2)
        self.assertEqual(s['duplicates'],1);self.assertEqual(s['offered_cpu'],.5);self.assertEqual(s['demand'][0]['count'],1)
    def test_conflicting_duplicate_rolls_back_and_persists_error(self):
        e=event(sid=self.sid);self.s.ingest(self.sid,[(e,10)])
        with self.assertRaises(ReplayError):self.s.ingest(self.sid,[({**e,'cpu_request_cores':1},11)])
        s=self.s.metrics(self.sid);self.assertEqual(s['distinct_count'],1);self.assertEqual(s['status'],'failed');self.assertEqual(s['invalid'],1)
    def test_sequence_conflict(self):
        self.s.ingest(self.sid,[(event(sid=self.sid),10)])
        with self.assertRaisesRegex(ReplayError,'sequence'):self.s.ingest(self.sid,[(event(sid=self.sid,instance='raw_attempt_row_8'),11)])
    def test_gap_rolls_back_entire_batch(self):
        with self.assertRaises(ReplayError):self.s.ingest(self.sid,[(event(sid=self.sid),10),(event(sequence=3,sid=self.sid),11)])
        s=self.s.metrics(self.sid);self.assertEqual(s['distinct_count'],0);self.assertEqual(s['gaps'],1);self.assertEqual(s['next_offset'],10)
    def test_equal_time_tie_order(self):
        self.s.ingest(self.sid,[(event(sid=self.sid,instance='raw_attempt_row_10'),10)])
        with self.assertRaisesRegex(ReplayError,'tie order'):self.s.ingest(self.sid,[(event(sequence=2,sid=self.sid,instance='raw_attempt_row_2'),11)])
    def test_session_isolation(self):
        self.s.update(self.sid,status='cancelled');other=str(uuid.uuid4());self.s.create(other,250,'a'*64,2,0,self.cfg,10)
        self.s.ingest(self.sid,[(event(sid=self.sid),10)]);self.s.ingest(other,[(event(sid=other),10)])
        self.assertEqual(self.s.metrics(self.sid)['distinct_count'],1);self.assertEqual(self.s.metrics(other)['distinct_count'],1)
        with self.assertRaises(ReplayError):self.s.ingest(other,[(event(sequence=2,sid=self.sid),11)])
    def test_only_one_active_session(self):
        with self.assertRaises(ReplayError):self.s.create(str(uuid.uuid4()),250,'a'*64,2,0,self.cfg,10)
    def test_restart_safe_counts_and_readonly_interface(self):
        e=event(sid=self.sid);self.s.ingest(self.sid,[(e,10)])
        with State(self.path) as second:second.ingest(self.sid,[(e,10)]);second.heartbeat(self.sid,'consumer')
        s=read_metrics(self.path,self.sid);self.assertEqual(s['distinct_count'],1);self.assertEqual(s['duplicates'],1)
        self.assertEqual(len(read_sessions(self.path)),1)
        with State(self.path,readonly=True) as reader:
            with self.assertRaises(Exception):reader.update(self.sid,confirmed=100)
    def test_invalid_manifest_fails_without_offset_advance(self):
        with self.assertRaises(ReplayError):self.s.ingest(self.sid,[({**event(sid=self.sid),'input_manifest_sha256':'b'*64},10)])
        self.assertEqual(self.s.session(self.sid)['next_offset'],10)
