"""Verify every fixed ablation and report gains and performance tradeoffs."""
from collections import Counter
import itertools
import json
from pathlib import Path
from RAW_Alibaba.data import verified_manifest, PACKAGE
from RAW_Alibaba.extract import digest
from RAW_Alibaba.run import write_csv
from .run import HERE, source_hashes


def main():
    protocol = json.loads((HERE / "config.json").read_text())
    manifest = verified_manifest()
    rows = [json.loads(p.read_text()) for p in (HERE / "reports/runs").rglob("summary.json")]
    key = lambda r: (r["workload_groups"], r["power_curve"], r["policy"])
    expected = set(itertools.product(manifest["config"]["workload_group_counts"],
        manifest["config"]["power_curves"], protocol["policies"]))
    assert len(rows) == len(expected) and set(map(key, rows)) == expected
    original = {key(r): r for r in json.loads((HERE.parent / "RAW_Alibaba/reports/summaries.json").read_text())}
    index = {key(r): r for r in rows}
    hashes = source_hashes()
    exact_metrics = ("energy_j", "mean_wait_s", "p95_wait_s", "migrations", "mean_active_hosts",
                     "overload_host_time_fraction", "completed_instances", "stop_time_s")
    for row in rows:
        assert row["source_sha256"] == hashes
        assert row["manifest_sha256"] == digest(PACKAGE / "manifest.json")
        assert row["validation"]["passed"] and not row["synthetic_workload"]
        assert not row["uses_yaksh_prepared_inputs"]
        assert not row["rejected_instances"] and not row["unfinished_instances"]
        workload = next(x for x in manifest["workloads"] if x["task_groups"] == row["workload_groups"])
        assert row["completed_instances"] == workload["instances"]
        if row["policy"].startswith("energy_first"):
            assert all(row[m] == original[key(row)][m] for m in exact_metrics), key(row)
    limits = protocol["success_limits"]
    comparisons = []
    for r in sorted(rows, key=key):
        paired = "payback_cpu" if r["policy"].startswith("payback") else "energy_first_cpu"
        for reference in dict.fromkeys(("energy_first_cpu", paired)):
            ref = index[(r["workload_groups"], r["power_curve"], reference)]
            savings = 100*(ref["energy_kwh"]-r["energy_kwh"])/ref["energy_kwh"]
            mean_limit = max(limits["wait_absolute_floor_s"], ref["mean_wait_s"]*limits["mean_wait_relative_increase"])
            p95_limit = max(limits["wait_absolute_floor_s"], ref["p95_wait_s"]*limits["p95_wait_relative_increase"])
            ok = (r["mean_wait_s"]-ref["mean_wait_s"] <= mean_limit
                  and r["p95_wait_s"]-ref["p95_wait_s"] <= p95_limit
                  and r["overload_host_time_fraction"]-ref["overload_host_time_fraction"] <= limits["pressure_absolute_increase"])
            comparisons.append(dict(workload_groups=r["workload_groups"], power_curve=r["power_curve"],
                policy=r["policy"], reference=reference, energy_kwh=r["energy_kwh"],
                energy_saving_pct=savings, energy_win=savings > 0,
                passes_performance_limits=ok, qualified_win=savings > 0 and ok,
                mean_wait_s=r["mean_wait_s"], p95_wait_s=r["p95_wait_s"],
                pressure_fraction=r["overload_host_time_fraction"], migrations=r["migrations"],
                mean_active_hosts=r["mean_active_hosts"]))
    out = HERE / "reports"
    write_csv(out / "comparison.csv", comparisons)
    (out / "summaries.json").write_text(json.dumps(sorted(rows,key=key), indent=2)+"\n")
    validation = dict(passed=True, runs=len(rows), baseline_exact_reproductions=18,
        per_curve_runs=dict(Counter(r["power_curve"] for r in rows)),
        total_completed_instance_replays=sum(r["completed_instances"] for r in rows),
        identical_manifest_sha256=digest(PACKAGE / "manifest.json"),
        source_sha256=hashes, evaluation_role=protocol["evaluation_role"])
    (out / "validation.json").write_text(json.dumps(validation,indent=2)+"\n")
    lines = ["# Fixed algorithm ablation on unchanged raw Alibaba samples", "",
        "These are in-sample development comparisons, not held-out evidence or proof of universal savings. "
        "The 64-host pool, requests, task-create releases, multiplicity, individual observed durations, "
        "simulation settings, and input hashes are unchanged. Each SPEC curve runs separately in a fresh simulator.", "",
        "## Aggregate results", "", "| Policy | Energy wins vs original CPU / 9 | Wins within performance limits / 9 |",
        "|---|---:|---:|"]
    for policy in protocol["policies"]:
        group = [r for r in comparisons if r["policy"] == policy and r["reference"] == "energy_first_cpu"]
        lines.append(f"| {policy} | {sum(r['energy_win'] for r in group)} | {sum(r['qualified_win'] for r in group)} |")
    lines += ["", "Performance limits fixed before runs: mean and p95 waiting may each rise by at most "
        "max(1 second, 5% of baseline); overload-proxy host-time fraction may rise by at most 0.01. "
        "This proxy is requested CPU/memory pressure, not a measured application SLA.", "",
        "## All energy outcomes", "", "Positive percentages save energy relative to the original CPU policy.", "",
        "| Curve | Groups | Original memory | Compact memory | Payback CPU | Payback memory | Payback + compact memory |",
        "|---|---:|---:|---:|---:|---:|---:|"]
    for size, curve in itertools.product(manifest["config"]["workload_group_counts"],manifest["config"]["power_curves"]):
        vals = []
        for policy in protocol["policies"][1:]:
            c = next(r for r in comparisons if (r["workload_groups"],r["power_curve"],r["policy"],r["reference"]) == (size,curve,policy,"energy_first_cpu"))
            vals.append(f"{c['energy_saving_pct']:+.4f}%" + (" *" if not c["passes_performance_limits"] else ""))
        lines.append(f"| {curve} | {size} | " + " | ".join(vals) + " |")
    lines += ["", "* Exceeds at least one fixed performance limit; see comparison.csv for actual metrics.", "",
        "## Fair CPU/memory comparison with the same payback controller", "",
        "| Memory policy | Energy wins vs payback CPU / 9 | Wins within performance limits / 9 |", "|---|---:|---:|"]
    for policy in ("payback_memory","payback_compact_memory"):
        group = [r for r in comparisons if r["policy"] == policy and r["reference"] == "payback_cpu"]
        lines.append(f"| {policy} | {sum(r['energy_win'] for r in group)} | {sum(r['qualified_win'] for r in group)} |")
    lines += ["", "## Changes and limitations", "",
        "1. Compact packing keeps incremental modeled watts as the primary objective; power ties favor "
        "a small product of remaining CPU and memory capacity, rather than equal CPU/memory utilization.",
        "2. A migration payback gate compares staying versus moving over the unchanged 300-second control "
        "interval. It accounts for source/destination power, duplicate reservations during copying, "
        "wakeup, the 60-second source idle timeout, and sleep. Projected steady benefit must exceed "
        "1.2 times transient cost. Tasks younger than 60 seconds are not moved. Source-group moves are accepted "
        "or rejected together, preserving transactional evacuation; rejected proposals leave no migration locks.",
        "3. The gate uses current requests and elapsed age only. It assumes current tasks stay for the "
        "projection horizon; future completions and arrivals are unknown. It may reject pressure-relief "
        "moves that do not pay back. This is a heuristic, not a guarantee or an established novelty claim.", "",
        "All 54 runs completed and conserved offered work; 18 unmodified baseline runs exactly reproduce "
        "the previous results on energy, waiting, migrations, host counts, pressure and stop time. "
        "Every candidate and adverse outcome is retained. No per-case winning policy is selected.", "",
        "The source archive's legacy published compressed checksum does not match; gzip/member integrity "
        "checks and raw-member corroboration passed, as documented in RAW_Alibaba. This is batch-only "
        "requested-resource simulation with task-create release, not the entire production cluster or measured "
        "hardware energy. A claim of consistent improvement still needs untouched Alibaba time windows/samples "
        "with the algorithm and settings fixed before evaluation.", "",
        "Reproduce from the repository root:", "", "```powershell",
        "python -m unittest POLICY_Improvement.test_policies -v",
        *[f"python -m POLICY_Improvement.run --curve {c}" for c in manifest["config"]["power_curves"]],
        "python -m POLICY_Improvement.report", "```", ""]
    (out / "REPORT.md").write_text("\n".join(lines))
    print(json.dumps(validation,indent=2))
    print("\n".join(lines[:18]))


if __name__ == "__main__":
    main()
