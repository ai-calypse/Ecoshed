#!/usr/bin/env python3
"""Minimal simulator adapter. Expand individual instances lazily, never as a gang."""
from dataclasses import dataclass
from pathlib import Path
import argparse
import csv
import json

@dataclass(frozen=True)
class Instance:
    instance_id: str
    task_group_id: str
    job_id: str
    arrival_time_s: int
    cpu_request_cores: float
    memory_request_normalized: float
    duration_s: float

def iter_instances(path):
    """Yield synthetic replay IDs; these are NOT original Alibaba instance IDs.

    Arrival is task creation. Instances may be queued/placed independently.
    Runtime is visible to the simulator engine; policies must not use future
    completion times or future observed CPU measurements to make decisions.
    """
    with Path(path).open(newline='') as f:
        for r in csv.DictReader(f):
            for i in range(int(r['instance_num'])):
                yield Instance(f"{r['task_group_id']}_i{i}",r['task_group_id'],r['job_id'],int(r['arrival_time_s']),
                               float(r['cpu_request_cores']),float(r['memory_request_normalized']),float(r['duration_s']))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('workload',type=Path)
    a=p.parse_args();count=0;cpu_work=0.
    for instance in iter_instances(a.workload):
        count+=1;cpu_work+=instance.cpu_request_cores*instance.duration_s
    print(json.dumps({'instances':count,'cpu_request_core_seconds':cpu_work},indent=2))
