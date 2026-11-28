"""Academic tables with lossless CSV and presentation-only display rounding."""
from dataclasses import dataclass, field
import csv
import json
import subprocess

from ARNAV_Task.analysis.artifacts import POLICIES, PRIMARY, CURVES, SIZES, SKEWS
from ARNAV_Task.analysis.metrics import METRICS, definitions


@dataclass
class Table:
    identifier: str
    title: str
    rows: list
    sources: list
    caption: str
    units: dict = field(default_factory=dict)
    evidence: str = "active research evidence"


def contributions(root):
    """Git proves paths/authorship, not each person's unrecorded collaboration."""
    rows=[]
    for owner, paths, scope in (
        ('Yaksh Gandhi',['YAKSH_Task'],'Historical D1 workload package; not active-study inputs'),
        ('Brave Desai',['BRAVE_Task','RAW_Alibaba','ecosched','BASELINE_Comparison'],'D2 simulator/power; active raw preparation and D4 integration'),
        ('Rohan Rane',['ROHAN_Task'],'D3 scheduling policies; inspect author vs owner attribution'),
        ('Rushi Jhala',['RUSHI_Task'],'D5 analysis only; same-job extension excluded'),
    ):
        result=subprocess.run(['git','-C',str(root),'log','--all','--format=%H|%an|%s','--',*paths],capture_output=True,text=True)
        records=[line.split('|',2) for line in result.stdout.splitlines() if line]
        rows.append(dict(owner=owner,area=scope,paths=', '.join(paths),
                         commits='; '.join(r[0] for r in records),git_authors='; '.join(sorted({r[1] for r in records})),
                         evidence='Git path history; directory ownership does not establish commit authorship',
                         source='git log --all -- '+ ' '.join(paths)))
    rows.append(dict(owner='Arnav Desai',area='D6 final package: adapters, dashboard, recovered inputs, Kafka, publication exports',
                     paths='ARNAV_Task/',commits='Uncommitted D6 working tree',git_authors='Not committed',
                     evidence='Current implementation and Phase 1–5 verification receipts; no D6 commit claimed',source='ARNAV_Task/README.md'))
    return rows


def academic_tables(a, p3, p4, p5, validation, current_tests=None):
    raw='RAW_Alibaba/prepared/manifest.json';config='RAW_Alibaba/config.json';baseline='BASELINE_Comparison/reports/summaries.json'
    runs=a.filter_runs();pairs=a.comparisons(primary_only=True)
    def table(identifier,title,rows,sources,caption,**kw):
        return Table(identifier,title,rows,sources,caption,**kw)
    yield table('T01_dataset','Dataset characteristics',[
        dict(characteristic=k,value=v) for k,v in {
            'Dataset':a.manifest['data_source'],'Source':a.manifest['archive']['source_url'],
            'Archive bytes':a.manifest['archive']['archive_bytes'],'Archive SHA-256':a.manifest['archive']['archive_sha256'],
            'Sampling seed':a.raw_config['seed'],'Host pool':a.raw_config['host_count'],
            'Logical arrival window (s)':a.raw_config['window_end_s']-a.raw_config['window_start_s'],
            'Runtime model':a.raw_config['runtime_model'],'Arrival model':a.raw_config['arrival_model'],
            'Raw rows independently verified':p3['independent_validation']['passed'],
            'Exact prepared outputs recovered':p3['prepared_outputs_match_active_study']}.items()],
        [raw,config,'ARNAV_Task/reports/phase3_verification.json'],
        'Active raw-derived Alibaba v2017 package. Individual observed durations support offline simulation; arrival replay events do not expose future durations.')
    yield table('T02_workloads','Workload groups and individual instances',a.manifest['workloads'],[raw],
        'Groups preserve original instance multiplicity. Skew counts are population counts, not category-specific performance outcomes.')
    yield table('T03_experiment_matrix','Active experiment matrix',[
        dict(workload_groups=r['workload_groups'],power_curve=r['power_curve'],policy=r['policy'],source_summary=r['source_individual_summary']) for r in runs],
        [baseline],'Exactly 36 unique outcomes: four approved policies × three workloads × three separately evaluated SPECpower curves.')
    settings={**{k:v for k,v in a.raw_config.items() if k not in ('simulation','policies','power_curves')},
              **a.raw_config['simulation'],**a.policy_config['simulation_overrides'],**a.policy_config['policy']}
    yield table('T04_simulator_configuration','Fixed simulator and sampling configuration',
        [dict(parameter=k,value=v) for k,v in settings.items()],[config,'ROHAN_Task/config/default.json'],
        'Fixed simulation assumptions. Memory-unit conversion and independent per-transfer bandwidth are modeling assumptions, not Alibaba measurements.')
    yield table('T05_power_models','SPECpower model configuration',[
        dict(power_curve=c,**a.curve_data['curves'][c],mapping=a.curve_data['mapping']) for c in CURVES],['ecosched/power_curves.json'],
        'Separate measured SPECpower curves drive a CPU-request-based surrogate, with no RAM/core-count scaling. Raw watt-point arrays are retained.')
    descriptions={
        'first_fit':'Powered-host-first first fit; common FIFO admission and CPU/memory feasibility.',
        'best_fit':'Fullest feasible CPU host, preferring powered hosts; no consolidation controller.',
        'lr_mmt':'Common LR overload detector and MMT selector; CPU-oriented incremental-power placement.',
        'lr_mmt_memory':'Same LR/MMT controller; incremental-power score plus CPU/memory imbalance penalty.'}
    yield table('T06_policies','Active scheduling policy definitions',[
        dict(policy=p,label=a.config['policies'][p],definition=descriptions[p],source='ROHAN_Task/README.md') for p in POLICIES],
        ['ROHAN_Task/README.md','ROHAN_Task/config/default.json','BASELINE_Comparison/reports/REPORT.md'],
        'The primary controlled ablation changes placement only. Additional baselines are included without restoring historical policies.')
    def select(fields):return [{k:r.get(k) for k in ('workload_groups','power_curve','policy',*fields,'source_individual_summary')} for r in runs]
    yield table('T07_energy','Complete modeled energy results',select(['energy_kwh']),[baseline],
        'Modeled kWh for each active outcome. Each row is a separate deterministic simulation, not measured production energy.',units={'energy_kwh':'kWh'})
    yield table('T08_efficiency','Energy per completed individual instance',select(['energy_kwh','completed_instances','wh_per_completed_instance']),[baseline],
        'Wh per completed instance = 1000 × modeled kWh / completed individual instances; task groups are not the denominator.',units={'energy_kwh':'kWh','completed_instances':'instances','wh_per_completed_instance':'Wh/instance'})
    yield table('T09_primary_comparisons','Primary energy and performance comparisons',pairs,
        ['BASELINE_Comparison/reports/proposal_pairs.csv'],
        'Energy reduction = 100 × (baseline − candidate) / baseline; CPU LR-MMT is baseline. Positive means savings. Conditions match exactly.',
        units={'energy_reduction_pct':'percent','mean_wait_delta_s':'seconds','p95_wait_delta_s':'seconds','pressure_delta_percentage_points':'percentage points'})
    yield table('T10_performance','Hosts, migrations and waiting outcomes',
        select(['mean_active_hosts','peak_active_hosts','migrations','migration_pause_instance_seconds','mean_wait_s','p95_wait_s','rejected_instances','unfinished_instances']),
        [baseline],'P95 values are individual-run quantiles; no averaging across runs. Pause is accumulated instance-seconds, not elapsed experiment overhead.',
        units={k:METRICS[k][0] for k in ('mean_active_hosts','peak_active_hosts','migrations','migration_pause_instance_seconds','mean_wait_s','p95_wait_s','rejected_instances','unfinished_instances')})
    yield table('T11_pressure_fragmentation','Reservation pressure, fragmentation and stranded capacity',
        select(['overload_host_time_fraction','mean_fragmentation_index','cpu_stranded_by_memory_core_seconds','memory_stranded_by_cpu_unit_seconds']),[baseline],
        'Reservation pressure is a modeled overload/SLA proxy, not application SLA violations. Stranded capacity has time-integrated units.',
        units={'overload_host_time_fraction':'fraction','mean_fragmentation_index':'fraction','cpu_stranded_by_memory_core_seconds':'core-seconds','memory_stranded_by_cpu_unit_seconds':'normalized-unit-seconds'})
    skew=a.resource_skew();skew_rows=[]
    for s in SIZES:
        for c in CURVES:
            for p in PRIMARY:
                for category in SKEWS:
                    r=next((r for r in skew if (r['workload_groups'],r['power_curve'],r['policy'],r['task_type'])==(s,c,p,category)),None)
                    skew_rows.append({**(r or dict(workload_groups=s,power_curve=c,policy=p,task_type=category,
                        **{k:None for k in ('instances','mean_wait_s','p95_wait_s','delayed_pct','placed_on_asleep_or_waking_server_pct','migrated_pct')})),
                                      'observation_status':'Observed' if r else 'No observations'})
    yield table('T12_resource_skew','Supported resource-skew outcomes',skew_rows,['RUSHI_Task/reports/outcomes_by_task_type.csv'],
        'Only primary policies have category outcomes: 48 observed rows plus six explicit absent-category rows. Missing outcomes remain empty, never artificial zeros. '
        'CPU-heavy means (CPU / median host CPU) / (memory / median host memory) > 2; memory-heavy means this ratio < 0.5; otherwise balanced.',
        units={'mean_wait_s':'seconds','p95_wait_s':'seconds','migrated_pct':'percent'},evidence='D5 mechanism analysis')
    broker=p4['broker'];yield table('T13_kafka_configuration','Tested Kafka infrastructure',[
        dict(parameter=k,value=broker[k]) for k in ('version','image','architecture','immutable_index_digest','arm64_manifest_digest','heap','container_memory_limit_bytes','topic')],
        ['ARNAV_Task/reports/phase4_verification.json','ARNAV_Task/docker-compose.yml'],
        'One ARM64 broker/controller in KRaft mode, one partition and replication factor one; localhost-only external listener. Not a high-availability deployment.',evidence='Kafka transport verification')
    replay=[]
    for r in p4['integration']['workloads']:
        m=r['metrics'];v=r['verification'];replay.append(dict(mode='Phase 4 fast',size=v['size'],replay_id=v['replay_id'],speed=0,
            distinct_instances=v['distinct_instances'],groups=v['groups'],elapsed_wall_s=m['elapsed_wall_s'],average_instances_per_s=m['average_instances_per_s'],
            complete=v['complete'],integrity_passed=v['passed'],invalid=v['invalid_messages'],sequence_gaps=v['sequence_gaps']))
    b=p5['browser_full_250_at_600x'];v=b['final_verification']
    replay.append(dict(mode='Phase 5 browser timed',size=v['size'],replay_id=v['replay_id'],speed=b['speed'],distinct_instances=v['distinct_instances'],
        groups=v['groups'],elapsed_wall_s=b['elapsed_wall_s'],average_instances_per_s=b['average_instances_per_s'],complete=v['complete'],integrity_passed=v['passed'],invalid=v['invalid_messages'],sequence_gaps=v['sequence_gaps']))
    yield table('T14_kafka_replays','Complete replay and event-level verification results',replay,
        ['ARNAV_Task/reports/phase4_verification.json','ARNAV_Task/reports/phase5_verification.json'],
        'Fast and timed runs are explicitly separate. Session durations are controller lifecycle measurements, not isolated verifier time or scheduler benchmark time.',
        units={'elapsed_wall_s':'seconds','average_instances_per_s':'distinct instances/second'},evidence='Kafka transport verification')
    recovery=[]
    for name in ('duplicate_redelivery','consumer_restart'):
        t=p4['integration']['tests'][name];v=t['verification']
        recovery.append(dict(test=name,**{k:v[k] for k in ('replay_id','consumed_deliveries','distinct_instances','duplicate_deliveries','invalid_messages','sequence_gaps','passed')},
            persisted_before_restart=t.get('persisted_before_restart'),offset_before_restart=t.get('offset_before_restart')))
    yield table('T15_recovery','Duplicate delivery and interruption recovery',recovery,['ARNAV_Task/reports/phase4_verification.json'],
        'Exact duplicates increase accepted deliveries without increasing unique-instance counts. Consumer restart resumes from durable offsets after SQLite persistence.',evidence='Kafka transport verification')
    test_rows=[
        dict(evidence='Phase 4 recorded tests',check='Distinct passing tests',value=p4['test_results']['total_distinct_tests_passed']),
        dict(evidence='Phase 5 recorded tests',check='Distinct passing tests',value=p5['test_results']['total_distinct_passed']),
        dict(evidence='Numerical reconciliation',check='Grouped artifact checks passed',value=validation['numerical']['checks_passed']),
        dict(evidence='Numerical reconciliation',check='Active experiment outcomes',value=validation['numerical']['active_outcomes']),
        dict(evidence='Numerical reconciliation',check='Rejected instances',value=validation['numerical']['rejected_instances']),
        dict(evidence='Numerical reconciliation',check='Unfinished instances',value=validation['numerical']['unfinished_instances']),
        dict(evidence='Phase 3 independent reconstruction',check='Raw-row validation passed',value=p3['independent_validation']['passed']),
        dict(evidence='Phase 3 independent reconstruction',check='Hosts independently checked',value=p3['independent_validation']['checked_hosts'])]
    test_sources=['ARNAV_Task/reports/phase4_verification.json','ARNAV_Task/reports/phase5_verification.json','ARNAV_Task/reports/phase3_verification.json','ARNAV_Task/reports/artifact_validation.json']
    if current_tests:
        test_rows.extend(dict(evidence='Phase 6 executed regression',check=k.replace('_',' '),value=v) for k,v in current_tests['counts'].items())
        test_sources.append('ARNAV_Task/reports/publication/test_results.json')
    yield table('T16_recorded_validation','Recorded validation and test coverage',test_rows,test_sources,
        'Historical receipts are labeled by phase and not added together. Phase 6 totals, when present, use the frozen executed-test receipt; ordinary discovery skips broker tests which are counted only in the explicit integration run.')
    prov=validation['provenance'];status=[dict(layer='Numerical results',status=validation['numerical']['passed'],evidence='36 active outcomes cross-checked against raw aggregate and individual summaries'),
        dict(layer='Source-code fingerprint consistency',status=prov['source_code_fingerprints']['consistent'],evidence='Recorded simulator and preparation source hashes agree; this is distinct from historical metadata identity'),
        dict(layer='Reconstructed prepared-output identity',status=p3['prepared_outputs_match_active_study'],evidence=p3['input_manifest_sha256']),
        dict(layer='Historical metadata lineage',status='UNRESOLVED',evidence='Three expected historical versions not recovered'),
        dict(layer='Compressed archive identity',status='Active archive match; legacy archive differs',evidence=a.manifest['archive']['archive_sha256']),
        dict(layer='End-to-end simulation replication in D6',status=False,evidence='No benchmark simulations rerun')]
    status.extend(dict(layer=r['id'],status='UNRESOLVED',evidence='Current: '+r['current_sha256']+'; expected: '+', '.join(r['expected_sha256'])) for r in prov['discrepancies'])
    yield table('T17_provenance','Layered reproducibility and provenance status',status,
        ['ARNAV_Task/reports/artifact_validation.json','ARNAV_Task/reports/phase3_verification.json','ARNAV_Task/reports/provenance_reconciliation.md'],
        'Prepared-file byte identity, raw-member identity and numerical consistency do not repair three missing historical metadata versions. Full lineage remains unresolved.')
    yield table('T18_contributions','Individual contributions and Git evidence',contributions(a.root),
        ['docs/EcoSched_Proposal.pdf','ARNAV_Task/README.md','RUSHI_Task/README.md','ROHAN_Task/README.md','YAKSH_Task/README.md'],
        'Current ownership is checked against path-specific Git history, not the original proposal ownership table. Git authors and directory owners are distinguished. D6 is uncommitted.')
    # The underlying D5 evidence is reused verbatim; no new attribution methodology.
    for ident,name in [('T19_d5_energy_accounting','pair_energy_gap'),('T20_d5_placement','placement_decisions'),
                       ('T21_d5_controller','controller_diagnostics'),('T22_d5_score_arithmetic','placement_score_arithmetic')]:
        yield table(ident,'D5 '+name.replace('_',' '),a.d5_tables[name],[f'RUSHI_Task/reports/{name}.csv'],
            'Existing D5 analysis, restricted to the active study. Energy change in D5 means candidate minus baseline; positive indicates a penalty, unlike energy reduction.',evidence='D5 mechanism analysis')


def cell(value, *, display=False):
    if value is None:return '—' if display else ''
    if isinstance(value,(dict,list)):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
    if isinstance(value,float) and display:return f'{value:,.6g}'
    return str(value)


def latex_escape(value):
    translation={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_',
                 '{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}
    # Permit long hashes/paths to wrap without changing their visible contents.
    import re
    return ''.join(''.join(translation.get(c,c) for c in token) if len(token)<24 else
                   r'\allowbreak{}'.join(''.join(translation.get(c,c) for c in token[i:i+12]) for i in range(0,len(token),12))
                   for token in re.split(r'(\s+)',str(value)))


def write_table(table, directory):
    """CSV retains original scalar precision; human formats round display only."""
    directory.mkdir(parents=True,exist_ok=True)
    columns=list(dict.fromkeys(k for r in table.rows for k in r))
    paths=[];path=directory/(table.identifier+'.csv')
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=columns,lineterminator='\n');w.writeheader()
        w.writerows({k:cell(r.get(k)) for k in columns} for r in table.rows)
    paths.append(path)
    headers=[k.replace('_',' ').title()+(f' ({table.units[k]})' if k in table.units else '') for k in columns]
    md=lambda value:cell(value,display=True).replace('|',r'\|').replace('\n','<br>')
    text=f'# {table.title}\n\n{table.caption}\n\n'+'| '+' | '.join(headers)+' |\n'+'| '+' | '.join('---' for _ in columns)+' |\n'
    text+=''.join('| '+' | '.join(md(r.get(k)) for k in columns)+' |\n' for r in table.rows)
    text+='\nSources: '+', '.join(f'`{p}`' for p in table.sources)+'.\n'
    path=directory/(table.identifier+'.md');path.write_text(text,encoding='utf-8');paths.append(path)
    # Wide tables are split into panels with repeated condition/identity columns.
    keys=[k for k in ('workload_groups','power_curve','policy','task_type') if k in columns]
    others=[k for k in columns if k not in keys];width=max(1,7-len(keys))
    panels=[keys+others[i:i+width] for i in range(0,len(others),width)] or [columns]
    tex='% Requires longtable, booktabs, array; tables are split into manageable column panels.\n'
    for panel in panels:
        spec=''.join(r'>{\raggedright\arraybackslash}p{'+f'{.80/len(panel):.3f}'+r'\linewidth}' for _ in panel)
        tex+=r'\begin{longtable}{'+spec+'}\n'+r'\caption{'+latex_escape(table.title)+'}\\\n'+r'\toprule'+'\n'
        tex+=' & '.join(latex_escape(headers[columns.index(k)]) for k in panel)+r' \\'+'\n'+r'\midrule\endhead'+'\n'
        tex+=''.join(' & '.join(latex_escape(cell(r.get(k),display=True)) for k in panel)+r' \\'+'\n' for r in table.rows)
        tex+=r'\bottomrule\end{longtable}'+'\n'
    tex+='% '+table.caption+'\n% Sources: '+', '.join(table.sources)+'\n'
    path=directory/(table.identifier+'.tex');path.write_text(tex,encoding='utf-8');paths.append(path)
    return paths
