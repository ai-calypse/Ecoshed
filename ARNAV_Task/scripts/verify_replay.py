"""Full event-by-event comparison of durable Kafka arrivals with Phase 3 source."""
import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import time
from ARNAV_Task.kafka.events import config, ReplayError
from ARNAV_Task.kafka.state import State
from ARNAV_Task.workload.source import WorkloadSource
from ARNAV_Task.workload.prepare_replay import canonical_event


def verify(store,sid='latest',*,source=None,allow_partial=False,mark=True):
    source=source or WorkloadSource();s=store.session(sid);sid=s['replay_id'];errors=[]
    full=s['distinct_count']==s['expected']
    if s['manifest']!=source.manifest_sha256:errors.append('Recovered manifest identity differs')
    if s['invalid'] or s['gaps'] or store.db.execute('SELECT COUNT(*) FROM errors WHERE replay_id=?',(sid,)).fetchone()[0]:
        errors.append('Replay has persisted validation, delivery or lifecycle errors')
    if s['confirmed']!=s['distinct_count']:errors.append('Confirmed publication and distinct consumption differ')
    if s['producer_status'] not in (('completed','partial') if allow_partial else ('completed',)):
        errors.append('Producer did not complete the requested replay')
    if s['consumer_status'] not in ('completed','stopped'):errors.append('Consumer has not finished persistence')
    if not full and not allow_partial:errors.append('Incomplete workload instance coverage')
    original=source.events(s['size'])
    if allow_partial and not full:original=itertools.islice(original,s['distinct_count'])
    persisted=store.db.execute('SELECT sequence,digest,payload FROM events WHERE replay_id=? ORDER BY sequence',(sid,))
    compared=0;actual_hash=hashlib.sha256();expected_hash=hashlib.sha256();groups=Counter()
    for row,expected in itertools.zip_longest(persisted,original):
        if row is None or expected is None:
            errors.append(f'Event coverage differs after sequence {compared}');break
        actual=json.loads(row['payload']);encoded=canonical_event(actual)
        if actual!=expected or row['sequence']!=expected['sequence'] or row['digest']!=hashlib.sha256(encoded).hexdigest():
            errors.append(f"Event-level mismatch at sequence {expected['sequence']} ({expected['instance_id']})");break
        actual_hash.update(encoded);expected_hash.update(canonical_event(expected));compared+=1;groups[actual['task_group_id']]+=1
    stored_groups={r['task_group_id']:r['count'] for r in store.db.execute('SELECT * FROM groups WHERE replay_id=?',(sid,))}
    if stored_groups!=dict(groups):errors.append('Persisted group counters differ from verified instances')
    if full:
        expected_groups={k:int(v['instance_num']) for k,v in source.groups(s['size']).items()}
        if dict(groups)!=expected_groups:errors.append('Original task-group multiplicity differs')
    passed=not errors
    result={'replay_id':sid,'passed':passed,'complete':full and passed,'bounded_partial':not full,
            'size':s['size'],'expected_instances':s['expected'],'distinct_instances':s['distinct_count'],
            'confirmed_published':s['confirmed'],'consumed_deliveries':s['consumed'],'duplicate_deliveries':s['duplicates'],
            'invalid_messages':s['invalid'],'sequence_gaps':s['gaps'],'compared_events':compared,'groups':len(groups),
            'input_manifest_sha256':s['manifest'],'persisted_source_stream_sha256':actual_hash.hexdigest(),
            'expected_source_stream_sha256':expected_hash.hexdigest(),'producer_status':s['producer_status'],
            'consumer_status':s['consumer_status'],'errors':errors,
            'scope':'Actual Kafka arrival replay; no live scheduler execution or energy benchmark.'}
    if mark:
        store.save_verification(sid,result)
        if passed:store.update(sid,status='complete' if full else 'partial',ended_at=s['ended_at'] or time.time())
        elif s['status'] not in ('cancelled','partial'):store.update(sid,status='failed',ended_at=s['ended_at'] or time.time())
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config');parser.add_argument('--replay-id',default='latest')
    parser.add_argument('--allow-partial',action='store_true');parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    try:
        cfg=config(args.config)
        with State(cfg['database']) as store:r=verify(store,args.replay_id,allow_partial=args.allow_partial)
        text=json.dumps(r,indent=2)
        if args.output:
            from ARNAV_Task.analysis.artifacts import ROOT,output_path
            output=output_path(ROOT,args.output);output.parent.mkdir(parents=True,exist_ok=True);output.write_text(text+'\n')
        print(text);return 0 if r['passed'] else 1
    except Exception as exc:print(f'ERROR: {exc}');return 1

if __name__=='__main__':raise SystemExit(main())
