"""Build Rushi's D5 analysis (tables, charts, REPORT.md) from committed files.

    python -m RUSHI_Task.analyze

Runs on a fresh clone; it needs no raw archive and runs no simulations. Inputs:
  RAW_Alibaba/reports/summaries.json   the 36 active runs (checked against the
                                       hash BASELINE_Comparison validated)
  RAW_Alibaba/prepared/manifest.json   workload mix by task type
  ecosched/power_curves.json           SPECpower curves
  ROHAN_Task.policies.PolicyConfig     memory_balance_weight (0.25)
  RUSHI_Task/reports/runs/**.json      decision recordings from RUSHI_Task.rerun
"""
import csv
import json
import statistics
from pathlib import Path

from ecosched.power import load_curve
from RAW_Alibaba.extract import digest
from RAW_Alibaba.run import source_hashes
from ROHAN_Task.policies import PolicyConfig
from . import charts
from .accounting import (GAP_PARTS, band_slopes, break_even_imbalance, pair_gap, run_breakdown,
                         small_task_score_gap, wake_score_cost)

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
OUT = HERE / "reports"
RUNS = OUT / "runs"
SUMMARIES = ROOT / "RAW_Alibaba/reports/summaries.json"
MANIFEST = ROOT / "RAW_Alibaba/prepared/manifest.json"
BASELINE_VALIDATION = ROOT / "BASELINE_Comparison/reports/validation.json"
BASELINE_SUMMARIES = ROOT / "BASELINE_Comparison/reports/summaries.json"
RAW_VALIDATION = ROOT / "RAW_Alibaba/reports/validation.json"
POLICIES = ("first_fit", "best_fit", "lr_mmt", "lr_mmt_memory")
PAIR = ("lr_mmt", "lr_mmt_memory")
SIZES = (250, 1000, 4000)
CURVES = {"hpe_dl360_gen9": "HPE DL360 Gen9", "huawei_rh2288h_v3": "Huawei RH2288H V3",
          "quanta_d51b_2u": "QuantaGrid D51B-2U"}
SKEWS = {"balanced": "Balanced", "memory_heavy": "Memory-heavy", "cpu_heavy": "CPU-heavy"}
DESTINATIONS = {"sleeping": "asleep (woken for it)", "waking": "still waking up",
                "on_empty": "on, with no work", "on_running": "on, already running work"}
KWH = 3_600_000
PRIMARY = "hpe_dl360_gen9"
LARGEST = 4000


# ---------------------------------------------------------------- inputs
def load_committed():
    """The 36 active runs, with the same provenance/completion checks as
    BASELINE_Comparison.build. Two recorded file hashes are stale in the team
    repo (see README), so content equality is checked instead of those hashes."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = json.loads(SUMMARIES.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE_VALIDATION.read_text(encoding="utf-8"))
    baseline_rows = json.loads(BASELINE_SUMMARIES.read_text(encoding="utf-8"))
    raw = json.loads(RAW_VALIDATION.read_text(encoding="utf-8"))
    if not baseline["passed"] or not raw["passed"] or raw["runs"] != len(rows):
        raise ValueError("RAW_Alibaba or BASELINE_Comparison validation did not pass")
    code = source_hashes()
    counts = {w["task_groups"]: w["instances"] for w in manifest["workloads"]}
    selected = [r for r in rows if r["policy"] in POLICIES]
    index = {(r["workload_groups"], r["power_curve"], r["policy"]): r for r in selected}
    expected = {(s, c, p) for s in SIZES for c in CURVES for p in POLICIES}
    if len(selected) != len(expected) or set(index) != expected:
        raise ValueError("Active 36-run grid is incomplete or duplicated")
    validated = {(r["workload_groups"], r["power_curve"], r["policy"]): r for r in baseline_rows}
    if validated != index:
        raise ValueError("Active runs differ from the rows BASELINE_Comparison validated")
    for key, r in index.items():
        if (r["source_sha256"] != code or r["config"] != manifest["config"]["simulation"]
                or not r["validation"]["passed"] or r["synthetic_workload"] or r["uses_yaksh_prepared_inputs"]
                or r["data_source"] != "fresh_user_archive_alibaba_v2017"
                or r["completed_instances"] != counts[r["workload_groups"]]
                or r["completed_task_groups"] != r["workload_groups"]
                or r["rejected_instances"] or r["unfinished_instances"] or r["capacity_violation_host_seconds"]):
            raise ValueError(f"Committed run failed a provenance/completion check: {key}")
    provenance = {
        "summaries_sha256": digest(SUMMARIES),
        "summary_sha256_recorded_by_baseline_validation": baseline["source_summary_sha256"],
        "active_rows_equal_baseline_validated_rows": True,
        "raw_result_validation_passed": True, "simulator_source_unchanged_since_runs": True,
        "manifest_sha256_recorded_in_results": sorted({r["manifest_sha256"] for r in selected}),
        "committed_manifest_sha256": digest(MANIFEST),
    }
    return manifest, index, provenance


def load_recordings(index):
    """Decision recordings; all 18 or none. Each must equal its committed run."""
    files = sorted(RUNS.glob("*/workload_*/*.json"))
    if not files:
        return {}
    recordings = {}
    for path in files:
        row = json.loads(path.read_text(encoding="utf-8"))
        key = (row["workload_groups"], row["power_curve"], row["policy"])
        committed = index[key]
        decisions = row["decisions"]
        if (key in recordings or not row["reproduces_committed_summary"]
                or row["energy_kwh"] != committed["energy_kwh"] or row["migrations"] != committed["migrations"]
                or decisions["own_rule_recompute_mismatches"]
                or decisions["placements"] != committed["completed_instances"]):
            raise ValueError(f"Recording does not reproduce its committed run: {path}")
        recordings[key] = row
    expected = {(s, c, p) for s in SIZES for c in CURVES for p in PAIR}
    if set(recordings) != expected:
        raise ValueError(f"Recording grid incomplete: missing {sorted(expected - set(recordings))}")
    return recordings


# ---------------------------------------------------------------- helpers
def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in rows for k in r)), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def pct(part, whole):
    return 100.0 * part / whole if whole else 0.0


def signed(value, digits=2):
    return f"{value:+.{digits}f}"


def tick_mean(series):
    return statistics.fmean(series) if series else 0.0


def pooled(decisions, field):
    return sum(v[field] for v in decisions["by_skew"].values())


def pooled_destinations(decisions):
    totals = dict.fromkeys(DESTINATIONS, 0)
    for v in decisions["by_skew"].values():
        for kind, count in v["destinations"].items():
            totals[kind] += count
    return totals


# ---------------------------------------------------------------- tables
def run_table(index):
    rows = []
    for (size, curve, policy), r in sorted(index.items(), key=lambda kv: (list(CURVES).index(kv[0][1]), kv[0][0], POLICIES.index(kv[0][2]))):
        b = run_breakdown(r, load_curve(curve))
        rows.append({
            "power_curve": curve, "workload_groups": size, "policy": policy, "energy_kwh": r["energy_kwh"],
            "servers_on_hours": b["on_s"] / 3600, "on_running_work_hours": b["running_s"] / 3600,
            "on_without_work_hours": b["idle_on_s"] / 3600, "waking_hours": b["waking_s"] / 3600,
            "asleep_hours": b["sleep_s"] / 3600, "wakeups": r["wakeups"],
            "idle_floor_kwh": b["idle_floor_j"] / KWH, "load_dependent_kwh": b["dynamic_j"] / KWH,
            "waking_kwh": r["waking_energy_j"] / KWH, "asleep_kwh": r["sleep_energy_j"] / KWH,
            "mean_powered_servers": r["mean_active_hosts"], "migrations": r["migrations"],
            "mean_wait_s": r["mean_wait_s"], "p95_wait_s": r["p95_wait_s"],
            "pressure_pct": 100 * r["overload_host_time_fraction"],
            "fragmentation_index": r["mean_fragmentation_index"],
            "cpu_stranded_by_memory_core_hours": r["cpu_stranded_by_memory_core_seconds"] / 3600,
        })
    return rows


def gap_table(index):
    rows = []
    for curve in CURVES:
        for size in SIZES:
            cpu, memory = index[(size, curve, PAIR[0])], index[(size, curve, PAIR[1])]
            gap = pair_gap(cpu, memory, load_curve(curve))
            row = {"power_curve": curve, "workload_groups": size,
                   "cpu_lr_mmt_kwh": cpu["energy_kwh"], "memory_aware_kwh": memory["energy_kwh"],
                   "energy_change_kwh": gap["total_j"] / KWH,
                   "energy_change_pct": 100 * (memory["energy_kwh"] / cpu["energy_kwh"] - 1)}
            for key, _ in GAP_PARTS:
                row[key.replace("_j", "_kwh")] = gap[key] / KWH
            row.update({
                "servers_on_hours_change": gap["other_on_hours"] - gap["base_on_hours"],
                "on_running_work_hours_change": gap["other_running_hours"] - gap["base_running_hours"],
                "on_without_work_hours_change": gap["other_idle_on_hours"] - gap["base_idle_on_hours"],
                "wakeups_cpu_lr_mmt": gap["base_wakeups"], "wakeups_memory_aware": gap["other_wakeups"],
                "mean_powered_servers_cpu_lr_mmt": cpu["mean_active_hosts"],
                "mean_powered_servers_memory_aware": memory["mean_active_hosts"],
            })
            rows.append(row)
    return rows


def tradeoff_table(index):
    rows = []
    for curve in CURVES:
        for size in SIZES:
            a, b = index[(size, curve, PAIR[0])], index[(size, curve, PAIR[1])]
            rows.append({
                "power_curve": curve, "workload_groups": size,
                "energy_change_pct": 100 * (b["energy_kwh"] / a["energy_kwh"] - 1),
                "mean_wait_change_s": b["mean_wait_s"] - a["mean_wait_s"],
                "p95_wait_change_s": b["p95_wait_s"] - a["p95_wait_s"],
                "pressure_change_pct_points": 100 * (b["overload_host_time_fraction"] - a["overload_host_time_fraction"]),
                "migrations_cpu_lr_mmt": a["migrations"], "migrations_memory_aware": b["migrations"],
                "fragmentation_cpu_lr_mmt": a["mean_fragmentation_index"],
                "fragmentation_memory_aware": b["mean_fragmentation_index"],
                "cpu_stranded_core_hours_cpu_lr_mmt": a["cpu_stranded_by_memory_core_seconds"] / 3600,
                "cpu_stranded_core_hours_memory_aware": b["cpu_stranded_by_memory_core_seconds"] / 3600,
            })
    return rows


def arithmetic_table(index, recordings):
    weight = PolicyConfig().memory_balance_weight
    rows = []
    for curve_name, label in CURVES.items():
        curve = load_curve(curve_name)
        sleep_watts = index[(LARGEST, curve_name, PAIR[0])]["config"]["sleep_watts"]
        slopes = band_slopes(curve)
        cheapest = min(slopes, key=lambda s: s["added_watts"])
        row = {"power_curve": curve_name, "sleep_watts": sleep_watts, "idle_watts": curve.watts[0],
               "full_watts": curve.watts[-1], "first_band_added_watts": slopes[0]["added_watts"],
               "cheapest_band": cheapest["band"], "cheapest_band_added_watts": cheapest["added_watts"],
               "memory_balance_weight": weight,
               "wake_score_cost": wake_score_cost(curve, sleep_watts),
               "balance_gain_needed_to_justify_a_wakeup_pct_points": 100 * break_even_imbalance(curve, sleep_watts, weight)}
        if recordings:
            # Typical task and typical busy server, both measured in the CPU LR-MMT run.
            reference = recordings[(LARGEST, curve_name, PAIR[0])]
            task_cpu = reference["task_size"]["median_cpu_fraction_of_median_host"]
            task_memory = reference["task_size"]["median_memory_fraction_of_median_host"]
            ts = reference["time_series"]
            ticks = [i for i, n in enumerate(ts["hosts_running_work"]) if n]
            busy_cpu = tick_mean([ts["mean_cpu_of_hosts_running_work"][i] for i in ticks])
            busy_memory = tick_mean([ts["mean_memory_of_hosts_running_work"][i] for i in ticks])
            gap = small_task_score_gap(curve, task_cpu, busy_cpu)
            busy_penalty = weight * abs(busy_memory - busy_cpu)
            empty_penalty = weight * abs(task_memory - task_cpu)
            row.update({"median_task_cpu_fraction": task_cpu, "median_task_memory_fraction": task_memory,
                        "typical_busy_server_cpu": busy_cpu, "typical_busy_server_memory": busy_memory,
                        "power_score_advantage_of_busy_server": gap,
                        "balance_penalty_typical_busy_server": busy_penalty,
                        "balance_penalty_empty_server": empty_penalty,
                        "balance_advantage_over_power_advantage": (busy_penalty - empty_penalty) / gap,
                        "balance_gain_needed_to_prefer_empty_server_pct_points": 100 * gap / weight})
        rows.append(row)
    return rows


def mix_table(manifest):
    rows = []
    for w in sorted(manifest["workloads"], key=lambda w: w["task_groups"]):
        counts = w["instance_resource_skew_counts"]
        row = {"workload_groups": w["task_groups"], "instances": w["instances"]}
        for skew in SKEWS:
            row[f"{skew}_instances"] = counts.get(skew, 0)
            row[f"{skew}_pct"] = pct(counts.get(skew, 0), w["instances"])
        rows.append(row)
    return rows


def decision_tables(recordings):
    decisions, bands, outcomes, controller, servers = [], [], [], [], []
    for curve in CURVES:
        for size in SIZES:
            for policy in PAIR:
                rec = recordings[(size, curve, policy)]
                d = rec["decisions"]
                placed = d["placements"]
                destinations = pooled_destinations(d)
                disagree = pooled(d, "other_rule_disagreements")
                less_loaded = pooled(d, "disagreements_where_chosen_host_less_loaded")
                pairs = d["disagreement_destination_pairs"]
                other_opens_empty = sum(n for k, n in pairs.items()
                                        if k.split("->")[1] == "on_empty" and k.split("->")[0] in ("on_running", "waking"))
                base = {"power_curve": curve, "workload_groups": size, "policy": policy}
                decisions.append({**base, "placements": placed,
                                  **{f"to_{k}_pct": pct(v, placed) for k, v in destinations.items()},
                                  "mean_cpu_of_chosen_server_after": sum(v["mean_post_placement_cpu"] * v["placements"]
                                                                         for v in d["by_skew"].values()) / placed,
                                  "rules_disagree_pct": pct(disagree, placed),
                                  "disagreements_own_pick_less_loaded_pct": pct(less_loaded, disagree),
                                  "other_rule_would_use_empty_server_instead_pct": pct(other_opens_empty, placed)})
                for skew, v in d["by_skew"].items():
                    bands.append({**base, "task_type": skew, "placements": v["placements"],
                                  **{f"cpu_after_{10 * i}_{10 * (i + 1)}_pct": pct(n, v["placements"])
                                     for i, n in enumerate(v["post_placement_cpu_bands"])},
                                  "rules_disagree_pct": pct(v["other_rule_disagreements"], v["placements"]),
                                  "disagreements_own_pick_less_loaded_pct": pct(
                                      v["disagreements_where_chosen_host_less_loaded"], v["other_rule_disagreements"])})
                for skew, v in rec["outcomes_by_skew"].items():
                    placed_skew = d["by_skew"][skew]
                    outcomes.append({**base, "task_type": skew, "instances": v["instances"],
                                     "mean_wait_s": v["mean_wait_s"], "p95_wait_s": v["p95_wait_s"],
                                     "delayed_pct": 100 * v["delayed_share"],
                                     "placed_on_asleep_or_waking_server_pct": pct(placed_skew["destinations"]["waking"]
                                                                        + placed_skew["destinations"]["sleeping"],
                                                                        placed_skew["placements"]),
                                     "migrated_pct": pct(v["migrated_instances"], v["instances"])})
                controller.append({**base, **rec["controller_diagnostics"]})
                ts = rec["time_series"]
                servers.append({**base, "tick_mean_powered_servers": tick_mean(ts["powered_hosts"]),
                                "tick_mean_servers_running_work": tick_mean(ts["hosts_running_work"]),
                                "tick_mean_cpu_of_servers_running_work": tick_mean(
                                    [x for x, n in zip(ts["mean_cpu_of_hosts_running_work"], ts["hosts_running_work"]) if n]),
                                "tick_mean_memory_of_servers_running_work": tick_mean(
                                    [x for x, n in zip(ts["mean_memory_of_hosts_running_work"], ts["hosts_running_work"]) if n])})
    # The policy's Counter only holds counters that occurred; an absent counter means 0.
    counters = sorted({k for row in controller for k in row} - {"power_curve", "workload_groups", "policy"})
    controller = [{**{k: row[k] for k in ("power_curve", "workload_groups", "policy")},
                   **{k: row.get(k, 0) for k in counters}} for row in controller]
    return decisions, bands, outcomes, controller, servers


# ---------------------------------------------------------------- charts
def chart_energy_gap(gaps):
    groups = []
    largest = [g for g in gaps if g["workload_groups"] == LARGEST]
    rows = [("on_running_work_kwh", "Servers on longer, running work"),
            ("on_without_work_kwh", "Servers on longer, with no work"),
            ("load_dependent_kwh", "Load-dependent power"),
            ("wakeups_kwh", "Wake-ups (full power for 10 s each)"),
            ("energy_change_kwh", "Net change")]
    for key, label in rows:
        bars = []
        for g in largest:
            value = g[key]
            colour = charts.NET if key == "energy_change_kwh" else charts.ADDS if value >= 0 else charts.SAVES
            bars.append({"label": CURVES[g["power_curve"]], "value": value, "colour": colour,
                         "tip": f'{label}, {CURVES[g["power_curve"]]}: {value:+.3f} kWh'})
        groups.append({"label": label, "bars": bars})
    charts.bar_groups(
        OUT / "energy_gap_breakdown.svg",
        "Where the proposed placement's extra energy goes (4,000 groups)",
        "Change in kWh versus CPU-oriented LR-MMT, split exactly by what the simulator charges for each server-second.",
        groups, [("adds energy", charts.ADDS), ("saves energy", charts.SAVES), ("net change", charts.NET)],
        "kWh change (proposed minus CPU-oriented LR-MMT)",
        lambda v, tick=False: ("0" if tick and abs(v) < 1e-12 else f"{v:+.1f}" if tick else f"{v:+.2f}").replace("-", "−"),
        note="Components add up exactly to the net change. Same Alibaba sample, 64 hosts and LR/MMT controller; only placement differs.")


def chart_servers(recordings):
    panels = []
    hours = lambda ts: [t / 3600 for t in ts["time_s"]]
    series = {p: recordings[(LARGEST, PRIMARY, p)]["time_series"] for p in PAIR}
    short = {"lr_mmt": "CPU-oriented", "lr_mmt_memory": "Proposed"}
    panels.append({"title": "Servers switched on (not asleep)", "y_max": 64, "y_format": lambda v: f"{v:.0f}",
                   "series": [{"name": charts.POLICY_NAMES[p], "short": short[p], "colour": charts.POLICY_COLOURS[p],
                               "x": hours(series[p]), "y": series[p]["powered_hosts"]} for p in PAIR]})
    # Average over ticks with at least one server running work, as in servers_running_work.csv.
    busy_average = lambda ts: tick_mean([x for x, n in zip(ts["mean_cpu_of_hosts_running_work"],
                                                           ts["hosts_running_work"]) if n])
    panels.append({"title": "Average CPU load of the servers running work", "y_max": 1.0,
                   "y_format": lambda v: f"{100 * v:.0f}%",
                   "series": [{"name": charts.POLICY_NAMES[p], "short": short[p], "colour": charts.POLICY_COLOURS[p],
                               "x": hours(series[p]), "y": series[p]["mean_cpu_of_hosts_running_work"],
                               "average": busy_average(series[p])} for p in PAIR]})
    charts.line_panels(
        OUT / "servers_over_time.svg",
        "The proposed placement keeps more servers on, each less loaded",
        "4,000 groups, HPE DL360 Gen9 curve, sampled every 300 s by the simulator's controller tick.",
        panels, [(charts.POLICY_NAMES[p], charts.POLICY_COLOURS[p]) for p in PAIR], "Simulated time (hours)")


def chart_disagreements(decision_rows):
    rows = {(r["workload_groups"], r["policy"]): r for r in decision_rows if r["power_curve"] == PRIMARY}
    categories = [f"{s:,} groups" for s in SIZES]
    charts.grouped_columns(
        OUT / "who_picks_the_emptier_server.svg",
        "When the two placement rules disagree, which server does each pick?",
        "Share of disagreements where the policy's own pick was the less-loaded server (HPE curve).",
        categories,
        [{"name": charts.POLICY_NAMES[p], "colour": charts.POLICY_COLOURS[p],
          "values": [rows[(s, p)]["disagreements_own_pick_less_loaded_pct"] for s in SIZES]} for p in PAIR],
        "% of disagreements where the policy picked the less-loaded server", lambda v: f"{v:.0f}%",
        note="At every placement the recorder also computed the other rule's choice from the same snapshot; nothing was changed.")


def chart_waits(outcome_rows):
    rows = {(r["task_type"], r["policy"]): r for r in outcome_rows
            if r["power_curve"] == PRIMARY and r["workload_groups"] == LARGEST}
    groups = []
    for skew, label in SKEWS.items():
        if (skew, PAIR[0]) not in rows:
            continue
        n = rows[(skew, PAIR[0])]["instances"]
        groups.append({"label": f"{label} tasks ({n:,})", "bars": [
            {"label": charts.POLICY_NAMES[p].replace(" (proposed)", ""), "value": rows[(skew, p)]["delayed_pct"],
             "colour": charts.POLICY_COLOURS[p],
             "tip": f'{label}, {charts.POLICY_NAMES[p]}: {rows[(skew, p)]["delayed_pct"]:.1f}% waited; mean wait '
                    f'{rows[(skew, p)]["mean_wait_s"]:.1f} s, p95 {rows[(skew, p)]["p95_wait_s"]:.0f} s'} for p in PAIR]})
    charts.bar_groups(
        OUT / "wait_by_task_type.svg",
        "Share of tasks that had to wait, by task type (4,000 groups, HPE curve)",
        "A task waits when no server has room, or when its server is still waking up (10 s). Mean waits are in REPORT.md.",
        groups, [(charts.POLICY_NAMES[p], charts.POLICY_COLOURS[p]) for p in PAIR],
        "% of the task type's instances that started later than their release", lambda v, tick=False: f"{v:.0f}%" if tick else f"{v:.1f}%",
        note="Task types are RAW_Alibaba/prepare.py's labels, based on each task's requested CPU versus memory share of a median server.")


# ---------------------------------------------------------------- report
def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" if i == 0 else "---:" for i in range(len(headers))) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return lines


def build_report(manifest, index, provenance, gaps, trades, arithmetic, mix, recs, decision_rows, band_rows,
                 outcome_rows, controller_rows, server_rows):
    largest = [g for g in gaps if g["workload_groups"] == LARGEST]
    total_gap = sum(g["energy_change_kwh"] for g in largest)
    running_share = 100 * sum(g["on_running_work_kwh"] for g in largest) / total_gap
    idle_share = 100 * sum(g["on_without_work_kwh"] for g in largest) / total_gap
    load_share = 100 * sum(g["load_dependent_kwh"] for g in largest) / total_gap
    wake_share = 100 * sum(g["wakeups_kwh"] for g in largest) / total_gap
    hpe = next(g for g in largest if g["power_curve"] == PRIMARY)
    wins = sum(g["energy_change_kwh"] < 0 for g in gaps)
    L = ["# Why CPU/memory-aware placement uses more energy at scale", "",
         "**Owner:** Rushi Jhala. **Deliverable:** D5 (memory-aware extension and analysis) from the "
         "[proposal](../../docs/EcoSched_Proposal.pdf). Generated by `python -m RUSHI_Task.analyze`; every number below "
         "comes from committed simulator output. No workload, policy or simulator setting was changed.", "",
         "## Short answer", "",
         f"- The proposed placement saves energy in **{wins}/9** paired cases, all small or medium. On the largest workload it "
         f"uses **{min(g['energy_change_pct'] for g in largest):.2f}–{max(g['energy_change_pct'] for g in largest):.2f}% more** energy.",
         f"- About **{running_share:.0f}%** of that extra energy is servers kept **switched on while running work** "
         f"(roughly {hpe['on_running_work_hours_change']:.0f} more server-hours on the HPE curve). Servers sitting "
         f"empty contribute essentially nothing ({idle_share:+.1f}%). Load-dependent power adds {load_share:.0f}%, and "
         f"fewer wake-ups give back {abs(wake_share):.0f}%.",
         "- Cause: within powered-on servers, the balance term outweighs the power difference, so tasks are spread across "
         "more servers at lower load instead of being packed onto fewer servers. Waking a sleeping server is too expensive "
         "for the balance term to justify, so the proposed policy actually wakes servers **less** often.",
         "- What it buys: lower overload pressure, less resource fragmentation and slightly shorter waits on the largest "
         "workload. This is an energy/performance trade-off, not a free improvement."]
    if recs:
        hpe_out = {(r["task_type"], r["policy"]): r for r in outcome_rows
                   if r["power_curve"] == PRIMARY and r["workload_groups"] == LARGEST}
        a, b = hpe_out[("memory_heavy", PAIR[0])], hpe_out[("memory_heavy", PAIR[1])]
        c, d = hpe_out[("balanced", PAIR[0])], hpe_out[("balanced", PAIR[1])]
        L += [f"- By task type (the proposal's question): on the largest workload, memory-heavy tasks gain the most. The "
              f"share that had to wait drops from {a['delayed_pct']:.1f}% to {b['delayed_pct']:.1f}% (balanced tasks: "
              f"{c['delayed_pct']:.1f}% to {d['delayed_pct']:.1f}%, HPE curve), mainly because fewer tasks wait for a "
              "server to wake up. Mean waits change by at most 2 s."]
    L += [""]

    L += ["## Inputs and checks", "",
          "- 36 committed runs from `RAW_Alibaba/reports/summaries.json`. They are identical, row for row, to the 36 rows "
          "`BASELINE_Comparison` validated, and simulator source hashes still match every run. All runs complete every "
          "instance, with no rejections or capacity violations.",
          f"- `RAW_Alibaba/prepared/manifest.json` currently hashes to `{provenance['committed_manifest_sha256'][:12]}…`, but the "
          f"runs and `RAW_Alibaba/data_validation.json` record `{provenance['manifest_sha256_recorded_in_results'][0][:12]}…`. "
          "The prepared CSVs still match the committed manifest byte-for-byte, so this analysis checks everything except "
          "that one hash. See the README for the fix suggested to Brave.",
          "- Energy accounting uses the simulator's own rule: every server-second is asleep (5 W), waking (full power for "
          "10 s) or on (the SPECpower curve at its requested CPU load). The components below add up exactly to each run's "
          "total, and unit tests check that against the simulator."]
    if recs:
        L += ["- Decision recordings: 18 re-runs of the primary pair with a read-only recorder. Each re-run reproduced its "
              "committed summary field-for-field, which shows the recorder changed nothing. Inputs were rebuilt from the "
              "team's `data-v1.0.0` release archive; that archive matches Alibaba's published SHA-256, and all prepared CSVs "
              "match the committed manifest."]
    L += [""]

    L += ["## 1. Where the extra energy goes", "",
          "Positive kWh means the proposed placement used more energy than CPU-oriented LR-MMT.", "",
          "![Energy gap breakdown](energy_gap_breakdown.svg)", ""]
    L += table(["Curve", "Groups", "Net kWh", "On longer, running work", "On longer, no work", "Load-dependent",
                "Wake-ups", "Wake-ups CPU → proposed", "Powered servers CPU → proposed"],
               [[CURVES[g["power_curve"]], f"{g['workload_groups']:,}", signed(g["energy_change_kwh"], 3),
                 signed(g["on_running_work_kwh"], 3), signed(g["on_without_work_kwh"], 3), signed(g["load_dependent_kwh"], 3),
                 signed(g["wakeups_kwh"], 3), f"{g['wakeups_cpu_lr_mmt']:,} → {g['wakeups_memory_aware']:,}",
                 f"{g['mean_powered_servers_cpu_lr_mmt']:.1f} → {g['mean_powered_servers_memory_aware']:.1f}"] for g in gaps])
    L += ["", "How the parts are defined (exact, from `RUSHI_Task/accounting.py`):", "",
          "- **On longer**: each extra server-hour switched on instead of asleep costs (idle watts − 5 W), e.g. "
          f"{arithmetic[0]['idle_watts'] - arithmetic[0]['sleep_watts']:.0f} W on the HPE curve, before it does any work. "
          "This is split into servers running at least one task and servers on with nothing to run.",
          "- **Load-dependent**: power above idle. The same total work costs more when it is spread thinly, because the "
          "first 10% of CPU load is the steepest part of every SPECpower curve (table in section 2).",
          "- **Wake-ups**: each wake-up runs a server at full power for 10 s instead of 5 W.", "",
          "Reading: on the largest workload the proposed placement does not leave servers idling. It keeps more servers "
          "**busy at the same time**, so fewer of them empty out, fall asleep and save energy.", ""]

    L += ["## 2. Why: the placement score arithmetic", "",
          "Both policies score each candidate server and pick the lowest score (`ROHAN_Task/policies.py`, `LRMMT._score`):", "",
          "```", "power score   = (watts after placing − watts before) / (full watts − idle watts)",
          f"proposed adds = {PolicyConfig().memory_balance_weight} × |CPU fraction − memory fraction|  (after placing)", "```", ""]
    L += table(["Curve", "Watts added by the first 10% CPU", "Cheapest 10% band", "Score cost of waking a server",
                "Balance gain needed to justify a wake-up"],
               [[CURVES[a["power_curve"]], f"{a['first_band_added_watts']:.1f} W",
                 f"{a['cheapest_band_added_watts']:.1f} W ({a['cheapest_band']})", f"{a['wake_score_cost']:.3f}",
                 f"{a['balance_gain_needed_to_justify_a_wakeup_pct_points']:.0f} points"] for a in arithmetic])
    L += ["", "**Waking a sleeping server** costs 0.17–0.20 in score for any task size, while the balance term can add at "
          "most 0.25. The proposed rule would only wake a server for balance if that improved |CPU − memory| by 69–80 "
          "percentage points, which almost never happens. That is why it does **not** wake more servers (section 1 shows it "
          "wakes fewer).", ""]
    if recs:
        a = arithmetic[0]
        L += ["**Choosing between servers that are already on** is different. Measured on the largest workload (CPU "
              f"LR-MMT run, HPE curve): a typical task needs {100 * a['median_task_cpu_fraction']:.2f}% of a server's CPU and "
              f"{100 * a['median_task_memory_fraction']:.2f}% of its memory. On average, a server that is running work sits "
              f"at {100 * a['typical_busy_server_cpu']:.0f}% CPU but {100 * a['typical_busy_server_memory']:.0f}% memory, so it "
              "is memory-heavy. The table compares an empty powered-on server with a server at that average load "
              "(each curve uses its own CPU LR-MMT run).", ""]
        L += table(["Curve", "Power-score advantage of the busy server", "Balance penalty on the busy server",
                    "Balance penalty on an empty server", "Balance advantage ÷ power advantage"],
                   [[CURVES[a["power_curve"]], f"{a['power_score_advantage_of_busy_server']:.4f}",
                     f"{a['balance_penalty_typical_busy_server']:.4f}", f"{a['balance_penalty_empty_server']:.4f}",
                     f"{a['balance_advantage_over_power_advantage']:.1f}×"] for a in arithmetic])
        L += ["", "An empty server is perfectly balanced: 0% CPU and 0% memory, so a tiny task leaves it almost balanced. The "
              "busy server pays a balance penalty several times larger than its power advantage. Among powered-on servers, "
              "the proposed rule therefore decides mainly by balance: it moves tasks away from busy, memory-heavy servers "
              "towards emptier ones, which keeps more servers running work. CPU-only scoring does the opposite. The "
              "cheapest place for a small task is a server already in the middle of the curve, so it packs work together.", ""]

    if recs:
        dec = {(r["power_curve"], r["workload_groups"], r["policy"]): r for r in decision_rows}
        big = [dec[(c, LARGEST, p)] for c in CURVES for p in PAIR]
        mem_less = [r["disagreements_own_pick_less_loaded_pct"] for r in big if r["policy"] == PAIR[1]]
        cpu_less = [r["disagreements_own_pick_less_loaded_pct"] for r in big if r["policy"] == PAIR[0]]
        opens = [r["other_rule_would_use_empty_server_instead_pct"] for r in big if r["policy"] == PAIR[0]]
        ctl = {(r["power_curve"], r["workload_groups"], r["policy"]): r for r in controller_rows}
        hpe_ctl = [ctl[(PRIMARY, LARGEST, p)] for p in PAIR]
        L += ["## 3. What the policies actually did", "",
              "The recorder saw every placement decision. It also computed the other rule's pick from the same snapshot, so "
              "the two rules can be compared decision by decision without changing the run.", "",
              "![Who picks the emptier server](who_picks_the_emptier_server.svg)", "",
              f"On the largest workload, when the two rules disagree, the proposed policy's own pick is the less-loaded "
              f"server in **{min(mem_less):.0f}–{max(mem_less):.0f}%** of cases, against "
              f"**{min(cpu_less):.0f}–{max(cpu_less):.0f}%** for CPU-oriented LR-MMT. Replaying CPU LR-MMT's own decisions, "
              f"the proposed rule would have sent **{min(opens):.1f}–{max(opens):.1f}%** of all tasks to a powered-on server "
              "with no work, where CPU-only scoring added them to a server that already had work.", "",
              f"The consolidation controller then pushes back. On the HPE curve it planned to empty "
              f"{hpe_ctl[1].get('evacuated_host_plans', 0):,} under-used hosts (moving all their tasks elsewhere) for the "
              f"proposed policy, against {hpe_ctl[0].get('evacuated_host_plans', 0):,} for CPU LR-MMT, using "
              f"{hpe_ctl[1].get('consolidation_migrations', 0):,} against {hpe_ctl[0].get('consolidation_migrations', 0):,} "
              "consolidation migrations. Even so, about eight more servers stay on: placement spreads tasks faster than "
              "consolidation packs them back.", ""]
        L += table(["Curve", "Groups", "Policy", "Rules disagree", "Own pick less loaded (of disagreements)",
                    "Other rule would use an empty server", "Mean CPU of chosen server after placing"],
                   [[CURVES[r["power_curve"]], f"{r['workload_groups']:,}", charts.POLICY_NAMES[r["policy"]],
                     f"{r['rules_disagree_pct']:.1f}%", f"{r['disagreements_own_pick_less_loaded_pct']:.1f}%",
                     f"{r['other_rule_would_use_empty_server_instead_pct']:.1f}%",
                     f"{100 * r['mean_cpu_of_chosen_server_after']:.1f}%"] for r in decision_rows])
        L += ["", "Where tasks were placed (share of all placements, by the chosen server's state just before):", ""]
        L += table(["Curve", "Groups", "Policy"] + [v for v in DESTINATIONS.values()],
                   [[CURVES[r["power_curve"]], f"{r['workload_groups']:,}", charts.POLICY_NAMES[r["policy"]]]
                    + [f"{r[f'to_{k}_pct']:.1f}%" for k in DESTINATIONS] for r in decision_rows])
        L += ["", "Most tasks land on a server that is still waking up: tasks arrive in bursts (a task group releases all its "
              "instances at once), so the first task wakes a server and the next ones follow it there.", "",
              "![Servers over time](servers_over_time.svg)", ""]
        L += table(["Curve", "Groups", "Policy", "Powered servers (tick mean)", "Servers running work",
                    "CPU load of servers running work", "Memory load of servers running work"],
                   [[CURVES[r["power_curve"]], f"{r['workload_groups']:,}", charts.POLICY_NAMES[r["policy"]],
                     f"{r['tick_mean_powered_servers']:.2f}", f"{r['tick_mean_servers_running_work']:.2f}",
                     f"{100 * r['tick_mean_cpu_of_servers_running_work']:.1f}%",
                     f"{100 * r['tick_mean_memory_of_servers_running_work']:.1f}%"] for r in server_rows])
        L += ["", "Controller activity (same LR detector and MMT selector in both; counts from the policy's diagnostics):", ""]
        L += table(["Curve", "Groups", "Policy", "Overloaded host-ticks", "Overload migrations", "Consolidation migrations",
                    "Hosts evacuated", "Evacuations rolled back"],
                   [[CURVES[r["power_curve"]], f"{r['workload_groups']:,}", charts.POLICY_NAMES[r["policy"]],
                     f"{r.get('overloaded_host_ticks', 0):,}", f"{r.get('overload_migrations', 0):,}",
                     f"{r.get('consolidation_migrations', 0):,}", f"{r.get('evacuated_host_plans', 0):,}",
                     f"{r.get('evacuations_rolled_back', 0):,}"] for r in controller_rows])
        L += [""]

        L += ["## 4. Results by task type", "",
              "Task types come from `RAW_Alibaba/prepare.py`: a task is CPU-heavy if its CPU share of a median server is more "
              "than twice its memory share, memory-heavy if less than half, otherwise balanced.", ""]
        L += table(["Groups", "Instances", "Balanced", "Memory-heavy", "CPU-heavy"],
                   [[f"{m['workload_groups']:,}", f"{m['instances']:,}", f"{m['balanced_pct']:.1f}%",
                     f"{m['memory_heavy_pct']:.1f}%", f"{m['cpu_heavy_pct']:.2f}%"] for m in mix])
        out = {(r["power_curve"], r["workload_groups"], r["task_type"], r["policy"]): r for r in outcome_rows}
        mh = [out[(c, LARGEST, "memory_heavy", p)] for c in CURVES for p in PAIR]
        bal = [out[(c, LARGEST, "balanced", p)] for c in CURVES for p in PAIR]
        drop = lambda rows: [a["delayed_pct"] - b["delayed_pct"] for a, b in zip(rows[::2], rows[1::2])]
        big_waits = [abs(out[(c, LARGEST, k, PAIR[1])]["mean_wait_s"] - out[(c, LARGEST, k, PAIR[0])]["mean_wait_s"])
                     for c in CURVES for k in SKEWS if (c, LARGEST, k, PAIR[0]) in out]
        memory_gains_most = all(m > b for m, b in zip(drop(mh), drop(bal)))
        smaller = [r for r in outcome_rows if r["workload_groups"] < LARGEST]
        wake_only = all(abs(r["delayed_pct"] - r["placed_on_asleep_or_waking_server_pct"]) < 1e-9 for r in smaller)
        small_mh = [out[(c, SIZES[0], "memory_heavy", p)] for c in CURVES for p in PAIR]
        small_reversal = all(b["delayed_pct"] > a["delayed_pct"] for a, b in zip(small_mh[::2], small_mh[1::2]))
        text_4 = ("On the largest workload, the proposed placement mostly changes **how many tasks wait at all**, not how "
                  f"long the long waits are. The share of memory-heavy tasks that waited falls by "
                  f"{min(drop(mh)):.0f}–{max(drop(mh)):.0f} percentage points, and for balanced tasks by "
                  f"{min(drop(bal)):.0f}–{max(drop(bal)):.0f} points. Mean waits move by at most {max(big_waits):.1f} s, and "
                  "P95 waits barely change. The 'placed on an asleep or waking server' column shows why. Fewer tasks have "
                  "to wait the 10 s wake-up, because more servers are already on. That is the same extra powered-on time "
                  "that costs energy in section 1.")
        if memory_gains_most:
            text_4 += " Memory-heavy tasks, the type this policy targets, gain the most on every curve."
        L += ["", "![Share of tasks that waited, by task type](wait_by_task_type.svg)", "", text_4, ""]
        if wake_only:
            L += ["At 250 and 1,000 groups every wait is a wake-up wait. The two percentage columns are identical and P95 "
                  "is exactly the 10 s wake latency, because no task queues for capacity at those sizes."
                  + (" On the smallest workload the effect reverses for memory-heavy tasks: slightly more of them wait "
                     "under the proposed placement." if small_reversal else ""), ""]
        L += table(["Curve", "Groups", "Task type", "Instances", "Waited at all CPU → proposed",
                    "Placed on an asleep or waking server", "Mean wait CPU → proposed (s)", "P95 wait CPU → proposed (s)",
                    "Migrated CPU → proposed"],
                   [[CURVES[c], f"{s:,}", SKEWS.get(k, k), f"{o[0]['instances']:,}",
                     f"{o[0]['delayed_pct']:.1f}% → {o[1]['delayed_pct']:.1f}%",
                     f"{o[0]['placed_on_asleep_or_waking_server_pct']:.1f}% → {o[1]['placed_on_asleep_or_waking_server_pct']:.1f}%",
                     f"{o[0]['mean_wait_s']:.1f} → {o[1]['mean_wait_s']:.1f}",
                     f"{o[0]['p95_wait_s']:.0f} → {o[1]['p95_wait_s']:.0f}",
                     f"{o[0]['migrated_pct']:.1f}% → {o[1]['migrated_pct']:.1f}%"]
                    for c in CURVES for s in SIZES for k in SKEWS
                    for o in [[out.get((c, s, k, p)) for p in PAIR]] if o[0] and o[1]])
        L += ["", "Energy is charged per server, not per task, so energy cannot be split by task type without an extra "
              "allocation assumption. Waiting and migration outcomes can be split exactly, so those are reported instead.", ""]

    L += ["## 5. The trade-off", "",
          "Negative wait/pressure changes favour the proposed placement; positive energy changes favour CPU-oriented LR-MMT.", ""]
    L += table(["Curve", "Groups", "Energy", "Mean wait", "P95 wait", "Pressure", "Migrations CPU → proposed",
                "Fragmentation index CPU → proposed"],
               [[CURVES[t["power_curve"]], f"{t['workload_groups']:,}", f"{t['energy_change_pct']:+.2f}%",
                 f"{t['mean_wait_change_s']:+.2f} s", f"{t['p95_wait_change_s']:+.0f} s",
                 f"{t['pressure_change_pct_points']:+.2f} pts", f"{t['migrations_cpu_lr_mmt']:,} → {t['migrations_memory_aware']:,}",
                 f"{t['fragmentation_cpu_lr_mmt']:.4f} → {t['fragmentation_memory_aware']:.4f}"] for t in trades])
    big_trades = [t for t in trades if t["workload_groups"] == LARGEST]
    all_better = all(t["fragmentation_memory_aware"] < t["fragmentation_cpu_lr_mmt"] and t["pressure_change_pct_points"] < 0
                     and t["mean_wait_change_s"] < 0 for t in big_trades)
    L += ["", ("On the largest workload the proposed placement does what it was designed to do: on all three curves it "
               "lowers fragmentation, pressure and mean wait. " if all_better else "")
          + "In this simulator, though, energy depends mostly on how many servers are switched on. Balancing spreads work "
          "across more servers, so it costs energy whenever the load is large enough to keep those extra servers busy."
          + ("" if not (rises := [t for t in trades if t["fragmentation_memory_aware"] > t["fragmentation_cpu_lr_mmt"]])
             else " At smaller sizes the differences are small and mixed; fragmentation even rises in "
             + ", ".join(f"the {t['workload_groups']:,}-group {CURVES[t['power_curve']]} case" for t in rises) + "."), ""]

    L += ["## Limits", "",
          "- Simulation estimates from requested resources and whole-server SPECpower curves, not measured Alibaba "
          "electricity. Background online load, failures and DAG dependencies are not replayed.",
          "- Nine overlapping, deterministic cases (three sizes × three curves) are not independent replications, so no "
          "significance or generalisation claim follows.",
          "- The balance weight is fixed at the implemented 0.25. No weight was tuned: AGENTS.md excludes new placement "
          "variants and the core freeze applies. A weight sensitivity study is listed as optional follow-up in the README.",
          "- Task types are based on requested resources, not observed usage.", "",
          "## Rebuild", "", "```", "python -m unittest discover -s RUSHI_Task/tests -v",
          "python -m RUSHI_Task.analyze        # tables, charts and this report from committed files",
          "python -m RUSHI_Task.rerun          # optional: re-record decisions (needs prepared inputs, ~20 min)", "```", ""]
    return "\n".join(L)


def main():
    manifest, index, provenance = load_committed()
    recordings = load_recordings(index)
    OUT.mkdir(parents=True, exist_ok=True)
    runs = run_table(index)
    gaps = gap_table(index)
    trades = tradeoff_table(index)
    arithmetic = arithmetic_table(index, recordings)
    mix = mix_table(manifest)
    write_csv(OUT / "run_energy_breakdown.csv", runs)
    write_csv(OUT / "pair_energy_gap.csv", gaps)
    write_csv(OUT / "tradeoffs.csv", trades)
    write_csv(OUT / "placement_score_arithmetic.csv", arithmetic)
    write_csv(OUT / "workload_mix.csv", mix)
    write_csv(OUT / "curve_band_watts.csv", [{"power_curve": c, **s} for c in CURVES for s in band_slopes(load_curve(c))])
    chart_energy_gap(gaps)
    decision_rows = band_rows = outcome_rows = controller_rows = server_rows = []
    if recordings:
        decision_rows, band_rows, outcome_rows, controller_rows, server_rows = decision_tables(recordings)
        write_csv(OUT / "placement_decisions.csv", decision_rows)
        write_csv(OUT / "placement_load_bands.csv", band_rows)
        write_csv(OUT / "outcomes_by_task_type.csv", outcome_rows)
        write_csv(OUT / "controller_diagnostics.csv", controller_rows)
        write_csv(OUT / "servers_running_work.csv", server_rows)
        chart_servers(recordings)
        chart_disagreements(decision_rows)
        chart_waits(outcome_rows)
    report = build_report(manifest, index, provenance, gaps, trades, arithmetic, mix, recordings, decision_rows,
                          band_rows, outcome_rows, controller_rows, server_rows)
    (OUT / "REPORT.md").write_text(report, encoding="utf-8", newline="\n")
    validation = {
        "passed": True, "committed_runs_checked": len(index), "pairs_decomposed": len(gaps),
        "decomposition_exact": True, "decision_recordings": len(recordings),
        "recordings_reproduce_committed_runs": len(recordings) == 18,
        "new_simulations_in_this_step": 0, "synthetic_runs": 0, **provenance,
        "analysis_source_sha256": {p.relative_to(ROOT).as_posix(): digest(p)
                                   for p in sorted(HERE.glob("*.py"))},
    }
    (OUT / "validation.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in validation.items() if k != "analysis_source_sha256"}, indent=2))


if __name__ == "__main__":
    main()
