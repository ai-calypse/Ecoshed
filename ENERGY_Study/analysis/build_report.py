"""Render all outcomes without selecting only successful scenarios."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
reports = ROOT / "reports"
with (reports / "paired_comparisons.csv").open(newline="", encoding="utf-8") as f:
    pairs = list(csv.DictReader(f))
with (reports / "confidence_intervals.csv").open(newline="", encoding="utf-8") as f:
    intervals = list(csv.DictReader(f))
validation = json.loads((reports / "verification.json").read_text())
heldout = [p for p in pairs if p["phase"] == "heldout"]
witness = [p for p in pairs if p["phase"] == "mechanism"]
accepted = sum(p["accepted"] == "True" for p in heldout)
positive = sum(float(p["energy_reduction_pct"]) > 0 for p in heldout)
lines = [
    "# Energy-first placement: mechanism and robustness study", "",
    "**HISTORICAL SYNTHETIC DIAGNOSTIC — not Alibaba project evidence.** "
    "See [ALIBABA_REPORT.md](ALIBABA_REPORT.md) for the active trace-derived experiment.", "",
    "This is a new **synthetic-only** study. It does not read Yaksh's cleaned data, "
    "does not replace the original 36-run results, and does not claim raw Alibaba replay.", "",
    f"**{validation['verified_runs']} runs, {validation['verified_pairs']} paired comparisons and "
    f"{validation['verified_pointwise_intervals']} pointwise intervals independently verified.** "
    "The study completed 80,664 individual synthetic instance replays.", "",
    "## What changed", "",
    "The new CPU-oriented and memory-aware variants use incremental steady-state power as the first "
    "placement objective. The memory-aware variant uses normalized CPU/memory imbalance only to break "
    "power ties (rounded at one nanowatt to remove floating-point noise). The CPU variant breaks those "
    "ties by CPU occupancy. Both inherit the same LR/MMT controller, migration guard, cooldown, admission "
    "and physical resource constraints. The original weighted-balance policy is preserved and appears "
    "as a development-only reference alongside the original CPU-oriented policy.", "",
    "Instrumentation adds exact event-interval energy components, powered-idle time, stranded CPU/memory "
    "threshold measures, request-specific blocked-capacity probes, fragmentation, p95 wait and p95 "
    "turnaround. Tests verify that instrumentation preserves every metric from Brave's original engine.", "",
    "## Designed mechanism case", "",
    "Four requests arrive together on hosts of capacity `(100 CPU, 1 memory)`: "
    "`a=(72,.20)`, `b=(72,.80)`, `c=(14,.01)`, `d=(15,.30)`. Total CPU is 173 "
    "and total memory 1.31, so at least two hosts are necessary. A feasible packing is "
    "`{a,d}=(87,.50)` and `{b,c}=(86,.81)`. The memory-aware power tie-break recovers "
    "that two-host solution; the CPU tie-break uses three. Both resource fractions remain below 0.9.", "",
    "This is an intentionally constructed unit mechanism, not a random workload sample. "
    "The controller is disabled **for both policies only in this case**, with zero wake latency "
    "and immediate sleep to isolate placement. It establishes existence of a saving opportunity, "
    "not broad production performance or LR-controller performance.", "",
    "| Curve | CPU-oriented kWh | Memory-aware kWh | Reduction | Preset budgets pass |",
    "|---|---:|---:|---:|---|",
]
for row in witness:
    lines.append(f"| {row['curve']} | {float(row['cpu_energy_kwh']):.6f} | "
                 f"{float(row['memory_energy_kwh']):.6f} | {float(row['energy_reduction_pct']):+.3f}% | {row['accepted']} |")
lines += ["", "## Held-out generated workloads", "",
    "Five requested resource mixes, two lifetime bands and eight held-out seeds give 80 paired "
    "base comparisons. Every episode has 160 independent instances on 16 synthetic hosts. "
    "The same workload bytes, runtime and simulator settings are used for each pair. The synthetic "
    "catalog and probabilities are explicit in `workloads.py`; the scarce-CPU mix is illustrative "
    "and is not a reconstruction of the original Alibaba distribution.", "",
    f"Energy decreased in **{positive}/80** base held-out pairs. **{accepted}/80** met all preset "
    "practical energy, waiting, migration and pressure budgets. These criteria are stronger than "
    "simply observing any positive energy difference.", "",
    "| Mix | Lifetimes | Episodes | Mean reduction | 95% pointwise bootstrap interval | All budgets pass |",
    "|---|---|---:|---:|---:|---:|",
]
for row in intervals:
    if row["phase"] == "heldout":
        lines.append(f"| {row['mix']} | {row['lifetime']} | {row['episodes']} | "
                     f"{float(row['mean_energy_reduction_pct']):+.3f}% | "
                     f"[{float(row['ci_lower_pct']):+.3f}, {float(row['ci_upper_pct']):+.3f}]% | {row['accepted_episodes']}/8 |")
lines += ["", "Positive reductions mean less modeled energy; negative values mean more energy. "
    "The mixed/short result is encouraging within this generator, but its confidence interval does "
    "not establish that the practical 1% saving threshold is exceeded at the population level. "
    "Other base-case intervals include zero. The original general energy-saving claim remains unestablished.", "",
    "## Complete power and assumption sensitivity", "",
    "Each row uses the same eight mixed/long held-out seeds. Power-curve changes reuse the same "
    "workloads; other cases vary exactly one setting from the HPE baseline. These rows are "
    "correlated sensitivity checks, not additional independent production observations.", "",
    "| Curve / setting | Mean reduction | 95% pointwise bootstrap interval | All budgets pass |",
    "|---|---:|---:|---:|",
]
for row in intervals:
    if row["phase"] != "heldout":
        label = row["curve"] if row["phase"] == "power_sensitivity" else row["scenario"]
        lines.append(f"| {label} | {float(row['mean_energy_reduction_pct']):+.3f}% | "
                     f"[{float(row['ci_lower_pct']):+.3f}, {float(row['ci_upper_pct']):+.3f}]% | {row['accepted_episodes']}/8 |")
lines += ["", "The HPE mixed/long base case uses 60-second control, 64 GiB per normalized memory "
    "unit, 125 MB/s migration bandwidth, a 60-second idle timeout, 5-W sleep and 10-second wake latency. "
    "The full matrix is retained, including adverse outcomes. A favorable 300-second sensitivity "
    "result is not a reason to retune the policy on these held-out cases; any selected revision "
    "would require a new untouched evaluation set.", "",
    "## Protocol and interpretation", "",
    "Development seeds are 11–13; held-out seeds are 101–108. No policy parameter search or "
    "selection was performed. Source/config hashes and the entire plan were locally snapshotted "
    "before execution in `reports/frozen_protocol.json`; this is not an external preregistration. "
    "Each pointwise 95% interval resamples paired episode reductions 2,000 times with bootstrap "
    "seed 560. Tasks are not treated as independent samples. The eight generated episodes "
    "support inference only within the specified synthetic generator. The 24 intervals are "
    "exploratory and have no family-wise or false-discovery correction.", "",
    "Preset per-episode acceptance: at least 1% energy reduction; no rejected/unfinished work; "
    "mean and p95 wait increase no greater than 5% or a 1-second floor; migration increase no "
    "greater than 10% or a one-migration floor; pressure-proxy increase no greater than 0.01 "
    "absolute. The pressure proxy is not observed SLA failures. Meeting these synthetic budgets "
    "does not establish acceptable behavior for an actual production service.", "",
    "The residual fragmentation index compares pooled free normalized host-units with "
    "co-located balanced residual fit, considering powered hosts only. Stranded threshold metrics "
    "use >=90% utilization in one resource and <=50% in the other. Probe metrics integrate "
    "free CPU on hosts that could fit a catalog request's CPU but not its memory. All diagnostics "
    "use reservations, including wake/migration reservations, rather than measured usage. They "
    "describe different aspects of fragmentation and need not improve together.", "",
    "## What this supports", "",
    "There is a verified mechanism by which CPU/memory-aware tie-breaking can reduce host count "
    "and modeled energy without sacrificing the preset budgets. Held-out evidence shows that "
    "benefits depend on workload shape, task duration, power curve and controller assumptions. "
    "It does not support unconditional savings, measured electricity savings or an Alibaba "
    "production claim. Direct raw-trace replay with independently prepared windows and calibrated "
    "migration assumptions remains a separate required step.", "",
    "## Reproduce", "", "```sh", "python -m unittest discover -s ENERGY_Study/tests -v",
    "python -m ENERGY_Study.run", "python -m ENERGY_Study.verify",
    "python ENERGY_Study/analysis/build_report.py", "```", "",
    "Review all numeric outcomes in [paired_comparisons.csv](reports/paired_comparisons.csv), "
    "[confidence_intervals.csv](reports/confidence_intervals.csv), "
    "[runs.csv](reports/runs.csv) and [verification.json](reports/verification.json).", "",
]
(ROOT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(ROOT / "REPORT.md")
