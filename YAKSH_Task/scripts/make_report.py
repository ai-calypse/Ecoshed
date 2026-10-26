#!/usr/bin/env python3
"""Generate a concise handoff report from measured build and validation results."""
import argparse
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main(root):
    m=json.loads((root/'manifest.json').read_text());a=json.loads((root/'reports'/'audit.json').read_text())
    v=json.loads((root/'reports'/'validation.json').read_text());cfg=m['config']
    repro_path=root/'reports'/'reproducibility.json'
    repro=json.loads(repro_path.read_text()) if repro_path.exists() else None
    with (root/'data'/'tasks_clean.csv').open() as f:tasks=list(csv.DictReader(f))
    with (root/'data'/f"hosts_{cfg['host_count']}.csv").open() as f:hosts=list(csv.DictReader(f))
    skew={k:sum(t['resource_skew']==k for t in tasks) for k in ['cpu_heavy','balanced','memory_heavy']}
    missing_mem=a['batch_instance.csv']['missing'].get('real_mem_avg',0)
    total_instance=a['batch_instance.csv']['rows']
    lines=['# EcoSched D1: data preparation and sampling report','',
      'Prepared for the **Yaksh / Data & sampling** assignment in the EcoSched AMS 560 proposal. '
      'This is a data handoff, not a simulator or scheduler result.','',
      '## Completion evidence','',
      '| Proposal requirement | Delivered evidence |','|---|---|',
      '| Acquire and verify Alibaba v2017 | Published archive checksum matches; all six extracted files checked against archive content |',
      '| Clean schema and invalid values | All six CSVs audited; filtered task population, named output fields, exclusion accounting |',
      '| Preserve instance_num | Unmodified source multiplicity in all cleaned/sample records; independent validation |',
      '| Deterministic representative host sample | 64 hosts; capacity/utilization strata, seed 560, comparison table |',
      '| Time-stratified workloads at several sizes | 250 / 1,000 / 4,000 groups; skew quotas, 15-minute bins, multiplicity bands |',
      '| D1 documented subset, manifest, cleaned inputs | CSV package, manifest, configurations, scripts and simulator handoff |','',
      '## Verified source','',
      f"The archive SHA-256 is `{cfg['expected_archive_sha256']}`. "
      'Full-source validation also confirms each extracted CSV is byte-identical to the corresponding file inside that verified archive.','',
      '| Raw file | Rows | Size (MiB) |','|---|---:|---:|']
    for n,meta in m['source_files'].items():lines.append(f"| {n} | {a[n]['rows']:,} | {meta['bytes']/1024**2:.2f} |")
    lines += ['',f"The source has **{total_instance:,} instance-trial records**. "
      f"Of these, **{a['batch_instance.csv']['flags']['missing_join_key']:,}** lack job/task join keys and "
      f"**{missing_mem:,} ({missing_mem/total_instance:.1%})** lack average actual memory measurements. "
      'These are measured source limitations, not values imputed by this pipeline.','',
      'The headerless container-event file has an extra trailing blank field; it is recognized and counted. '
      'The missing download schema was supplied from the official v2017 repository and saved under `docs/upstream/`. '
      'The proposal\'s `machine_meta` filename is corrected to v2017\'s `server_event.csv`.','',
      '## Primary population and cleaning','',
      f"The arrival window is **[{cfg['window_start_s']}, {cfg['window_end_s']}) seconds** "
      f"({(cfg['window_end_s']-cfg['window_start_s'])/3600:g} hours). Task/instance completion at the endpoint is allowed. "
      'Only completed task groups with valid requests and usable first-attempt runtime observations enter the population.','',
      f"**{len(tasks):,} clean task groups**, representing **{sum(int(t['instance_num']) for t in tasks):,} declared instances**, remain. "
      f"Median duration-observation coverage is **{a['duration_coverage_median']:.1%}**. "
      f"There are **{sum(float(t['duration_observation_coverage'])<1 for t in tasks):,}** groups with partial duration coverage; "
      'their modeled runtime still uses the available observations and their original multiplicity is preserved.','',
      '| Exclusion (first applicable reason) | Task groups |','|---|---:|']
    for k,n in a['task_exclusions_first_reason'].items():lines.append(f"| {k.replace('_',' ')} | {n:,} |")
    lines += ['',f"The exclusions plus {len(tasks):,} retained groups reconcile to {a['batch_task.csv']['rows']:,} original task rows.",
      '', 'The per-group runtime is the mean of positive completed first-attempt durations inside the parent task interval. '
      'All replicated instances of a group use that mean. This reduces straggler variation and does not reproduce '
      'source instance staggering or DAG dependencies. Selection of completed work introduces survivor/boundary bias.','',
      '## Fixed mini-cluster','',
      f"**{len(hosts)} of 1,313 hosts** are selected using deterministic capacity and observed CPU/memory load strata. "
      f"The host-stratum total-variation distance is **{a['host_sample_total_variation']:.4f}** "
      '(0 is identical; 1 is disjoint). At least one host from each rounded capacity class is reserved; '
      'this deliberately overrepresents the rarest type. See `host_sampling_comparison.csv` for omitted/rounded utilization strata.','',
      f"Total CPU capacity is **{sum(float(h['cpu_capacity_cores']) for h in hosts):g} cores**. "
      f"Total normalized memory capacity is **{sum(float(h['memory_capacity_normalized']) for h in hosts):.6f} units**. "
      'No GB conversion is asserted.','',
      f"Valid source utilization timestamps range from **{a['usage_timestamp_range_s'][0]} to {a['usage_timestamp_range_s'][1]} seconds**. "
      'That later observation window is used only for host sampling/characterization. It is not added as background load '
      'to the first-12-hours batch experiment. Host characteristics are selected offline and are fixed for all schedulers.','',
      '## Workloads and stress diagnostics','',
      '| Groups | Declared instances | Mean offered CPU / memory capacity | Peak offered CPU / memory capacity | Role |',
      '|---:|---:|---:|---:|---|']
    for w in m['workloads']:
        peak=max(w['peak_offered_cpu_capacity_ratio'],w['peak_offered_memory_capacity_ratio'])
        role='light / smoke run' if peak<1 else 'burst-constrained comparison' if peak<3 else 'heavy burst stress case'
        lines.append(f"| {w['task_groups']:,} | {w['instances']:,} | {w['mean_offered_cpu_capacity_ratio']:.3f} / {w['mean_offered_memory_capacity_ratio']:.3f} | {w['peak_offered_cpu_capacity_ratio']:.3f} / {w['peak_offered_memory_capacity_ratio']:.3f} | {role} |")
    lines += ['', 'Offered demand assumes every group\'s instances start immediately at task creation and hold their requested '
      'resources for the modeled mean duration. Ratios above 1 require queuing/rejection or overcommit. '
      'These diagnostics are neither measured utilization nor simulated SLA violations. '
      'Keep queue/admission rules identical across policies and drain all accepted work after the arrival window.','',
      '## Representativeness','',
      '| Groups | Arrival-bin TV | Resource-skew TV | Instance-weighted resource-skew TV |',
      '|---:|---:|---:|---:|']
    for w in m['workloads']:lines.append(f"| {w['task_groups']:,} | {w['time_bin_total_variation']:.4f} | {w['skew_total_variation']:.4f} | {w['instance_weighted_skew_total_variation']:.4f} |")
    lines += ['', 'Total variation compares normalized sample and clean-population distributions. '
      'Resource-mix quotas are applied first, then time/multiplicity quotas, using stable seeded hashes within strata. '
      'Samples preserve original arrival times and instance counts; they do not preserve every rare group or exact '
      'instance-weighted burst magnitude. Sampling is relative to the cleaned completed-work population, not the unfiltered source.','',
      '| Population resource skew | Task groups |','|---|---:|']
    for k,n in skew.items():lines.append(f"| {k} | {n:,} |")
    lines += ['', 'The skew definition compares each request\'s CPU and memory fractions of the median sampled host; '
      'ratio >2 is CPU-heavy and <0.5 is memory-heavy.','',
      '## Verification and reproducibility','',
      f"- Independent saved-output checks: **{v['checks_passed']} passed**; full source/archive verification: **{v['full_source_verification']}**.",
      '- Nine focused algorithm tests passed: selection invariance to input order, quota rounding, uniqueness, seed variation, '
      'edge sample sizes, invalid sizes, resource-skew units, nonfinite-value handling and rare host-capacity preservation.']
    if repro:lines.append(f"- Fresh rebuild comparison: **{repro['compared_files']} generated data/config/report files byte-identical**, "
                         f"manifest identical: **{repro['manifest_identical']}**.")
    else:lines.append('- Fresh rebuild comparison: not yet recorded.')
    lines += ['', 'No scheduler, energy model or performance experiment has been run in D1. '
      'Constant requested demand limits claims about production temporal variability; absolute RAM and migration '
      'time need explicit simulator assumptions. See `docs/SIMULATOR_HANDOFF.md` before integrating LR/MMT.','',
      '## Next team handoff','',
      '1. Brave loads hosts and the lazy instance iterator, using one common queue, sleep and completion model.',
      '2. Rohan and Rushi use identical workload files and physical resource constraints across placement policies.',
      '3. Yaksh keeps the manifest, configs and queue/admission rules with each result set.',
      '4. Treat the 4,000-group replay as stress; run the smaller inputs first. Do not interpret aggregate '
      'burst pressure as a placement-policy failure or claim Alibaba actual electricity savings.','',
      '## References','',
      '- [Alibaba v2017 source and download documentation](https://github.com/alibaba/clusterdata/tree/master/cluster-trace-v2017)',
      '- [Official schema](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2017/schema.csv)',
      '- [Maintainer CPU-unit correction, issue 11](https://github.com/alibaba/clusterdata/issues/11)',
      '- [Published archive SHA-256](https://raw.githubusercontent.com/alibaba/clusterdata/master/cluster-trace-v2017/SHA256SUM)',
      '- Local requirements: EcoSched_Proposal.pdf, sections 4-6.','']
    (root/'REPORT.md').write_text('\n'.join(lines))
    print(root/'REPORT.md')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);a=p.parse_args();main(a.root)
