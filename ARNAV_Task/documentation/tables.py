"""Document selections over existing adapter tables; display rounding only."""
from .evidence import SHORT, POLICY_SHORT
from ARNAV_Task.analysis.artifacts import SIZES, CURVES, PRIMARY


def report_table(e,name):
    a=e.a
    if name=='workloads':return ['Task groups','Individual instances','Balanced','Memory-heavy','CPU-heavy'],[
        [r['task_groups'],r['instances'],r['instance_resource_skew_counts'].get('balanced',0),r['instance_resource_skew_counts'].get('memory_heavy',0),r['instance_resource_skew_counts'].get('cpu_heavy',0)] for r in a.manifest['workloads']]
    if name=='primary':return ['Groups','Curve','CPU LR-MMT (kWh)','Memory-aware (kWh)','Reduction (%)'],[
        [r['workload_groups'],SHORT[r['power_curve']],f"{r['baseline_energy_kwh']:.6f}",f"{r['energy_kwh']:.6f}",f"{r['energy_reduction_pct']:+.4f}"] for r in a.comparisons(primary_only=True)]
    if name=='efficiency_primary':return ['Groups','Curve','Completed instances','CPU LR-MMT (Wh/instance)','Memory-aware (Wh/instance)'],[
        [s,SHORT[c],a.index[(s,c,PRIMARY[0])]['completed_instances'],*[f"{a.index[(s,c,p)]['wh_per_completed_instance']:.6f}" for p in PRIMARY]] for s in SIZES for c in CURVES]
    if name=='energy_all':return ['Groups','Curve','Policy','Completed','Energy (kWh)','Wh/instance'],[
        [r['workload_groups'],SHORT[r['power_curve']],POLICY_SHORT[r['policy']],r['completed_instances'],f"{r['energy_kwh']:.6f}",f"{r['wh_per_completed_instance']:.6f}"] for r in a.filter_runs()]
    if name=='performance_all':return ['Groups','Curve','Policy','Mean hosts','Peak hosts','Migrations','Pause (instance-s)','Mean wait (s)','P95 wait (s)','Pressure fraction','Fragmentation'],[
        [r['workload_groups'],SHORT[r['power_curve']],POLICY_SHORT[r['policy']],f"{r['mean_active_hosts']:.3f}",r['peak_active_hosts'],r['migrations'],f"{r['migration_pause_instance_seconds']:.2f}",f"{r['mean_wait_s']:.3f}",f"{r['p95_wait_s']:.1f}",f"{r['overload_host_time_fraction']:.6f}",f"{r['mean_fragmentation_index']:.6f}"] for r in a.filter_runs()]
    if name=='skew_all':return ['Groups','Curve','Policy','Category','Instances','Mean wait (s)','P95 wait (s)','Delayed (%)','Migrated (%)'],[
        [r['workload_groups'],SHORT[r['power_curve']],POLICY_SHORT[r['policy']],r['task_type'].replace('_',' '),r['instances'],f"{r['mean_wait_s']:.3f}",f"{r['p95_wait_s']:.1f}",f"{r['delayed_pct']:.3f}",f"{r['migrated_pct']:.3f}"] for r in a.resource_skew()]
    if name=='mechanism':return ['Curve','Net penalty (kWh)','Extra on/work (kWh)','Share of net penalty (%)','Extra on/work (host-h)'],[
        [SHORT[r['power_curve']],f"{r['energy_change_kwh']:.6f}",f"{r['on_running_work_kwh']:.6f}",f"{100*r['on_running_work_kwh']/r['energy_change_kwh']:.4f}",f"{r['on_running_work_hours_change']:.3f}"] for r in a.d5_tables['pair_energy_gap'] if r['workload_groups']==max(SIZES)]
    if name=='streaming':return ['Groups','Distinct instances','Session time (s)','Distinct instances/s','Verification'],[
        [r['verification']['size'],r['verification']['distinct_instances'],f"{r['metrics']['elapsed_wall_s']:.3f}",f"{r['metrics']['average_instances_per_s']:.2f}",'Full event-level pass'] for r in e.receipts[4]['integration']['workloads']]
    if name=='raw_hashes':return ['Original raw member','SHA-256'],[[name,r['sha256']] for name,r in sorted(e.receipts[3]['archive']['source_files'].items())]
    if name=='prepared_hashes':
        r=e.receipts[3]['prepared_outputs']
        return ['Prepared output','Recorded / reconstructed identity'],[[str(k),str(v)] for k,v in r.items()] if isinstance(r,dict) else [[str(r.get('path',r.get('name',''))),str(r)] for r in r]
    if name=='contributions':return ['Member','Implementation credit and repository evidence'],[
        ['Yaksh Gandhi','D1 historical verified data package, sampling and handoff; commits bb176f4, d307337. Historical seed 560 package is not substituted for active inputs.'],
        ['Brave Desai','D2 event simulator and SPECpower model; active RAW_Alibaba preparation, instrumentation and D4 integration. Commit 320da27; PR #1 merged in 938af17.'],
        ['Rohan Rane','D3 policies and shared LR/MMT consolidation, documented in ROHAN_Task. Imported in Brave-authored integration commit 320da27; module ownership and Git authorship differ.'],
        ['Rushi Jhala','D5 observer, accounting, placement diagnostics, skew analysis and research report. Active analysis commit 8fba308; PR #2 merged in b0c4828. Later same-job results excluded.'],
        ['Arnav Desai','D6 artifact/metric validation, dashboard, exact input recovery, Kafka workers/controller/state, live monitoring, publication assets and this final report/deck/runbook. D6 working tree is uncommitted; no commit authorship is invented.']]
    if name=='metrics':return ['Metric','Definition and interpretation'],[
        ['Energy / efficiency','Modeled kWh; 1000 × kWh / completed individual instances.'],
        ['Energy reduction','100 × (baseline − candidate) / baseline; positive means savings.'],
        ['Mean / peak hosts','Time-weighted non-sleeping hosts / maximum non-sleeping hosts.'],
        ['Migration / pause','Completed transfer plans; accumulated pause across instances (instance-seconds).'],
        ['Mean / P95 wait','Initial start minus arrival, including queue and wake delay; separate from migration pause. No averaging P95 quantiles.'],
        ['Reservation pressure','Time above CPU or memory reservation fraction 0.9, divided by host count × simulated duration; modeled SLA proxy.'],
        ['Rejected / unfinished','Instances unable to fit / not completed by the stopping rule; report alongside completed work.'],
        ['Fragmentation','Time-averaged (pooled residual balanced fit − colocated residual fit) / pooled residual fit across powered hosts; zero if no pooled residual fit.'],
        ['Stranded capacity','Time-integrated spare CPU blocked by memory, and spare memory blocked by CPU; core-s and normalized-memory-unit-s.'],
        ['Resource-skew outcome','Category-specific observed instances, waiting quantiles and migrated percentage; primary policies only.']]
    raise ValueError(f'Unknown final-document table: {name}')
