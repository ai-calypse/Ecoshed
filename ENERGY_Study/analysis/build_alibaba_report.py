"""Render only validated Alibaba-derived results; never use synthetic summaries."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
reports = HERE / "alibaba_reports"
validation = json.loads((reports / "validation.json").read_text(encoding="utf-8"))
rows = json.loads((reports / "summaries.json").read_text(encoding="utf-8"))
if not validation["passed"] or validation["synthetic_runs"]:
    raise ValueError("An Alibaba-only validated matrix is required")
if any(r["synthetic_workload"] or r["data_source"] != "alibaba_v2017_prepared_trace_rows" for r in rows):
    raise ValueError("Generated or unverified data cannot enter the project report")
index = {(r["workload_groups"], r["power_curve"], r["policy"]): r for r in rows}
curves = ("hpe_dl360_gen9", "huawei_rh2288h_v3", "quanta_d51b_2u")
sizes = (250, 1000, 4000)
new_pair_wins = 0
lines = ["# Energy-first scheduler: Alibaba-derived experiment results", "",
    "**Every run in this report uses Alibaba-derived trace records. No artificial workloads "
    "or synthetic workload substitutions are included.** The previous generated-workload study "
    "is historical diagnostic material and is not evidence for this project.", "",
    f"The verified matrix contains **{validation['runs']} runs**, "
    f"**{validation['total_completed_instance_replays']:,} completed instance replays**, and "
    "zero rejected/unfinished instances. HPE, Huawei and Quanta each have the same 12 "
    "combinations, with fresh simulator state and one power curve per run.", "",
    "## Exact data scope", "",
    "Inputs are the existing **prepared Alibaba v2017 package in YAKSH_Task**: a fixed "
    "64-host pool and 250/1,000/4,000 task-group samples, preserving original instance counts, "
    "requests and arrivals. Their declared group-mean observed duration model is unchanged. "
    "The runner verifies input/config hashes against the preparation manifest and requires "
    "original source-row identifiers. It does not invent or rescale jobs.", "",
    "**This is not a fresh replay/preparation of the raw archive.** No raw archive exists locally, "
    "and this environment could not connect to Alibaba's archive download host. The use of "
    "Yaksh's prepared data is explicit in every result. Re-running an independently prepared raw "
    "trace pipeline remains a separate task; these files must not be described as such a replay.", "",
    "## Modeled energy: same full grid under each curve", "",
    "Values are modeled kWh. A positive reduction in the last column means that the energy-first "
    "memory variant beats its energy-first CPU baseline; a negative value means more energy.", "",
    "| Curve | Groups | Original LR-MMT | Original memory-aware | Energy-first CPU | Energy-first memory | New memory reduction vs new CPU |",
    "|---|---:|---:|---:|---:|---:|---:|",
]
for curve in curves:
    for size in sizes:
        a, b, c, d = [index[(size, curve, p)] for p in ("lr_mmt", "lr_mmt_memory", "energy_first_cpu", "energy_first_memory")]
        reduction = 100 * (c["energy_kwh"] - d["energy_kwh"]) / c["energy_kwh"]
        new_pair_wins += reduction > 0
        lines.append(f"| {curve} | {size:,} | {a['energy_kwh']:.6f} | {b['energy_kwh']:.6f} | "
                     f"{c['energy_kwh']:.6f} | {d['energy_kwh']:.6f} | {reduction:+.3f}% |")
lines += ["", f"The energy-first memory variant saved energy in **{new_pair_wins}/9** "
    "paired comparisons against its CPU counterpart. This is the observed outcome, not a "
    "guarantee or a reason to replace the data with favorable generated workloads.", "",
    "## Waiting, migrations and resource use: primary HPE curve", "",
    "| Groups | Policy | Mean wait, s | p95 wait, s | Migrations | Mean powered hosts | Fragmentation index |",
    "|---:|---|---:|---:|---:|---:|---:|",
]
for size in sizes:
    for name in ("energy_first_cpu", "energy_first_memory"):
        r = index[(size, curves[0], name)]
        lines.append(f"| {size:,} | {name} | {r['mean_wait_s']:.3f} | {r['p95_wait_s']:.3f} | "
                     f"{r['migrations']:,} | {r['mean_active_hosts']:.3f} | {r['mean_fragmentation_index']:.4f} |")
lines += ["", "Fragmentation is the instrumented residual-resource index, not an observed hardware "
    "measurement. Waiting includes queueing and wake latency; migration pause is reported separately "
    "in the full summaries. Lower fragmentation alone does not establish lower total energy.", "",
    "## Controls and limits", "",
    "The two original policies and the two energy-first variants all use the same LR/MMT controller, "
    "FIFO admission, physical CPU/memory constraints, sleep/wake settings and full-window-plus-drain "
    "stopping rule. The arrival window is 43,200 seconds, control interval 300 seconds, modeled sleep "
    "5 W, idle timeout 60 seconds and wake latency 10 seconds. Migration assumes 64 GiB per normalized "
    "memory unit and independent 125 MB/s bandwidth; neither is an Alibaba measurement.", "",
    "Three differently sized samples from the same prepared window are not independent random "
    "replications. No synthetic seed bootstrap or independent-window confidence intervals are attached "
    "to these results. These are benchmark outcomes under the stated model, not measured Alibaba "
    "electricity or proof of general production savings.", "",
    "## Validation and reproduction", "",
    "The active runner refuses altered/unverified trace CSVs and has no synthetic fallback. "
    "Per-run checks cover unique outcomes, completion counts, drained reservations, sampled "
    "capacities and per-host/energy-component reconciliation. Full verification checks complete "
    "per-curve coverage and matching input, implementation and assumption fingerprints.", "",
    "```sh", "python -m ENERGY_Study.run", "python -m ENERGY_Study.verify",
    "python ENERGY_Study/analysis/build_alibaba_report.py", "```", "",
    "[Full numeric comparison](alibaba_reports/comparison.csv) · "
    "[Per-run summaries](alibaba_reports/summaries.json) · "
    "[Validation](alibaba_reports/validation.json)", "",
]
(HERE / "ALIBABA_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(HERE / "ALIBABA_REPORT.md")
