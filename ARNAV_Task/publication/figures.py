"""Figures consume the Phase 1 adapter and existing D5 tables, never simulations."""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from .style import plt, POLICY_COLORS, SKEW_COLORS, LABELS, CURVE_LABELS
from ARNAV_Task.analysis.artifacts import POLICIES, CURVES, SIZES, PRIMARY, SKEWS
from ARNAV_Task.analysis.metrics import METRICS
from ARNAV_Task.dashboard.data_service import pareto_frontier
from ARNAV_Task.dashboard.constants import EXTRA_UNITS


@dataclass
class Figure:
    identifier: str
    section: str
    title: str
    caption: str
    sources: list
    data: object
    figure: object
    units: dict = field(default_factory=dict)
    filters: dict = field(default_factory=dict)
    evidence: str = "active research evidence"


def legend(fig, policies=POLICIES):
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(facecolor=POLICY_COLORS[p], edgecolor="#35434d", label=LABELS[p]) for p in policies],
               loc="outside lower center", ncol=len(policies), frameon=False)


def metric_grid(a, identifier, title, metrics, labels, *, line=False):
    rows = a.filter_runs()
    fig, axes = plt.subplots(len(metrics), len(CURVES), figsize=(11.8, 3.0 * len(metrics) + .5),
                             squeeze=False, layout="constrained")
    for i, (metric, label) in enumerate(zip(metrics, labels)):
        for j, curve in enumerate(CURVES):
            ax = axes[i, j]
            for n, policy in enumerate(POLICIES):
                values = [next(r for r in rows if (r['workload_groups'], r['power_curve'], r['policy']) ==
                               (size, curve, policy)).get(metric) for size in SIZES]
                y = [np.nan if value is None else value for value in values]
                if line:
                    ax.plot(SIZES, y, marker=("o", "s", "^", "D")[n], color=POLICY_COLORS[policy],
                            linewidth=1.8, markeredgecolor="#35434d", markersize=5)
                else:
                    ax.bar(np.arange(len(SIZES)) + (n-1.5)*.19, y, width=.18,
                           color=POLICY_COLORS[policy], edgecolor="#35434d", linewidth=.4)
            ax.set(xticks=SIZES if line else range(len(SIZES)), xticklabels=[f"{s:,}" for s in SIZES], xlabel="Task groups",
                   ylabel=label, title=CURVE_LABELS[curve] if i == 0 else None)
            ax.set_ylim(bottom=0)
            ax.grid(axis="y")
    fig.suptitle(title, fontsize=13)
    legend(fig)
    data = [{k: r.get(k) for k in ("workload_groups", "power_curve", "policy", *metrics)} for r in rows]
    return Figure(identifier, "research", title,
        f"{title}. All four policies use identical inputs and controls within each workload/curve condition. "
        "Each mark is one offline deterministic run; curves are separate sensitivity cases. Missing values are omitted. "
        + ("P95 values remain individual-run quantiles and are never averaged. " if 'p95_wait_s' in metrics else '')
        + ("Reservation pressure is a modeled overload/SLA proxy, not observed SLA violations." if 'overload_host_time_fraction' in metrics else ''),
        ["BASELINE_Comparison/reports/summaries.json", "RAW_Alibaba/reports/summaries.json"], data, fig,
        {metric: METRICS[metric][0] if metric in METRICS else EXTRA_UNITS.get(metric,"unavailable") for metric in metrics},
        {"policies":list(POLICIES),"workload_groups":list(SIZES),"power_curves":list(CURVES)})


def research_figures(a, config):
    yield metric_grid(a, "R01_energy", "Modeled energy across the active experiment matrix", ["energy_kwh"], ["Modeled energy (kWh)"])
    yield metric_grid(a, "R02_efficiency_sensitivity", "Workload-size and power-curve sensitivity",
                     ["energy_kwh", "wh_per_completed_instance"], ["Modeled energy (kWh)", "Wh / completed instance"], line=True)
    pairs = a.comparisons(primary_only=True)
    matrix = np.array([[next(r['energy_reduction_pct'] for r in pairs if r['workload_groups']==s and r['power_curve']==c)
                        for c in CURVES] for s in SIZES])
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.3), layout="constrained", width_ratios=[1.25, 1])
    for j, c in enumerate(CURVES):
        axes[0].bar(np.arange(3)+(j-1)*.24, matrix[:, j], width=.23, label=CURVE_LABELS[c],
                    color=["#0072B2", "#E69F00", "#009E73"][j], edgecolor="#35434d", linewidth=.4)
    axes[0].axhline(0, color="#17212b", lw=.8)
    axes[0].set(xticks=range(3), xticklabels=[f"{s:,}" for s in SIZES], xlabel="Task groups", ylabel="Energy reduction (%)")
    axes[0].legend(fontsize=7, frameon=False)
    limit = max(abs(matrix.min()), abs(matrix.max()))
    im=axes[1].imshow(matrix, cmap="BrBG", vmin=-limit, vmax=limit, aspect="auto")
    axes[1].set(xticks=range(3), xticklabels=["HPE", "Huawei", "Quanta"], yticks=range(3),
                yticklabels=[f"{s:,}" for s in SIZES], ylabel="Task groups")
    for i in range(3):
        for j in range(3):
            axes[1].text(j, i, f"{matrix[i,j]:+.2f}%", ha="center", va="center", color="white" if abs(matrix[i,j])>.65*limit else "#17212b")
    fig.colorbar(im, ax=axes[1], label="Energy reduction (%)", shrink=.85)
    fig.suptitle("Primary ablation: CPU/memory placement relative to CPU LR-MMT", fontsize=12)
    yield Figure("R03_primary_savings", "research", "Nine-condition primary energy comparison",
        "Energy reduction = 100 × (CPU LR-MMT − CPU/memory LR-MMT) / CPU LR-MMT. Positive values mean savings; "
        "negative values mean higher energy. The heatmap is centered at zero. No distinct power curves are pooled.",
        ["BASELINE_Comparison/reports/proposal_pairs.csv"], pairs, fig, {"energy_reduction_pct":"percent"})
    fig, ax=plt.subplots(figsize=(7.4,4.3),layout="constrained")
    points=[]
    for n,c in enumerate(CURVES):
        curve=a.curve_data['curves'][c]; load=np.linspace(0,1,len(curve['watts']))
        ax.plot(load*100,curve['watts'],marker=("o","s","^")[n],label=CURVE_LABELS[c],linewidth=1.8)
        points.extend(dict(power_curve=c,load_fraction=float(x),watts=y) for x,y in zip(load,curve['watts']))
    ax.set(xlabel="SPECpower target CPU load (%)",ylabel="Whole-server AC power (W)",xlim=(0,100),ylim=(0,None))
    ax.grid();ax.legend(frameon=False)
    yield Figure("R04_specpower", "research", "SPECpower surrogate power curves",
        "Published SPECpower points used by the existing piecewise-linear model. The same selected whole-server curve "
        "is mapped to each sampled host using requested CPU / host capacity, without core-count or memory scaling. "
        "This is a surrogate sensitivity model, not Alibaba hardware calibration.", ["ecosched/power_curves.json"],points,fig,
        {"load_fraction":"fraction","watts":"W"})
    focus=config['focus_workload_groups']
    gap=[r for r in a.d5_tables['pair_energy_gap'] if r['workload_groups']==focus]
    terms=("on_running_work_kwh","on_without_work_kwh","load_dependent_kwh","wakeups_kwh","longer_run_kwh","extra_transition_kwh")
    names=("On, running work","On, no work","Load-dependent","Wake transitions","Longer run / sleep","Other transitions")
    fig,axes=plt.subplots(1,3,figsize=(11.8,4.1),layout="constrained")
    for ax,c in zip(axes,CURVES):
        r=next(r for r in gap if r['power_curve']==c);v=[r[t] for t in terms]
        ax.barh(range(len(terms)),v,color=["#B35806" if x>0 else "#018571" for x in v])
        ax.set(yticks=range(len(terms)),yticklabels=names,xlabel="Memory-aware minus CPU LR-MMT (kWh)",title=CURVE_LABELS[c])
        ax.invert_yaxis();ax.axvline(0,color="#17212b",lw=.7);ax.text(.98,.02,f"Net: {r['energy_change_kwh']:+.3f} kWh",transform=ax.transAxes,ha="right")
    fig.suptitle(f"D5 energy accounting: {focus:,} task groups",fontsize=13)
    yield Figure("R05_d5_energy_decomposition","research","D5 decomposition of the largest-workload penalty",
        "Signed D5 energy-gap components; positive means additional consumption, the opposite sign to energy reduction. "
        "Components explain the net penalty without assigning energy to individual resource-skew categories.",
        ["RUSHI_Task/reports/pair_energy_gap.csv"],gap,fig,{t:"kWh" for t in terms},{"workload_groups":focus},"D5 mechanism analysis")
    for args in (
        ("R06_active_hosts","Active-host footprint",["mean_active_hosts","peak_active_hosts"],["Mean active hosts","Peak active hosts"]),
        ("R07_waiting","Waiting-time outcomes",["mean_wait_s","p95_wait_s"],["Mean wait (s)","P95 wait (s)"]),
        ("R08_migrations","Migration activity and pause",["migrations","migration_pause_instance_seconds"],["Migration transfers","Pause (instance-seconds)"]),
        ("R09_pressure_fragmentation","Reservation pressure and fragmentation",["overload_host_time_fraction","mean_fragmentation_index"],["Reservation pressure (fraction)","Fragmentation index (fraction)"]),
        ("R10_stranded_capacity","Stranded resource capacity",["cpu_stranded_by_memory_core_seconds","memory_stranded_by_cpu_unit_seconds"],["CPU stranded (core-seconds)","Memory stranded (unit-seconds)"])):
        yield metric_grid(a,*args)
    objectives=("mean_wait_s","overload_host_time_fraction","migrations","mean_active_hosts")
    titles=("Mean wait (s)","Reservation pressure (fraction)","Migration transfers","Mean active hosts")
    fig,axes=plt.subplots(4,3,figsize=(11.8,11),layout="constrained");data=[]
    for i,(objective,title) in enumerate(zip(objectives,titles)):
        for j,c in enumerate(CURVES):
            frame=pareto_frontier(pd.DataFrame(a.filter_runs(sizes=[focus],curves=[c])),y=objective)
            efficient=frame[frame.pareto_efficient.fillna(False)].sort_values('energy_kwh')
            axes[i,j].plot(efficient.energy_kwh,efficient[objective],color="#687681",ls="--",lw=.8,zorder=1)
            for n,r in frame.iterrows():
                axes[i,j].scatter(r.energy_kwh,r[objective],color=POLICY_COLORS[r.policy],marker=("o","s","^","D")[POLICIES.index(r.policy)],
                                  edgecolors="#17212b",s=65,zorder=2)
                data.append(dict(workload_groups=focus,power_curve=c,policy=r.policy,objective=objective,
                                 energy_kwh=r.energy_kwh,value=r[objective],pareto_efficient=bool(r.pareto_efficient)))
            axes[i,j].set(xlabel="Modeled energy (kWh)",ylabel=title,title=CURVE_LABELS[c] if i==0 else None)
            axes[i,j].grid()
    fig.suptitle(f"Descriptive energy–performance trade-offs · {focus:,} task groups",fontsize=13);legend(fig)
    yield Figure("R11_pareto_tradeoffs","research","Condition-specific descriptive Pareto comparisons",
        "Each panel minimizes modeled energy and its displayed performance objective, within one identical workload/curve. "
        "Dashed lines connect non-dominated observed policies only. They do not imply a continuous feasible frontier, global optimality, "
        "statistical significance or scheduler superiority. Reservation pressure is a modeled SLA proxy.",
        ["BASELINE_Comparison/reports/summaries.json","ARNAV_Task/dashboard/data_service.py"],data,fig,
        {'energy_kwh':'kWh',**dict(zip(objectives,["seconds","fraction","transfers","hosts"]))},{"workload_groups":focus})
    fig,axes=plt.subplots(1,2,figsize=(10,3.8),layout="constrained");mix=a.d5_tables['workload_mix']
    for ax,percent in zip(axes,(False,True)):
        bottom=np.zeros(len(SIZES))
        for skew in SKEWS:
            values=[next(r for r in mix if r['workload_groups']==s)[skew+('_pct' if percent else '_instances')] for s in SIZES]
            ax.bar(range(3),values,bottom=bottom,color=SKEW_COLORS[skew],label=skew.replace('_',' ').title(),edgecolor="#35434d",linewidth=.4);bottom+=values
        ax.set(xticks=range(3),xticklabels=[f"{s:,}" for s in SIZES],xlabel="Task groups",ylabel="Instances (%)" if percent else "Individual instances")
    axes[1].legend(frameon=False);fig.suptitle("Alibaba workload resource-skew composition",fontsize=13)
    yield Figure("R12_resource_composition","research","Resource-skew composition",
        "Instance counts and percentages use the existing D5 resource-skew classification. The 250-group sample has no CPU-heavy instances; "
        "this population zero does not imply zero waiting or migration outcomes for that absent category.",
        ["RUSHI_Task/reports/workload_mix.csv"],mix,fig,{"instances":"instances","share":"percent"},evidence="D5 mechanism analysis")
    c=config['resource_skew_curve'];out=a.resource_skew(curves=[c]);metrics=('mean_wait_s','p95_wait_s','migrated_pct')
    fig,axes=plt.subplots(3,3,figsize=(11.8,8.5),layout="constrained")
    for i,s in enumerate(SIZES):
        for j,metric in enumerate(metrics):
            ax=axes[i,j]
            for n,p in enumerate(PRIMARY):
                values=[next((r.get(metric) for r in out if r['workload_groups']==s and r['policy']==p and r['task_type']==sk),None) for sk in SKEWS]
                ax.bar(np.arange(3)+(n-.5)*.32,[np.nan if v is None else v for v in values],width=.3,color=POLICY_COLORS[p],edgecolor="#35434d",linewidth=.4)
            for category_index,category in enumerate(SKEWS):
                if not any(r['workload_groups']==s and r['task_type']==category for r in out):
                    ax.text(category_index,.5,"No observations",transform=ax.get_xaxis_transform(),rotation=90,ha="center",va="center",fontsize=8)
            ax.set(xticks=range(3),xticklabels=[s.replace('_','\n') for s in SKEWS],ylabel=f"{s:,} groups\n"+{'mean_wait_s':'Mean wait (s)','p95_wait_s':'P95 wait (s)','migrated_pct':'Migrated instances (%)'}[metric])
            ax.grid(axis="y")
    fig.suptitle(f"Resource-skew outcomes · {CURVE_LABELS[c]}",fontsize=13);legend(fig,PRIMARY)
    yield Figure("R13_resource_outcomes","research","Supported resource-skew outcomes",
        "Only the two primary policies have D5 category outcomes. The selected curve is shown without pooling other curves; full outcomes "
        "are exported in T12. Absent categories are labeled No observations. P95 values are category-specific quantiles, never averaged; no category energy is assigned.",
        ["RUSHI_Task/reports/outcomes_by_task_type.csv"],out,fig,{'mean_wait_s':'seconds','p95_wait_s':'seconds','migrated_pct':'percent'},
        {'power_curve':c,'policies':list(PRIMARY)},"D5 mechanism analysis")
    fig,axes=plt.subplots(3,3,figsize=(11.8,8.1),layout="constrained");data=[];sources=[]
    keys=('powered_hosts','mean_cpu_of_hosts_running_work','mean_memory_of_hosts_running_work')
    for j,c in enumerate(CURVES):
        for p in PRIMARY:
            recording=a.d5_recordings[(focus,c,p)];t=recording['time_series'];data.append(dict(power_curve=c,policy=p,workload_groups=focus,time_series=t))
            sources.append(f"RUSHI_Task/reports/runs/{c}/{focus}/{p}.json")
            for i,key in enumerate(keys):
                axes[i,j].step(np.array(t['time_s'])/3600,t[key],where="post",color=POLICY_COLORS[p],lw=1.1)
                axes[i,j].set(xlabel="Simulation time (h)",ylabel=("Powered hosts","Busy-host CPU (fraction)","Busy-host memory (fraction)")[i],title=CURVE_LABELS[c] if i==0 else None)
                axes[i,j].grid()
    fig.suptitle(f"Previously recorded D5 host samples · {focus:,} groups",fontsize=13);legend(fig,PRIMARY)
    # Obtain actual recording paths from the adapter's source inventory, avoiding layout assumptions.
    sources=sorted(p for p in a.source_paths if p.startswith('RUSHI_Task/reports/runs/'))
    yield Figure("R14_offline_host_timelines","research","Offline sampled host-state timelines",
        "Previously recorded D5 simulation samples, not live Kafka measurements. Busy-host means condition on hosts running work; "
        "sampled step lines are descriptive recordings and cannot reconstruct continuous event-level occupancy or energy.",sources,data,fig,
        {'time_s':'seconds','powered_hosts':'hosts','mean_cpu_of_hosts_running_work':'fraction','mean_memory_of_hosts_running_work':'fraction'},
        {'workload_groups':focus},"D5 mechanism analysis")
    arithmetic=a.d5_tables['placement_score_arithmetic'];decisions=[r for r in a.d5_tables['placement_decisions'] if r['workload_groups']==focus]
    fig,axes=plt.subplots(1,2,figsize=(11.8,4),layout="constrained")
    for n,key in enumerate(('power_score_advantage_of_busy_server','balance_penalty_typical_busy_server','balance_penalty_empty_server')):
        axes[0].bar(np.arange(3)+(n-1)*.23,[next(r for r in arithmetic if r['power_curve']==c)[key] for c in CURVES],width=.22,
                    color=('#0072B2','#E69F00','#009E73')[n],label=('Busy-host power advantage','Busy-host balance penalty','Empty-host balance penalty')[n])
    axes[0].set(xticks=range(3),xticklabels=['HPE','Huawei','Quanta'],ylabel="Placement score component (dimensionless)")
    axes[0].legend(fontsize=7,frameon=False,loc='upper center',bbox_to_anchor=(.5,-.13),ncol=1)
    for n,p in enumerate(PRIMARY):
        axes[1].bar(np.arange(3)+(n-.5)*.32,[next(r for r in decisions if r['power_curve']==c and r['policy']==p)['disagreements_own_pick_less_loaded_pct'] for c in CURVES],
                    width=.3,color=POLICY_COLORS[p],edgecolor="#35434d",linewidth=.4,label=LABELS[p])
    axes[1].set(xticks=range(3),xticklabels=['HPE','Huawei','Quanta'],ylabel="Own pick less loaded when rules disagree (%)");axes[1].legend(fontsize=7,frameon=False)
    fig.suptitle("D5 placement-score arithmetic and recorded choices",fontsize=13)
    yield Figure("R15_d5_placement","research","D5 explanation of memory-balance placement",
        "Left: D5's fixed illustrative score arithmetic, not an experiment rerun or fitted causal model. Right: actual disagreement "
        "outcomes from recorded primary-policy placement decisions at the largest workload. The balance term can outweigh the power preference for busy hosts.",
        ["RUSHI_Task/reports/placement_score_arithmetic.csv","RUSHI_Task/reports/placement_decisions.csv"],
        {'arithmetic':arithmetic,'decisions':decisions},fig,{'score':'dimensionless','disagreement':'percent'},evidence="D5 mechanism analysis")


def streaming_figures(p4,p5,history=None):
    source4="ARNAV_Task/reports/phase4_verification.json";source5="ARNAV_Task/reports/phase5_verification.json"
    workloads=p4['integration']['workloads'];sizes=[r['verification']['size'] for r in workloads]
    fig,axes=plt.subplots(1,2,figsize=(10,3.8),layout="constrained")
    for ax,key,label in zip(axes,('average_instances_per_s','elapsed_wall_s'),('Distinct instances / s','Session wall time (s)')):
        values=[r['metrics'][key] for r in workloads];ax.bar(range(len(sizes)),values,color="#82A9D0",edgecolor="#35434d",linewidth=.5)
        ax.set(xticks=range(len(sizes)),xticklabels=[f"{s:,}" for s in sizes],xlabel="Task groups",ylabel=label)
        for i,v in enumerate(values):ax.annotate(f"{v:,.2f}",(i,v),xytext=(0,3),textcoords='offset points',ha="center",fontsize=8)
        ax.margins(y=.18)
    fig.suptitle("Kafka fast-mode replay · one ARM64 laptop, one broker",fontsize=12)
    yield Figure("S01_fast_replay","streaming","Measured fast-mode Kafka replay",
        "Complete authentic workloads replayed as fast as possible in the Phase 4 environment. Throughput uses distinct persisted instances / "
        "recorded session wall time. Wall time includes the controller's completion/verification lifecycle; it is not an isolated verifier benchmark. "
        "These single-session observations do not establish distributed scalability or scheduler performance.",[source4],
        [{k:r['metrics'][k] for k in ('size','expected','distinct_count','elapsed_wall_s','average_instances_per_s','replay_id')} for r in workloads],fig,
        {'elapsed_wall_s':'seconds','average_instances_per_s':'instances/second'},evidence="Kafka transport verification")
    duplicate=p4['integration']['tests']['duplicate_redelivery']['verification'];restart=p4['integration']['tests']['consumer_restart']
    fig,axes=plt.subplots(1,2,figsize=(11,3.8),layout="constrained")
    before=next(r['verification'] for r in workloads if r['verification']['replay_id']==duplicate['replay_id'])
    for i,(label,key) in enumerate((('Accepted deliveries','consumed_deliveries'),('Distinct instances','distinct_instances'),('Duplicate deliveries','duplicate_deliveries'))):
        axes[0].bar(np.arange(2)+(i-1)*.23,[before[key],duplicate[key]],width=.22,label=label,color=('#82A9D0','#32B5A4','#D2A56A')[i])
    axes[0].set(xticks=[0,1],xticklabels=['Initial complete replay','After redelivery'],ylabel="Recorded messages / instances");axes[0].legend(frameon=False,fontsize=7)
    axes[1].axis('off');cells=[]
    for r in workloads:
        v=r['verification'];cells.append([f"{v['size']:,}",f"{v['distinct_instances']:,}",str(v['invalid_messages']),str(v['sequence_gaps']), 'Passed' if v['passed'] else 'Failed'])
    table=axes[1].table(cellText=cells,colLabels=['Groups','Distinct','Invalid','Gaps','Integrity'],loc='center',cellLoc='center');table.auto_set_font_size(False);table.set_fontsize(8);table.scale(1,1.7)
    axes[1].set_title(f"Restart: {restart['persisted_before_restart']:,} persisted before interruption\nFull verification passed after resumption",fontsize=9)
    fig.suptitle("Idempotent persistence and complete event-level integrity",fontsize=12)
    yield Figure("S02_integrity_recovery","streaming","Duplicate delivery and restart integrity",
        "At-least-once Kafka delivery with idempotent SQLite persistence: exact redelivery increases delivery counts while unique instances remain unchanged. "
        "The adjacent table reports full event-level verification, not count-only checks. Restart evidence is from the separately recorded interruption test.",
        [source4],{'initial':before,'redelivery':duplicate,'restart':restart,'complete':[r['verification'] for r in workloads]},fig,
        {'counts':'messages or distinct instances as labeled'},evidence="Kafka transport verification")
    browser=p5['browser_full_250_at_600x'];obs=browser['observations'];fig,axes=plt.subplots(1,2,figsize=(11,3.8),layout="constrained")
    for key,label,color in [('confirmed','Confirmed published','#82A9D0'),('distinct_count','Distinct persisted','#32B5A4')]:
        axes[0].plot([o['elapsed_wall_s'] for o in obs],[o[key] for o in obs],marker='o',ms=3,label=label,color=color)
    axes[0].set(xlabel="Session elapsed wall time (s)",ylabel="Observed events / instances");axes[0].legend(frameon=False)
    axes[1].plot([o['elapsed_wall_s'] for o in obs],[o['last_arrival']/3600 for o in obs],marker='o',ms=3,color='#0072B2')
    axes[1].set(xlabel="Session elapsed wall time (s)",ylabel="Latest consumed logical arrival (h)")
    for ax in axes:ax.grid()
    fig.suptitle(f"Browser-driven timed replay · {browser['final_verification']['size']} groups at {browser['speed']}×",fontsize=12)
    yield Figure("S03_browser_timed_replay","streaming","Recorded browser-driven timed replay",
        "Actual sampled browser observations from Phase 5; markers denote observations, connecting lines are guides. "
        "Producer acknowledgement counters are flushed in batches and can temporarily trail consumer observations. Logical source time is distinct "
        "from elapsed wall time. This timed replay is not combined with fast-mode throughput measurements.",[source5],browser,fig,
        {'elapsed_wall_s':'seconds','last_arrival':'logical seconds','counts':'instances'},evidence="Dashboard demonstration evidence")
    if history:
        fig,axes=plt.subplots(2,2,figsize=(11,6.8),layout="constrained");start=history['started_at']
        t=history['throughput'];off=history['offset_history'];d=history['demand']
        axes[0,0].bar([r['wall_second']-start for r in t],[r['count'] for r in t],width=.9,color='#32B5A4')
        axes[0,0].set(xlabel="Wall-clock bucket start relative to session (s)",ylabel="Distinct arrivals / 1 s bucket")
        for key,label,col in [('session_lag','Session lag','#009E73'),('topic_lag','Topic lag','#0072B2')]:
            if off and key in off[0]:axes[0,1].scatter([r['wall_second']-start for r in off],[r[key] for r in off],s=8,label=label,color=col)
        axes[0,1].set(xlabel="Observed wall time relative to session (s)",ylabel="Observed Kafka offsets behind");axes[0,1].legend(frameon=False)
        for ax,key,label in [(axes[1,0],'cpu','Offered CPU (requested core sum)'),(axes[1,1],'memory','Offered memory (normalized-unit sum)')]:
            ax.bar([r['logical_bucket']/3600 for r in d],[r[key] for r in d],width=.23,color='#82A9D0')
            ax.set(xlabel="Logical arrival interval start (h; 900 s bins)",ylabel=label)
        for ax in axes.flat:ax.grid(axis='y')
        fig.suptitle(f"Recorded transport observations · complete {history['size']:,}-group browser replay",fontsize=12)
        yield Figure("S04_recorded_transport_history","streaming","Measured throughput, lag and offered arrival demand",
            "Frozen read-only SQLite observations for the fully verified Phase 5 browser replay. Throughput counts distinct persisted instances in "
            "one-second wall-clock buckets; omitted buckets are unobserved, not interpolated. Lag uses actual consumer and broker offsets at observation time. "
            "Demand sums requests from arriving instances over logical 900-second intervals; it is not allocated resources or utilization.",
            [source5,'ARNAV_Task/reports/publication/streaming_observations.json'],history,fig,
            {'throughput':'distinct instances per one-second bucket','lag':'Kafka offsets','cpu':'requested cores','memory':'normalized units'},
            {'replay_id':history['replay_id']},"Kafka transport verification")
