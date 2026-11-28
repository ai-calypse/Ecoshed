"""Synthetic transport fixtures only; integration tests use real Phase 3 inputs."""
import json
from pathlib import Path
import unittest
import uuid
from ARNAV_Task.kafka.events import arrival,validate,encode,decode,payload_digest,ReplayError,FIELDS
from ARNAV_Task.analysis.artifacts import ROOT


def event(sequence=1, *, sid=None,instance=None,arrival_s=0):
    return arrival({'schema_version':1,'sequence':sequence,'instance_id':instance or f'raw_attempt_row_{sequence}',
                    'task_group_id':'j1_t1','job_id':'1','arrival_time_s':arrival_s,'cpu_request_cores':.5,
                    'memory_request_normalized':.01,'workload_groups':250,'input_manifest_sha256':'a'*64,
                    'resource_skew':'balanced'},sid or str(uuid.uuid4()))


class KafkaEventTests(unittest.TestCase):
    def test_schema_file_matches_runtime_required_fields(self):
        schema=json.loads((ROOT/'ARNAV_Task/kafka/schema.json').read_text())
        self.assertEqual(set(schema['required']),FIELDS)
        self.assertFalse(schema['additionalProperties'])
    def test_roundtrip_deterministic_and_hash_identity(self):
        e=event();self.assertEqual(decode(encode(e)),e);self.assertEqual(encode(e),encode(dict(reversed(list(e.items())))))
        other={**e,'replay_id':str(uuid.uuid4())};self.assertEqual(payload_digest(e),payload_digest(other))
    def test_extra_future_information_forbidden(self):
        for key in ('duration_s','completion_time','future_cpu','source_end_s'):
            with self.assertRaises(ReplayError):validate({**event(),key:7})
    def test_bad_fields(self):
        for field,value in [('schema_version',2),('schema_version',True),('sequence',0),('sequence',1.5),('arrival_time_s',-1),
                            ('workload_groups',12),('replay_id','latest'),('instance_id','fake'),('job_id','2'),
                            ('input_manifest_sha256','bad'),('resource_skew','unknown'),('event_type','end')]:
            with self.subTest(field=field,value=value),self.assertRaises(ReplayError):validate({**event(),field:value})
    def test_positive_finite_requests(self):
        for key in ('cpu_request_cores','memory_request_normalized'):
            for val in (0,-1,float('nan'),float('inf'),True,'1'):
                with self.subTest(key=key,value=val),self.assertRaises(ReplayError):validate({**event(),key:val})
    def test_invalid_json_and_duplicate_keys(self):
        for payload in (b'{',b'null',b'{}',b'{"sequence":1,"sequence":2}',b'\xff'):
            with self.assertRaises(ReplayError):decode(payload)
    def test_session_identity(self):
        e=event();s={'replay_id':e['replay_id'],'manifest':e['input_manifest_sha256'],'size':250}
        self.assertEqual(validate(e,session=s),e)
        with self.assertRaises(ReplayError):validate(e,session={**s,'manifest':'b'*64})
