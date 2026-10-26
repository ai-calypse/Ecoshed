#!/usr/bin/env python3
"""Independent validation of saved D1 files, multiplicity, references and hashes."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parents[1]

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def read(path):
    with path.open() as f:return list(csv.DictReader(f))

def validate(root, raw=None, archive=None):
    checks=[]
    def check(condition,label):
        if not condition:raise AssertionError(label)
        checks.append(label)
    m=json.loads((root/'manifest.json').read_text());cfg=m['config']
    for name,meta in m['outputs'].items():
        check(digest(root/name)==meta['sha256'],f'output fingerprint: {name}')
    check(digest(root/'scripts'/'build_data.py')==m['pipeline_sha256'],'pipeline source matches manifest')
    if raw:
        for name,meta in m['source_files'].items():check(digest(raw/name)==meta['sha256'],f'raw fingerprint: {name}')
    if archive:
        check(digest(archive)==cfg['expected_archive_sha256'],'archive matches published Alibaba checksum')
        with tarfile.open(archive,'r:gz') as t:
            members={Path(x.name).name:x for x in t.getmembers() if x.isfile()}
            for name,meta in m['source_files'].items():
                f=t.extractfile(members[name]);h=hashlib.sha256()
                for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
                check(h.hexdigest()==meta['sha256'],f'extracted source equals verified archive: {name}')
    hosts=read(root/'data'/f"hosts_{cfg['host_count']}.csv")
    check(len(hosts)==cfg['host_count'] and len({h['machine_id'] for h in hosts})==len(hosts),'host sample size and uniqueness')
    all_hosts=read(root/'data'/'hosts_all.csv')
    capacity=lambda rows:{(float(h['cpu_capacity_cores']),round(float(h['memory_capacity_normalized']),2)) for h in rows}
    check(capacity(hosts)==capacity(all_hosts),'all source host capacity classes represented')
    clean=read(root/'data'/'tasks_clean.csv');lookup={r['task_group_id']:r for r in clean}
    check(len(lookup)==len(clean),'unique cleaned task keys')
    for r in clean:
        n=int(r['instance_num']);d=float(r['duration_s']);cpu=float(r['cpu_request_cores']);mem=float(r['memory_request_normalized'])
        if not (n>0 and math.isfinite(d) and d>0 and cpu>0 and mem>0):raise AssertionError('invalid cleaned request/runtime')
        if not (int(r['duration_observations'])<=n and int(r['duration_observations'])>0):raise AssertionError('invalid duration coverage')
        if not math.isclose(cpu,float(r['plan_cpu_raw'])/cfg['batch_cpu_units_per_core']):raise AssertionError('CPU conversion mismatch')
        if not (0<=int(r['arrival_time_s'])<cfg['window_end_s']-cfg['window_start_s']):raise AssertionError('arrival outside window')
        if not (float(r['duration_min_s'])<=d<=float(r['duration_max_s'])+1e-8):raise AssertionError('runtime outside observations')
        if not any(cpu<=float(h['cpu_capacity_cores']) and mem<=float(h['memory_capacity_normalized']) for h in hosts):raise AssertionError('unplaceable instance')
    checks.append('all cleaned tasks: CPU units, positive requests/runtime, coverage, arrival window and single-instance feasibility')
    for summary in m['workloads']:
        size=summary['task_groups'];rows=read(root/'data'/f'workload_{size}.csv')
        check(len(rows)==size and len({r['task_group_id'] for r in rows})==size,f'{size}: exact size and no duplicate groups')
        check(all(r==lookup[r['task_group_id']] for r in rows),f'{size}: exact source-subset equality, including instance_num')
        check(sum(int(r['instance_num']) for r in rows)==summary['instances'],f'{size}: instance count reconciles')
        check([int(r['arrival_time_s']) for r in rows]==sorted(int(r['arrival_time_s']) for r in rows),f'{size}: chronological arrivals')
        work=sum(float(r['cpu_request_cores'])*int(r['instance_num'])*float(r['duration_s']) for r in rows)
        check(math.isclose(work,summary['cpu_request_core_seconds'],rel_tol=1e-12),f'{size}: CPU work includes multiplicity')
        check(summary['skew_total_variation']<=3/size,f'{size}: resource-mix quota rounding bound')
        check(summary['time_bin_total_variation']<=0.15,f'{size}: time-bin sampling deviation <= 0.15')
    audit=json.loads((root/'reports'/'audit.json').read_text())
    check(sum(audit['task_exclusions_first_reason'].values())+len(clean)==audit['batch_task.csv']['rows'],'task exclusion accounting balances')
    check(sum(audit['batch_instance.csv']['statuses'].values())==audit['batch_instance.csv']['rows'],'all instance statuses accounted for')
    result={'passed':True,'checks_passed':len(checks),'checks':checks,'full_source_verification':bool(raw and archive)}
    (root/'reports'/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--raw',type=Path);p.add_argument('--archive',type=Path)
    a=p.parse_args();validate(a.root,a.raw,a.archive)
