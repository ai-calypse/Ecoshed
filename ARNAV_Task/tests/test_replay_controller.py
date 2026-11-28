from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid
from ARNAV_Task.kafka.controller import run,main
from ARNAV_Task.kafka.events import config,ReplayError
from ARNAV_Task.kafka.state import State
from ARNAV_Task.scripts.verify_replay import verify
from ARNAV_Task.tests.test_kafka_events import event
from ARNAV_Task.kafka.events import source_event
from ARNAV_Task.analysis.artifacts import ROOT
from ARNAV_Task.kafka.admin import ensure_topic


class Source:
    manifest_sha256='a'*64
    def events(self,size):yield source_event(event())
    def groups(self,size):return {'j1_t1':{'instance_num':'1'}}


class ReplayControllerTests(unittest.TestCase):
    def test_unexpected_partition_count_is_rejected(self):
        with patch('ARNAV_Task.kafka.admin.KafkaAdminClient') as client:
            client.return_value.describe_topics.return_value=[{'partitions':[{'replica_nodes':[1]},{'replica_nodes':[1]}]}]
            with self.assertRaisesRegex(ReplayError,'exactly one partition'):ensure_topic(config(),create=False)

    def test_topic_creation_is_idempotent(self):
        from kafka.errors import TopicAlreadyExistsError
        with patch('ARNAV_Task.kafka.admin.KafkaAdminClient') as client:
            client.return_value.create_topics.side_effect=TopicAlreadyExistsError('fixture existing topic')
            client.return_value.describe_topics.return_value=[{'partitions':[{'replica_nodes':[1]}]}]
            client.return_value.describe_cluster.return_value={'brokers':[{'host':'fixture','port':19092}]}
            self.assertEqual(ensure_topic(config())['partitions'],1)

    def test_unavailable_broker_fails_before_creating_session(self):
        cfg=config()
        with tempfile.TemporaryDirectory() as tmp:
            cfg['database']=str(Path(tmp)/'db');cfg['runtime_directory']=tmp
            with patch('ARNAV_Task.kafka.controller.WorkloadSource') as source, patch('ARNAV_Task.kafka.controller.ensure_topic',side_effect=ReplayError('fixture offline broker')):
                source.return_value.select.return_value={'instances':1}  # Isolated unit fixture; no local data dependency.
                with self.assertRaisesRegex(ReplayError,'offline broker'):run(cfg,250,0)
            with State(cfg['database']) as s:self.assertEqual(s.sessions(),[])
    def test_unsupported_speed_and_invalid_limit(self):
        for speed,limit in [(42,None),(0,0)]:
            with self.assertRaises(ReplayError):run(config(),250,speed,limit=limit)
    def test_verify_full_payload_not_just_counts(self):
        cfg=config()
        with tempfile.TemporaryDirectory() as tmp,State(Path(tmp)/'db') as s:
            sid=str(uuid.uuid4());s.create(sid,250,'a'*64,1,0,cfg,0)
            s.ingest(sid,[(event(sid=sid),0)]);s.update(sid,confirmed=1,producer_status='completed',consumer_status='completed')
            self.assertTrue(verify(s,sid,source=Source())['passed'])
            bad=source_event(event());bad['cpu_request_cores']=.6
            s.db.execute('UPDATE events SET payload=? WHERE replay_id=?',(json.dumps(bad),sid))
            self.assertFalse(verify(s,sid,source=Source())['passed'])
    def test_partial_verification_never_claims_complete(self):
        cfg=config()
        with tempfile.TemporaryDirectory() as tmp,State(Path(tmp)/'db') as s:
            sid=str(uuid.uuid4());s.create(sid,250,'a'*64,2,0,cfg,0)
            s.ingest(sid,[(event(sid=sid),0)]);s.update(sid,confirmed=1,producer_status='partial',consumer_status='stopped')
            r=verify(s,sid,source=Source(),allow_partial=True)
            self.assertTrue(r['passed']);self.assertFalse(r['complete']);self.assertEqual(s.session(sid)['status'],'partial')
    def test_compose_configuration_is_pinned_local_and_bounded(self):
        text=(ROOT/'ARNAV_Task/docker-compose.yml').read_text()
        for required in ('apache/kafka:4.4.0@sha256:', 'platform: linux/arm64',
                         '127.0.0.1:19092:19092', 'KAFKA_PROCESS_ROLES: broker,controller',
                         'KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: "1"', '-Xmx512m',
                         'healthcheck:', 'mem_limit: 1536m', 'kafka-data:'):
            self.assertIn(required,text)
        self.assertNotIn('zookeeper:',text.lower())
