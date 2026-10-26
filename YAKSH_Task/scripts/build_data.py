#!/usr/bin/env python3
"""Build EcoSched D1 using Python's standard library; raw inputs stay untouched."""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
from sampling_quality import refine, measure, assert_limits, comparison_rows

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = {
    'server_event.csv': 'timestamp machine_id event_type event_detail cpu_capacity_cores memory_capacity_normalized disk_capacity_normalized'.split(),
    'server_usage.csv': 'timestamp machine_id cpu_percent memory_percent disk_percent load1 load5 load15'.split(),
    'batch_task.csv': 'create_timestamp modify_timestamp job_id task_id instance_num status plan_cpu_raw plan_mem_normalized'.split(),
    'batch_instance.csv': 'start_timestamp end_timestamp job_id task_id machine_id status seq_no total_seq_no real_cpu_max real_cpu_avg real_mem_max real_mem_avg'.split(),
    'container_event.csv': 'timestamp event_type instance_id machine_id plan_cpu plan_mem plan_disk cpuset'.split(),
    'container_usage.csv': 'timestamp instance_id cpu_percent memory_percent disk_percent load1 load5 load15 avg_cpi avg_mpki max_cpi max_mpki'.split()
}

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')

def write_csv(path, rows, fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    fields = fields or list(rows[0])
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def rank(seed, key):
    return hashlib.sha256(f'{seed}:{key}'.encode()).hexdigest()

def number(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (ValueError, TypeError):
        return None

def stratified(rows, size, key, seed, identity, marginal=None, ensure_marginal_coverage=False):
    """Hamilton proportional allocation, stable hash selection within each stratum."""
    if size > len(rows) or size < 1:
        raise ValueError(f'Cannot sample {size} from {len(rows)}')
    if marginal is not None:
        # Enforce resource-mix quotas before allocating time/multiplicity cells.
        # Flat largest-remainder sampling otherwise biases small samples toward
        # the most common category in many tiny time cells.
        outer = collections.defaultdict(list)
        for r in rows:
            outer[marginal(r)].append(r)
        q = {k: size*len(v)/len(rows) for k,v in outer.items()}
        n = {k: math.floor(v) for k,v in q.items()}
        lower = 1 if ensure_marginal_coverage else 0
        if size < lower*len(outer): raise ValueError('Host sample too small to cover capacity classes')
        n = {k:max(lower,v) for k,v in n.items()}
        while sum(n.values()) < size:
            k=min((k for k in outer if n[k]<len(outer[k])),key=lambda k:(-(q[k]-n[k]),rank(seed,str(k))))
            n[k]+=1
        while sum(n.values()) > size:
            k=min((k for k in outer if n[k]>lower),key=lambda k:(-(n[k]-q[k]),rank(seed,str(k))))
            n[k]-=1
        return [r for k in sorted(outer) if n[k] for r in stratified(outer[k],n[k],key,seed,identity)]
    groups = collections.defaultdict(list)
    for r in rows:
        groups[key(r)].append(r)
    quotas = {k: size * len(v) / len(rows) for k, v in groups.items()}
    counts = {k: math.floor(v) for k, v in quotas.items()}
    remainder = size - sum(counts.values())
    for k in sorted(groups, key=lambda k: (-(quotas[k] - counts[k]), rank(seed, str(k))))[:remainder]:
        counts[k] += 1
    result = []
    for k in sorted(groups):
        result.extend(sorted(groups[k], key=lambda r: rank(seed, identity(r)))[:counts[k]])
    return result

def scan(raw, name, audit):
    """Validate field count, record missing fields; fail on unexpected structural corruption."""
    a = {'rows': 0, 'widths': collections.Counter(), 'missing': collections.Counter(), 'extra_blank_column_rows': 0}
    audit[name] = a
    with (raw / name).open(newline='') as f:
        for line, row in enumerate(csv.reader(f), 1):
            a['rows'] += 1
            a['widths'][str(len(row))] += 1
            if name == 'container_event.csv' and len(row) == 9 and row[-1] == '':
                row = row[:-1]
                a['extra_blank_column_rows'] += 1
            if len(row) != len(SCHEMAS[name]):
                raise ValueError(f'{name}:{line}: unexpected {len(row)} fields')
            for i, x in enumerate(row):
                if x == '':
                    a['missing'][SCHEMAS[name][i]] += 1
            yield line, row

def skew(cpu, mem, ref_cpu, ref_mem, threshold):
    ratio = (cpu / ref_cpu) / (mem / ref_mem)
    return 'cpu_heavy' if ratio > threshold else 'memory_heavy' if ratio < 1 / threshold else 'balanced'

def distribution(rows, key, weight=lambda r: 1):
    c = collections.Counter()
    for r in rows:
        c[str(key(r))] += weight(r)
    return c

def tv(a, b):
    sa, sb = sum(a.values()), sum(b.values())
    return sum(abs(a[k]/sa-b[k]/sb) for k in sorted(a.keys() | b.keys())) / 2

def build(raw, out, cfg, archive=None):
    out.mkdir(parents=True, exist_ok=True)
    data, reports = out / 'data', out / 'reports'
    audit = {}
    sources = {n: {'bytes': (raw/n).stat().st_size, 'sha256': sha(raw/n)} for n in SCHEMAS}
    archive_info = {'verified': False, 'reason': 'archive not supplied'}
    if archive:
        digest = sha(archive)
        if digest != cfg['expected_archive_sha256']:
            raise ValueError('Archive differs from Alibaba published SHA256; inspect input before use.')
        archive_info = {'verified': True, 'sha256': digest, 'expected_sha256': cfg['expected_archive_sha256']}
    print('Input fingerprints complete; scanning hosts and tasks.', flush=True)
    hosts, events = {}, []
    for line, r in scan(raw, 'server_event.csv', audit):
        ts, mid, event = int(r[0]), r[1], r[2]
        if event == 'add':
            cpu, mem = number(r[4]), number(r[5])
            if not cpu or cpu <= 0 or not mem or mem <= 0:
                raise ValueError(f'Invalid host capacity, line {line}')
            if mid in hosts:
                raise ValueError(f'Duplicate host {mid}')
            hosts[mid] = {'machine_id': mid, 'cpu_capacity_cores': cpu, 'memory_capacity_normalized': mem,
                          'disk_capacity_normalized': float(r[6]), 'source_row': line}
        else:
            events.append({'timestamp_s': ts, 'machine_id': mid, 'event_type': event, 'event_detail': r[3], 'source_row': line})
    usage = collections.defaultdict(lambda: [0, 0., 0.])
    usage_rows = []
    usage_bad = 0
    for line, r in scan(raw, 'server_usage.csv', audit):
        vals = [number(x) for x in r[2:5]]
        if r[1] not in hosts or any(x is None or not 0 <= x <= 100 for x in vals):
            usage_bad += 1
            continue
        a = usage[r[1]]; a[0] += 1; a[1] += vals[0]; a[2] += vals[1]
        usage_rows.append({'timestamp_s': int(r[0]), 'machine_id': r[1], 'cpu_fraction': vals[0]/100, 'memory_fraction': vals[1]/100})
    for mid, h in hosts.items():
        n, cpu, mem = usage[mid]
        h.update({'usage_observations': n, 'mean_cpu_fraction': cpu/n/100 if n else '', 'mean_memory_fraction': mem/n/100 if n else ''})
    audit['server_usage.csv']['invalid_utilization_or_host_rows'] = usage_bad
    # Capacity and observed load strata. Missing utilization stays a separate stratum.
    for h in hosts.values():
        h['host_stratum'] = f"{h['cpu_capacity_cores']:g}|{round(h['memory_capacity_normalized'],2):.2f}|" + (
            f"{min(int(h['mean_cpu_fraction']*4),3)}|{min(int(h['mean_memory_fraction']*4),3)}" if h['usage_observations'] else 'missing')
    all_hosts = sorted(hosts.values(), key=lambda h: int(h['machine_id']))
    sample_hosts = stratified(all_hosts, cfg['host_count'], lambda h: h['host_stratum'], cfg['seed'], lambda h: h['machine_id'],
                             marginal=lambda h:(h['cpu_capacity_cores'],round(h['memory_capacity_normalized'],2)),ensure_marginal_coverage=True)
    sample_hosts.sort(key=lambda h: int(h['machine_id']))
    selected_ids = {h['machine_id'] for h in sample_hosts}
    ref_cpu = statistics.median(h['cpu_capacity_cores'] for h in sample_hosts)
    ref_mem = statistics.median(h['memory_capacity_normalized'] for h in sample_hosts)
    tasks, exclusions = {}, collections.Counter()
    for line, r in scan(raw, 'batch_task.csv', audit):
        reason = None
        vals = [number(r[i]) for i in [0, 1, 4, 6, 7]]
        if not r[2] or not r[3]: reason = 'missing_key'
        elif r[5] != 'Terminated': reason = 'not_terminated'
        elif any(v is None for v in vals): reason = 'missing_or_nonfinite_required_value'
        else:
            created, modified, count, cpu, mem = vals
            if not cfg['window_start_s'] <= created < cfg['window_end_s']: reason = 'arrival_outside_window'
            elif modified <= created or modified > cfg['window_end_s']: reason = 'invalid_or_censored_task_end'
            elif count < 1 or not count.is_integer() or cpu <= 0 or mem <= 0 or mem > 1: reason = 'invalid_request_or_count'
        if reason:
            exclusions[reason] += 1
            continue
        key = (r[2], r[3])
        if key in tasks: raise ValueError(f'Duplicate task key {key}')
        tasks[key] = {'job_id': r[2], 'task_id': r[3], 'instance_num': int(count), 'arrival_time_s': int(created)-cfg['window_start_s'],
            'source_create_timestamp_s': int(created), 'source_modify_timestamp_s': int(modified), 'source_status': r[5],
            'plan_cpu_raw': cpu, 'cpu_request_cores': cpu/cfg['batch_cpu_units_per_core'], 'memory_request_normalized': mem, 'source_row': line}
    print(f'Host sample selected; {len(tasks):,} candidate task groups. Scanning instances once.', flush=True)
    # Per task: count, duration sum, minimum, maximum, CPU count/sum, memory count/sum.
    agg = collections.defaultdict(lambda: [0,0.,float('inf'),0.,0,0.,0,0.])
    instance_flags = collections.Counter(); instance_status = collections.Counter()
    for line, r in scan(raw, 'batch_instance.csv', audit):
        instance_status[r[5]] += 1
        s, e = number(r[0]), number(r[1])
        if not r[2] or not r[3]: instance_flags['missing_join_key'] += 1
        if s is not None and s < 0: instance_flags['negative_start_timestamp'] += 1
        if s is None or e is None: instance_flags['invalid_timestamp'] += 1; continue
        if r[5] != 'Terminated' or s < cfg['window_start_s'] or e <= s or e > cfg['window_end_s']:
            instance_flags['not_complete_in_window'] += 1; continue
        if r[6] != '1': instance_flags['completed_retry_excluded'] += 1; continue
        key = (r[2], r[3])
        t = tasks.get(key)
        if t is None: instance_flags['no_eligible_task_join'] += 1; continue
        if r[4] not in hosts: instance_flags['unknown_machine'] += 1; continue
        if s < t['source_create_timestamp_s'] or e > t['source_modify_timestamp_s']:
            instance_flags['outside_parent_task_interval'] += 1; continue
        a = agg[key]; d=e-s; a[0]+=1; a[1]+=d; a[2]=min(a[2],d); a[3]=max(a[3],d)
        for idx, pos in [(9,4),(11,6)]:
            v=number(r[idx])
            if v is not None and v >= 0:
                a[pos]+=1; a[pos+1]+=v
        instance_flags['accepted_for_duration_estimate'] += 1
        if line % 2000000 == 0: print(f'  scanned {line:,} instance records', flush=True)
    audit['batch_instance.csv']['flags'] = instance_flags
    audit['batch_instance.csv']['statuses'] = instance_status
    clean=[]
    for key,t in tasks.items():
        a=agg.get(key)
        if not a or a[0]==0: exclusions['no_valid_completed_first_attempt']+=1; continue
        if a[0] > t['instance_num']: exclusions['more_completed_trials_than_declared_instances']+=1; continue
        cpu,mem=t['cpu_request_cores'],t['memory_request_normalized']
        if not any(cpu <= h['cpu_capacity_cores'] and mem <= h['memory_capacity_normalized'] for h in sample_hosts):
            exclusions['instance_cannot_fit_any_sample_host']+=1; continue
        t.update({'duration_s': a[1]/a[0], 'duration_min_s':a[2], 'duration_max_s':a[3], 'duration_observations':a[0],
                  'duration_observation_coverage':a[0]/t['instance_num'],
                  'actual_cpu_mean_observed':a[5]/a[4] if a[4] else '', 'actual_cpu_observations':a[4],
                  'actual_memory_mean_observed':a[7]/a[6] if a[6] else '', 'actual_memory_observations':a[6],
                  'resource_skew':skew(cpu,mem,ref_cpu,ref_mem,cfg['skew_ratio_threshold']),
                  'time_bin':t['arrival_time_s']//cfg['time_bin_s']})
        n=t['instance_num']; t['multiplicity_band']='1' if n==1 else '2-100' if n<=100 else '101-1000' if n<=1000 else '1001+'
        t['task_group_id']=f"j{t['job_id']}_t{t['task_id']}"
        clean.append(t)
    clean.sort(key=lambda t:(t['arrival_time_s'],int(t['job_id']),int(t['task_id'])))
    # Audit optional online-service tables structurally; do not silently add their usage to batch demand.
    for name in ['container_event.csv','container_usage.csv']:
        for _,r in scan(raw,name,audit): pass
    write_csv(data/'hosts_all.csv',all_hosts)
    write_csv(data/'hosts_64.csv' if cfg['host_count']==64 else data/f"hosts_{cfg['host_count']}.csv",sample_hosts)
    event_fields='timestamp_s machine_id event_type event_detail source_row'.split()
    write_csv(data/'host_events.csv',events,event_fields)
    write_csv(data/'host_usage_sample.csv',sorted((r for r in usage_rows if r['machine_id'] in selected_ids),key=lambda r:(r['timestamp_s'],int(r['machine_id']))))
    if not clean: raise ValueError('No eligible workload remains')
    write_csv(data/'tasks_clean.csv',clean)
    all_strata=lambda t:(t['time_bin'],t['resource_skew'],t['multiplicity_band'])
    summaries=[]; comparisons=[]; load_series=[]; weighted_comparisons=[]; quality_results=[]
    total_cpu=sum(h['cpu_capacity_cores'] for h in sample_hosts)
    total_mem=sum(h['memory_capacity_normalized'] for h in sample_hosts)
    horizon=cfg['window_end_s']-cfg['window_start_s']
    for size in cfg['workload_task_counts']:
        chosen=stratified(clean,size,all_strata,cfg['seed'],lambda t:t['task_group_id'],marginal=lambda t:t['resource_skew'])
        print(f'Calibrating {size:,} groups against instance/resource arrival profiles.', flush=True)
        chosen, refinement = refine(clean, chosen, cfg['seed'], cfg['sampling_refinement_max_passes'], cfg['sampling_mix_penalty'])
        chosen.sort(key=lambda t:(t['arrival_time_s'],int(t['job_id']),int(t['task_id'])))
        changes=[]
        for t in chosen:
            cpu=t['cpu_request_cores']*t['instance_num'];mem=t['memory_request_normalized']*t['instance_num']
            changes.extend([(t['arrival_time_s'],cpu,mem),(t['arrival_time_s']+t['duration_s'],-cpu,-mem)])
        active_cpu=active_mem=peak_cpu=peak_mem=0.;last=0.;over_cpu=over_mem=0.
        for ts,group in __import__('itertools').groupby(sorted(changes),key=lambda e:e[0]):
            if active_cpu>total_cpu:over_cpu+=ts-last
            if active_mem>total_mem:over_mem+=ts-last
            for _,c,m in group:active_cpu+=c;active_mem+=m
            peak_cpu=max(peak_cpu,active_cpu);peak_mem=max(peak_mem,active_mem);last=ts
        summary={'task_groups':size,'instances':sum(t['instance_num'] for t in chosen),
                 'cpu_request_core_seconds':sum(t['cpu_request_cores']*t['instance_num']*t['duration_s'] for t in chosen),
                 'memory_request_normalized_seconds':sum(t['memory_request_normalized']*t['instance_num']*t['duration_s'] for t in chosen),
                 'peak_offered_cpu_capacity_ratio':peak_cpu/total_cpu,'peak_offered_memory_capacity_ratio':peak_mem/total_mem,
                 'offered_cpu_over_capacity_seconds':over_cpu,'offered_memory_over_capacity_seconds':over_mem,
                 'time_bin_total_variation':tv(distribution(clean,lambda t:t['time_bin']),distribution(chosen,lambda t:t['time_bin'])),
                 'skew_total_variation':tv(distribution(clean,lambda t:t['resource_skew']),distribution(chosen,lambda t:t['resource_skew'])),
                 'instance_weighted_skew_total_variation':tv(distribution(clean,lambda t:t['resource_skew'],lambda t:t['instance_num']),distribution(chosen,lambda t:t['resource_skew'],lambda t:t['instance_num']))}
        summary['mean_offered_cpu_capacity_ratio']=summary['cpu_request_core_seconds']/total_cpu/horizon
        summary['mean_offered_memory_capacity_ratio']=summary['memory_request_normalized_seconds']/total_mem/horizon
        summary.update(measure(clean, chosen))
        assert_limits(summary, cfg['sampling_limits'])
        write_csv(data/f'workload_{size}.csv',chosen)
        weighted_comparisons.extend(comparison_rows(clean, chosen, size))
        quality_results.append({'task_groups': size, 'passed': True, 'refinement': refinement,
                                'metrics': {key: summary[key] for key in cfg['sampling_limits']}})
        print(f'  {size:,}: all weighted sampling quality limits passed.', flush=True)
        summaries.append(summary)
        for bin_id in range(math.ceil(horizon/cfg['time_bin_s'])):
            subset=[t for t in chosen if t['time_bin']==bin_id]
            load_series.append({'task_groups':size,'time_bin':bin_id,'bin_start_s':bin_id*cfg['time_bin_s'],'arriving_task_groups':len(subset),'arriving_instances':sum(t['instance_num'] for t in subset)})
        for label,fn in [('resource_skew',lambda t:t['resource_skew']),('time_bin',lambda t:t['time_bin']),('multiplicity_band',lambda t:t['multiplicity_band'])]:
            base=distribution(clean,fn);sample=distribution(chosen,fn)
            for k in sorted(base):comparisons.append({'task_groups':size,'dimension':label,'stratum':k,'population_count':base[k],'sample_count':sample[k],'population_fraction':base[k]/len(clean),'sample_fraction':sample[k]/size})
        dump(out/'config'/f'experiment_{size}.json',{'workload':f'../data/workload_{size}.csv','hosts':f"../data/hosts_{cfg['host_count']}.csv",'seed':cfg['seed'],
             'arrival_window_s':horizon,'completion_policy':'drain_after_last_arrival','scheduling_unit':'individual_instance',
             'instance_runtime_model':'task_mean_completed_first_attempt_duration', 'demand_model':'constant_requested_cpu_and_memory',
             'background_online_load':False,'replay_source_host_failures':False,
             'note':'Paths relative to this config. Data handoff only; simulator/policies/power model are separate deliverables.'})
    write_csv(reports/'workload_summary.csv',summaries)
    write_csv(reports/'sampling_comparison.csv',comparisons)
    write_csv(reports/'arrival_profile.csv',load_series)
    write_csv(reports/'weighted_sampling_comparison.csv',weighted_comparisons)
    dump(reports/'sampling_quality.json',{'limits':cfg['sampling_limits'],'workloads':quality_results})
    host_compare=[]
    base=distribution(all_hosts,lambda h:h['host_stratum']);small=distribution(sample_hosts,lambda h:h['host_stratum'])
    for k in sorted(base):host_compare.append({'stratum':k,'population_hosts':base[k],'sample_hosts':small[k],'population_fraction':base[k]/len(all_hosts),'sample_fraction':small[k]/len(sample_hosts)})
    write_csv(reports/'host_sampling_comparison.csv',host_compare)
    audit['task_exclusions_first_reason']=exclusions
    audit['clean_task_groups']=len(clean)
    audit['clean_instances']=sum(t['instance_num'] for t in clean)
    audit['host_sample_total_variation']=tv(base,small)
    audit['usage_timestamp_range_s']=[min(r['timestamp_s'] for r in usage_rows),max(r['timestamp_s'] for r in usage_rows)]
    audit['eligible_task_arrival_range_s']=[min(t['source_create_timestamp_s'] for t in clean),max(t['source_create_timestamp_s'] for t in clean)]
    audit['duration_coverage_median']=statistics.median(t['duration_observation_coverage'] for t in clean)
    dump(reports/'audit.json',audit)
    dump(out/'config'/'resolved_config.json',cfg)
    write_csv(out/'docs'/'raw_schema.csv',({'file':name,'column_1_based':i,'field':field} for name,fields in SCHEMAS.items() for i,field in enumerate(fields,1)))
    generated = list(data.glob('*.csv')) + list(reports.glob('*.csv')) + [reports/'audit.json',reports/'sampling_quality.json',out/'config'/'resolved_config.json',out/'docs'/'raw_schema.csv'] + list((out/'config').glob('experiment_*.json'))
    outputs={str(p.relative_to(out)): {'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(generated)}
    dump(out/'manifest.json',{'format_version':2,'config':cfg,'source_files':sources,'archive':archive_info,'pipeline_sha256':sha(Path(__file__)),
         'pipeline_files':{f'scripts/{name}':sha(Path(__file__).parent/name) for name in ['build_data.py','sampling_quality.py']},
         'outputs':outputs,'workloads':summaries,'host_count':len(sample_hosts),'clean_task_groups':len(clean),
         'official_sources':{'repository':'https://github.com/alibaba/clusterdata','schema':'https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2017/schema.csv','description':'https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2017/trace_201708.md','checksum':'https://raw.githubusercontent.com/alibaba/clusterdata/master/cluster-trace-v2017/SHA256SUM'}})
    print(json.dumps({'clean_task_groups':len(clean),'clean_instances':audit['clean_instances'],'workloads':summaries},indent=2),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw',type=Path,default=ROOT.parent/'trace_201708')
    p.add_argument('--output',type=Path,default=ROOT)
    p.add_argument('--config',type=Path,default=ROOT/'config'/'default.json')
    p.add_argument('--archive',type=Path,default=ROOT.parent/'trace_201708.tgz')
    a=p.parse_args();cfg=json.loads(a.config.read_text())
    if cfg['window_start_s']>=cfg['window_end_s'] or cfg['batch_cpu_units_per_core']<=0: p.error('Invalid time window or CPU divisor')
    build(a.raw.resolve(),a.output.resolve(),cfg,a.archive.resolve() if a.archive.exists() else None)

if __name__=='__main__': main()
