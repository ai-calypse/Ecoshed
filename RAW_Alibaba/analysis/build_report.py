"""Create the complete raw-data report from validated outputs, without filtering losses."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
reports = HERE / "reports"
validation = json.loads((reports / "validation.json").read_text(encoding="utf-8"))
manifest = json.loads((HERE / "prepared/manifest.json").read_text(encoding="utf-8"))
rows = json.loads((reports / "summaries.json").read_text(encoding="utf-8"))
if (not validation["passed"] or validation["synthetic_runs"] or validation["uses_yaksh_prepared_inputs"]
        or any(r["data_source"] != "fresh_user_archive_alibaba_v2017" for r in rows)):
    raise ValueError("Only independently prepared raw-archive results can enter this report")
config = manifest["config"]
index = {(r["workload_groups"], r["power_curve"], r["policy"]): r for r in rows}
names = {"hpe_dl360_gen9": "HPE DL360 Gen9", "huawei_rh2288h_v3": "Huawei RH2288H V3", "quanta_d51b_2u": "QuantaGrid D51B-2U"}
lines = ["# Fresh Alibaba raw-archive experiment results", "",
    "**These experiments were built directly from the uploaded raw Alibaba archive. "
    "No Yaksh cleaned CSVs, data loader or cleaning code were used to prepare/replay these inputs. "
    "No artificial workloads were substituted.** Shared simulator and scheduling code is reused.", "",
    f"**{validation['runs']} verified runs**, "
    f"**{validation['total_completed_instance_replays']:,} completed instance replays**, "
    "zero rejected/unfinished instances. Each power curve has the same 18 combinations: "
    "three sample sizes and six policies. Every simulation starts fresh and uses exactly one curve.", "",
    "## Archive integrity and provenance", "",
    f"Uploaded file: `{manifest['archive']['archive_file']}`. SHA-256: "
    f"`{manifest['archive']['archive_sha256']}`. Gzip CRC/trailer, tar members and all six extracted "
    "CSV lengths/hashes were checked. Every input and implementation file is fingerprinted.", "",
    "**The compressed archive does not match Alibaba's published legacy `trace_201708.tgz` hash.** "
    "The newer download is named `alibaba-trace-2017.tar.gz`; an "
    "[upstream issue](https://github.com/alibaba/clusterdata/issues/209) reports that discrepancy. "
    "We do not mark the publisher's compressed checksum as passed. Separately, all six extracted "
    "CSV hashes match raw-file fingerprints recorded in the earlier package audit. That comparison "
    "corroborates the raw bytes; it does not supply any cleaned experimental inputs. See "
    "[archive_audit.json](archive_audit.json) and "
    "[archive_content_corroboration.json](archive_content_corroboration.json).", "",
    "## Fresh preparation and observation fidelity", "",
    f"The pipeline read **{manifest['task_audit']['rows']:,} raw task rows**, "
    f"**{manifest['instance_audit']['rows']:,} raw instance-attempt rows**, and "
    f"**{manifest['host_audit']['rows']:,} host-event rows**. It found "
    f"**{manifest['completeness_audit']['complete_groups']:,} eligible complete groups**. "
    "Every included group has exactly its original declared number of valid completed first-attempt "
    "records. Missing observations are not fabricated and multiplicity is not reduced.", "",
    "Each included instance keeps its own observed source `end - start` duration. "
    "There is no group-mean runtime substitution. Task creation is still the modeled release; "
    "original host assignment and launch staggering are not replayed. Source host capacity records "
    "supply a newly selected fixed 64-host pool with seed 2026.", "",
    "| Task groups | Observed instances | Groups with variable runtimes |",
    "|---:|---:|---:|",
]
for w in manifest["workloads"]:
    lines.append(f"| {w['task_groups']:,} | {w['instances']:,} | {w['groups_with_variable_observed_runtime']:,} |")
lines += ["", "Selection uses fixed quotas over 15-minute arrival bins, relative resource skew and "
    "multiplicity bands, with no energy outcome used in sampling. These are group-level quotas; "
    "they do not establish identical instance-weighted bursts or exact representativeness. "
    "Complete-observation and completed-window filters introduce selection/boundary bias. "
    "The smaller samples share groups with the larger sample and are not independent replications.", "",
    "**Do not compare absolute kWh against the historical handoff as if the workloads were identical:** "
    "the eligible population, selected groups, host pool and per-instance runtime model differ. "
    "All policies below are rerun on the same freshly prepared inputs for a fair within-study comparison.", "",
    "## Modeled energy, kWh", "",
    "Columns compare first-fit (FF), CPU best-fit (BF), original CPU-oriented LR-MMT (LR), "
    "original weighted memory-aware LR-MMT (LR+M), energy-first CPU (EF-CPU), and energy-first "
    "memory (EF-M). A positive last column means EF-M used less energy than EF-CPU.", "",
    "| Curve | Groups | FF | BF | LR | LR+M | EF-CPU | EF-M | EF-M reduction vs EF-CPU |",
    "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
]
wins = 0
for curve in config["power_curves"]:
    for size in config["workload_group_counts"]:
        subset = [index[(size, curve, p)] for p in config["policies"]]
        cpu, memory = subset[-2:]
        saving = 100 * (cpu["energy_kwh"] - memory["energy_kwh"]) / cpu["energy_kwh"]
        wins += saving > 0
        cells = " | ".join(f"{r['energy_kwh']:.6f}" for r in subset)
        lines.append(f"| {names[curve]} | {size:,} | {cells} | {saving:+.4f}% |")
lines += ["", f"EF-M saved energy in **{wins}/9** paired workload/curve comparisons. "
    "A small positive difference, especially below 0.01%, should not be presented as robust "
    "production savings. All gains and losses are retained; no independent-window confidence "
    "interval or measured electricity-saving claim is made.", "",
    "## Waiting, migrations and powered hosts: primary HPE curve", "",
    "| Groups | Policy | Mean wait, s | p95 wait, s | Migrations | Mean powered hosts | Pressure fraction |",
    "|---:|---|---:|---:|---:|---:|---:|",
]
for size in config["workload_group_counts"]:
    for policy in ("energy_first_cpu", "energy_first_memory"):
        r = index[(size, config["power_curves"][0], policy)]
        lines.append(f"| {size:,} | {policy} | {r['mean_wait_s']:.3f} | {r['p95_wait_s']:.3f} | "
                     f"{r['migrations']:,} | {r['mean_active_hosts']:.3f} | {r['overload_host_time_fraction']:.4f} |")
lines += ["", "Pressure fraction integrates reserved CPU or memory above 0.9 over host-time; "
    "it is not an observed SLA failure rate. Mean/p95 waits include queueing and waking, while "
    "migration pauses are separate and included in actual completion timing. The full summaries "
    "also include fragmentation, stranded-capacity probes and sleep/wake/active energy components.", "",
    "## Shared assumptions and limitations", "",
    "All policies use the same host pool, original resource requests, original observed durations, "
    "independent-instance FIFO admission, capacity limits and window-plus-drain rule. LR/MMT "
    "controller settings and migration/sleep assumptions are shared by the four migration policies; "
    "FF/BF are non-migrating baselines. The energy-first pair differs only in its power tie-break.", "",
    "Task CPU is divided by 100 under "
    "[Alibaba's unit clarification](https://github.com/alibaba/clusterdata/issues/11). Memory "
    "remains normalized for placement. Migration assumes 64 GiB per normalized unit and "
    "125 MB/s per concurrent transfer. Sleep is modeled at 5 W after 60 seconds idle; wakeup "
    "takes 10 seconds. These parameters are assumptions, not measurements supplied in the trace.", "",
    "The model replays selected completed batch work, not production DAG dependencies, failures, "
    "background online load or empirical per-batch-instance usage histories. SPECpower is a "
    "whole-server surrogate curve applied at requested CPU fraction, not a calibration of "
    "Alibaba hardware or its electricity bill. No future durations or original placements are "
    "exposed to scheduling policies.", "",
    "## Validation and reproduction", "",
    "The independent validator reread raw task, host and attempt rows and matched every selected "
    "request, capacity, release and individual duration, plus complete original multiplicity. "
    "Replay validates unique outcomes, completed work, full drain, capacity samples, energy sums "
    "and observed runtime plus migration pauses. The final verifier checks full equal per-curve "
    "coverage and unchanged implementation/input hashes.", "",
    "```sh", "python -m RAW_Alibaba.extract", "python -m RAW_Alibaba.prepare",
    "python -m RAW_Alibaba.verify_data", "python -m RAW_Alibaba.run", "python -m RAW_Alibaba.verify",
    "python RAW_Alibaba/analysis/build_report.py", "```", "",
    "[Preparation manifest](prepared/manifest.json) · [Raw-row validation](data_validation.json) · "
    "[Full comparison](reports/comparison.csv) · [Final validation](reports/validation.json)", "",
]
(HERE / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(HERE / "REPORT.md")
