"""Proposal-only comparison: LR-MMT CPU versus memory placement, with FF/BF baselines."""
from collections import Counter
import html
import itertools
import json
from pathlib import Path
from RAW_Alibaba.data import verified_manifest, PACKAGE
from RAW_Alibaba.extract import digest
from RAW_Alibaba.run import source_hashes, write_csv

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "BASELINE_Comparison/reports"
POLICIES = {"first_fit": "First Fit", "best_fit": "Best Fit", "lr_mmt": "CPU-oriented LR-MMT",
            "lr_mmt_memory": "LR-MMT + CPU/memory-aware placement (proposed)"}
CURVES = {"hpe_dl360_gen9": "HPE DL360 Gen9", "huawei_rh2288h_v3": "Huawei RH2288H V3",
          "quanta_d51b_2u": "QuantaGrid D51B-2U"}


def load_verified():
    manifest = verified_manifest()
    path = ROOT / "RAW_Alibaba/reports/summaries.json"
    rows = json.loads(path.read_text())
    expected = set(itertools.product(manifest["config"]["workload_group_counts"],
                   manifest["config"]["power_curves"], manifest["config"]["policies"]))
    keys = [(r["workload_groups"], r["power_curve"], r["policy"]) for r in rows]
    if len(keys) != len(expected) or set(keys) != expected:
        raise ValueError("Original raw result grid incomplete or duplicated")
    fingerprints = source_hashes()
    sha = digest(PACKAGE / "manifest.json")
    for r in rows:
        count = next(x["instances"] for x in manifest["workloads"] if x["task_groups"] == r["workload_groups"])
        if (r["source_sha256"] != fingerprints or r["manifest_sha256"] != sha
            or r["config"] != manifest["config"]["simulation"]
            or not r["validation"]["passed"] or r["synthetic_workload"]
            or r["uses_yaksh_prepared_inputs"] or r["data_source"] != "fresh_user_archive_alibaba_v2017"
            or r["completed_instances"] != count or r["completed_task_groups"] != r["workload_groups"]
            or r["rejected_instances"] or r["unfinished_instances"] or r["capacity_violation_host_seconds"]):
            raise ValueError("Source, inputs, assumptions or completion checks failed")
    selected = [r for r in rows if r["policy"] in POLICIES]
    if len(selected) != 36:
        raise ValueError("Expected 36 proposal/baseline outcomes")
    return manifest, selected


def graph(rows):
    ix = {(r["workload_groups"],r["power_curve"],r["policy"]):r for r in rows}
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="420" viewBox="0 0 1120 420" role="img" aria-labelledby="title desc">',
        '<title id="title">Proposal: energy change relative to CPU-oriented LR-MMT</title>',
        '<desc id="desc">Only CPU/memory-aware placement changes. Negative percentages save energy; positive percentages consume more. Three sample sizes for each separate server curve.</desc>',
        '<rect width="1120" height="420" fill="white"/><g font-family="Arial, sans-serif" fill="#172a3a">',
        '<text x="25" y="30" font-size="22" font-weight="bold">Proposed placement: energy change versus CPU-oriented LR-MMT</text>',
        '<text x="25" y="55" font-size="14">Same Alibaba samples, 64-host pool and LR/MMT controller. Negative = savings; positive = more energy.</text>']
    for panel,(curve,label) in enumerate(CURVES.items()):
        x = 25+365*panel
        svg.append(f'<text x="{x}" y="95" font-size="17" font-weight="bold">{html.escape(label)}</text>')
        zero = x+115
        for tick in (0,5,10,15):
            tx=zero+tick*11
            svg.append(f'<line x1="{tx}" y1="118" x2="{tx}" y2="320" stroke="#d9e2e9"/><text x="{tx}" y="343" text-anchor="middle" font-size="12">{tick:+d}%</text>')
        for n,size in enumerate((250,1000,4000)):
            cpu,mem=ix[(size,curve,"lr_mmt")],ix[(size,curve,"lr_mmt_memory")]
            delta=100*(mem["energy_kwh"]/cpu["energy_kwh"]-1)
            y=143+n*65
            left=zero+min(0,delta)*11
            width=abs(delta)*11
            color="#b53c40" if delta>0 else "#087f8c"
            svg.append(f'<text x="{x}" y="{y+18}" font-size="13">{size:,} groups</text><rect x="{left}" y="{y}" width="{width}" height="27" fill="{color}"/><text x="{zero+max(0,delta)*11+5}" y="{y+19}" font-size="12">{delta:+.3f}%</text>')
    svg += ['<text x="25" y="390" font-size="13">Energy improves in 4/9 cases; larger workloads show a 10.96–14.56% penalty. This is in-sample simulation evidence.</text>','</g></svg>']
    (OUT / "largest_sample_energy.svg").write_text("\n".join(svg),encoding="utf-8")
    (OUT / "proposal_energy_change.svg").write_text("\n".join(svg),encoding="utf-8")


def main():
    manifest,rows=load_verified()
    OUT.mkdir(parents=True,exist_ok=True)
    ix={(r["workload_groups"],r["power_curve"],r["policy"]):r for r in rows}
    paired=[]
    all_pairs=[]
    totals=[]
    for curve in CURVES:
        for size in (250,1000,4000):
            cpu,mem=ix[(size,curve,"lr_mmt")],ix[(size,curve,"lr_mmt_memory")]
            paired.append(dict(power_curve=curve,workload_groups=size,cpu_energy_kwh=cpu["energy_kwh"],
                proposed_energy_kwh=mem["energy_kwh"],proposed_energy_increase_pct=100*(mem["energy_kwh"]/cpu["energy_kwh"]-1),
                proposed_energy_win=mem["energy_kwh"]<cpu["energy_kwh"],
                cpu_mean_wait_s=cpu["mean_wait_s"],proposed_mean_wait_s=mem["mean_wait_s"],
                cpu_p95_wait_s=cpu["p95_wait_s"],proposed_p95_wait_s=mem["p95_wait_s"],
                cpu_migrations=cpu["migrations"],proposed_migrations=mem["migrations"],
                cpu_mean_active_hosts=cpu["mean_active_hosts"],proposed_mean_active_hosts=mem["mean_active_hosts"],
                cpu_pressure_fraction=cpu["overload_host_time_fraction"],proposed_pressure_fraction=mem["overload_host_time_fraction"]))
            for candidate,baseline in itertools.product(POLICIES,repeat=2):
                a,b=ix[(size,curve,candidate)],ix[(size,curve,baseline)]
                all_pairs.append(dict(power_curve=curve,workload_groups=size,policy=candidate,baseline=baseline,
                    energy_kwh=a["energy_kwh"],energy_saving_pct=100*(b["energy_kwh"]-a["energy_kwh"])/b["energy_kwh"],
                    mean_wait_delta_s=a["mean_wait_s"]-b["mean_wait_s"],p95_wait_delta_s=a["p95_wait_s"]-b["p95_wait_s"],
                    migrations=a["migrations"],pressure_delta_percentage_points=100*(a["overload_host_time_fraction"]-b["overload_host_time_fraction"])))
        cpu_total=sum(ix[(s,curve,"lr_mmt")]["energy_kwh"] for s in (250,1000,4000))
        for policy in POLICIES:
            total=sum(ix[(s,curve,policy)]["energy_kwh"] for s in (250,1000,4000))
            totals.append(dict(power_curve=curve,policy=policy,energy_kwh_sum=total,energy_increase_vs_cpu_lr_mmt_pct=100*(total/cpu_total-1)))
    write_csv(OUT / "proposal_pairs.csv",paired)
    write_csv(OUT / "all_pairwise_comparisons.csv",all_pairs)
    write_csv(OUT / "per_curve_totals.csv",totals)
    (OUT / "summaries.json").write_text(json.dumps(rows,indent=2)+"\n")
    lines=["# Active proposal comparison", "", "The active evaluation is **CPU-oriented LR-MMT versus LR-MMT + CPU/memory-aware placement**. "
        "First Fit and Best Fit are additional baselines. Later controller/placement extensions are excluded. "
        "Previous extension experiments are historical, outside this comparison.", "",
        "## Same data and simulation", "", "This reuses 36 validated raw-Alibaba outcomes with no new simulations or data changes. "
        "Each of three curves is evaluated separately for 250 / 1,000 / 4,000 groups (16,534 / 68,457 / 378,285 instances). "
        "All policies use the same raw-derived requests, task-create releases, original multiplicity, individual observed durations, "
        "64-host pool, FIFO admission, power model and sleep assumptions. LR detection, MMT selection and controller parameters "
        "are identical in the primary pair; only placement scoring differs. The memory-aware implementation adds a weighted "
        "CPU/memory imbalance term to normalized incremental power. CPU-oriented placement still enforces memory capacity.", "",
        "## Primary energy comparison", "", "Positive change means the proposed memory-aware placement uses MORE energy; negative means savings.", "",
        "| Curve | Groups | CPU LR-MMT kWh | Proposed kWh | Proposed energy change |", "|---|---:|---:|---:|---:|"]
    for p in paired:
        lines.append(f"| {CURVES[p['power_curve']]} | {p['workload_groups']:,} | {p['cpu_energy_kwh']:.6f} | {p['proposed_energy_kwh']:.6f} | {p['proposed_energy_increase_pct']:+.4f}% |")
    lines += ["", "![Proposed placement energy change](proposal_energy_change.svg)", "",
        "The proposed variant saves energy in **4/9** cases; CPU-oriented LR-MMT saves energy in **5/9**. "
        "The proposed variant wins all three small cases and the medium Huawei case. It loses the other two medium "
        "cases and all three largest cases. On the largest workloads it uses **10.96–14.56% more energy**.", "",
        "## Per-curve energy totals", "", "These are sums over the same three sample sizes, not a production workload distribution.", "",
        "| Curve | Proposed energy change vs CPU LR-MMT |", "|---|---:|"]
    for t in totals:
        if t["policy"]=="lr_mmt_memory":
            lines.append(f"| {CURVES[t['power_curve']]} | {t['energy_increase_vs_cpu_lr_mmt_pct']:+.3f}% |")
    lines += ["", "## Performance on the largest workload", "", "| Curve | Policy | Mean wait (s) | P95 wait (s) | Migrations | Mean active hosts | Pressure (%) |", "|---|---|---:|---:|---:|---:|---:|"]
    for curve in CURVES:
        for policy in ("lr_mmt","lr_mmt_memory"):
            r=ix[(4000,curve,policy)]
            lines.append(f"| {CURVES[curve]} | {POLICIES[policy]} | {r['mean_wait_s']:.3f} | {r['p95_wait_s']:.1f} | {r['migrations']:,} | {r['mean_active_hosts']:.3f} | {100*r['overload_host_time_fraction']:.3f} |")
    lines += ["", "Memory-aware placement lowers modeled requested-resource pressure and mean waiting on the largest "
        "workload, but keeps more hosts powered. Thus CPU-oriented LR-MMT is better on energy overall in this grid, "
        "not better on every measured outcome. Pressure is a requested-resource proxy, not an observed application SLA.", "",
        "## Additional baselines", ""]
    for curve,label in CURVES.items():
        lines += [f"### {label}", "", "| Policy | 250 groups kWh | 1,000 groups kWh | 4,000 groups kWh |", "|---|---:|---:|---:|"]
        for policy,labelp in POLICIES.items():
            lines.append(f"| {labelp} | " + " | ".join(f"{ix[(s,curve,policy)]['energy_kwh']:.6f}" for s in (250,1000,4000)) + " |")
        lines.append("")
    lines += ["## Verdict and limits", "", "The current implementation does not support a claim of consistent energy reduction "
        "from adding memory-aware placement. The proposal asks when placement helps; the small-workload wins and "
        "energy/pressure tradeoff should be reported alongside losses. This is our batch adaptation of LR-MMT, "
        "not a bit-for-bit external CloudSim reproduction. The deterministic, overlapping samples and curve "
        "sensitivity cases are not independent replications. No generalization or significance claim follows.", "",
        "Power is modeled using requested CPU and whole-server SPEC curves. Background online load, failures and "
        "DAG dependencies are not replayed. Task creation is the modeled release. The legacy archive checksum "
        "mismatch remains documented in RAW_Alibaba; raw member integrity/corroboration is not a publisher checksum match.", "",
        "Rebuild: `python -m BASELINE_Comparison.build`. Source/input hashes and the original 54-run result grid "
        "are checked before selecting these 36 outcomes. All work completes without rejection, unfinished work "
        "or physical capacity violations. Full metrics: summaries.json; primary pairs: proposal_pairs.csv.", ""]
    (OUT / "REPORT.md").write_text("\n".join(lines),encoding="utf-8")
    graph(rows)
    validation=dict(passed=True,active_policies=list(POLICIES),unique_runs=len(rows),
        per_curve_runs=dict(Counter(r["power_curve"] for r in rows)),
        input_manifest_sha256=digest(PACKAGE / "manifest.json"),
        source_summary_sha256=digest(ROOT / "RAW_Alibaba/reports/summaries.json"),
        analysis_source_sha256=digest(Path(__file__)),source_result_grid_verified=54,
        no_new_simulations=True,synthetic_runs=0)
    (OUT / "validation.json").write_text(json.dumps(validation,indent=2)+"\n")
    print(json.dumps(validation,indent=2))


if __name__=="__main__":
    main()
