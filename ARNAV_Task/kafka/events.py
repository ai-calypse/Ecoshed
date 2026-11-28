"""Strict versioned arrival JSON. Control state is out-of-band in SQLite."""
import hashlib
import json
import math
from pathlib import Path
import re
import uuid

from ARNAV_Task.analysis.artifacts import ROOT, read_json
from ARNAV_Task.workload.source import EVENT_FIELDS
from ARNAV_Task.workload.prepare_replay import canonical_event

FIELDS = set(EVENT_FIELDS) | {'replay_id', 'event_type'}


class ReplayError(ValueError):
    def __init__(self, message, code='invalid'):
        super().__init__(message)
        self.code = code


def config(path=None):
    value = read_json(path or ROOT/'ARNAV_Task/config/replay.json')
    if value.get('schema_version') != 1:
        raise ReplayError('Unsupported replay configuration')
    for key in ('database','runtime_directory'):
        value[key] = str((ROOT/value[key]).resolve())
        if not Path(value[key]).is_relative_to(ROOT/'ARNAV_Task/.runtime'):
            raise ReplayError(f'{key} must remain under ARNAV_Task/.runtime')
    return value


def replay_id(value):
    try:
        parsed = uuid.UUID(value)
        if str(parsed) != value or parsed.version != 4:
            raise ValueError()
    except (ValueError, TypeError, AttributeError) as exc:
        raise ReplayError('replay_id must be a canonical UUID4') from exc
    return value


def validate(event, *, session=None):
    if not isinstance(event, dict) or set(event) != FIELDS:
        raise ReplayError('Arrival schema requires exactly the documented fields; future/extra fields are forbidden')
    replay_id(event['replay_id'])
    for name in ('schema_version','sequence','arrival_time_s','workload_groups'):
        if type(event[name]) is not int:
            raise ReplayError(f'{name} must be an integer')
    if event['schema_version'] != 1 or event['event_type'] != 'workload_arrival':
        raise ReplayError('Unsupported event schema_version or event_type')
    if event['sequence'] < 1 or event['arrival_time_s'] < 0 or event['workload_groups'] not in (250,1000,4000):
        raise ReplayError('Invalid sequence, arrival time or workload size')
    for name in ('cpu_request_cores','memory_request_normalized'):
        v=event[name]
        if isinstance(v,bool) or not isinstance(v,(float,int)) or not math.isfinite(v) or v <= 0:
            raise ReplayError(f'{name} must be positive and finite')
    if not isinstance(event['input_manifest_sha256'],str) or not re.fullmatch(r'[a-f0-9]{64}',event['input_manifest_sha256']):
        raise ReplayError('Invalid manifest SHA-256')
    if event['resource_skew'] not in ('balanced','cpu_heavy','memory_heavy'):
        raise ReplayError('Unsupported resource skew')
    for name,pattern in [('instance_id',r'raw_attempt_row_[1-9][0-9]*'),('task_group_id',r'j[0-9]+_t[0-9]+'),('job_id',r'[0-9]+')]:
        if not isinstance(event[name],str) or not re.fullmatch(pattern,event[name]):
            raise ReplayError(f'Invalid {name}')
    if event['task_group_id'].split('_')[0] != 'j'+event['job_id']:
        raise ReplayError('Task group and job identities differ')
    if session:
        if event['replay_id']!=session['replay_id'] or event['input_manifest_sha256']!=session['manifest'] or event['workload_groups']!=session['size']:
            raise ReplayError('Replay/session/manifest identity differs')
    return event


def arrival(source_event, session_id):
    return validate({**source_event,'replay_id':session_id,'event_type':'workload_arrival'})


def encode(event):
    validate(event)
    return json.dumps(event,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def decode(payload):
    def pairs(items):
        d={}
        for k,v in items:
            if k in d:raise ReplayError(f'Duplicate JSON key: {k}')
            d[k]=v
        return d
    try:
        return validate(json.loads(payload,object_pairs_hook=pairs))
    except (UnicodeError,ValueError,TypeError) as exc:
        raise ReplayError(f'Invalid Kafka arrival JSON: {exc}') from exc


def source_event(event):
    return {k:event[k] for k in EVENT_FIELDS}


def payload_digest(event):
    return hashlib.sha256(canonical_event(source_event(event))).hexdigest()
