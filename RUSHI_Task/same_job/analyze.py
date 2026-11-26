"""Score the same-job rule on the team's 9 cases (DESIGN.md in this folder).

    python -m RUSHI_Task.same_job.analyze

Reads the 36 runs in reports/runs/ and the team's committed First Fit and Best Fit results
(RAW_Alibaba/reports/summaries.json). Applies the success rule and the team's limits
(POLICY_Improvement/config.json), both fixed in DESIGN.md before any run. Also re-checks
the rule's premise on the team's trace: do tasks of the same job finish close together?
(That check needs the git-ignored prepared inputs; without them the committed
reports/premise_check.json is reused, so everything else rebuilds from committed files.)
Writes reports/REPORT.md, CSV tables, charts and validation.json.
"""
from collections import defaultdict
import csv
import json
from pathlib import Path
import random
import statistics

from ecosched import load_curve
from RUSHI_Task import charts as C
from RUSHI_Task.accounting import pair_gap
from .run import COMMITTED, CURVES, NAMES, ORIGINALS, OUTPUT, PACKAGE, SIZES, code_hashes, jobs

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
REPORTS = HERE / "reports"
LIMITS = json.loads((ROOT / "POLICY_Improvement" / "config.json").read_text(encoding="utf-8"))["success_limits"]
CASES = [(size, curve) for size in SIZES for curve in CURVES]
CURVE_NAMES = {"hpe_dl360_gen9": "HPE DL360 Gen9", "huawei_rh2288h_v3": "Huawei RH2288H V3",
               "quanta_d51b_2u": "QuantaGrid D51B-2U"}
LONG = {"lr_mmt": "LR-MMT", "lr_mmt_memory": "Memory-aware LR-MMT",
        "lr_mmt_same_job": "LR-MMT + same-job rule", "lr_mmt_memory_same_job": "Memory-aware LR-MMT + same-job rule",
        "first_fit": "First Fit", "best_fit": "Best Fit"}
SHORT = {"lr_mmt": "LR-MMT", "lr_mmt_memory": "Memory-aware", "lr_mmt_same_job": "LR-MMT + rule",
         "lr_mmt_memory_same_job": "Memory-aware + rule", "first_fit": "First Fit", "best_fit": "Best Fit"}
# Validated categorical palette, slots in order (blue, orange, aqua, yellow, magenta).
COLOURS = {"lr_mmt": "#2a78d6", "lr_mmt_memory": "#eb6834", "lr_mmt_memory_same_job": "#1baf7a",
           "first_fit": "#eda100", "lr_mmt_same_job": "#e87ba4"}
TYPE_NAMES = {"balanced": "Balanced", "memory_heavy": "Memory-heavy", "cpu_heavy": "CPU-heavy"}
COMPARISONS = (("S1", "lr_mmt_same_job", "lr_mmt"),
               ("S2", "lr_mmt_memory_same_job", "lr_mmt_memory"),
               ("S3", "lr_mmt_same_job", "first_fit"),
               ("S4", "lr_mmt_memory_same_job", "first_fit"),
               ("S5", "lr_mmt_memory_same_job", "lr_mmt"),
               ("S6", "lr_mmt_memory_same_job", "lr_mmt_same_job"))
ALL = ("first_fit", "best_fit", "lr_mmt", "lr_mmt_memory", "lr_mmt_same_job", "lr_mmt_memory_same_job")
PAIRS = (("lr_mmt", "lr_mmt_same_job"), ("lr_mmt_memory", "lr_mmt_memory_same_job"))
METRICS = ("energy_kwh", "mean_wait_s", "p95_wait_s", "p95_turnaround_s", "overload_host_time_fraction",
           "migrations", "migration_pause_instance_seconds", "wakeups", "mean_active_hosts",
           "mean_fragmentation_index", "delayed_instances", "completed_instances")


# ---------- small helpers ----------

def pct(new, old):
    return 100 * (new - old) / old


def signed(value, tick=False, digits=1):
    if tick and abs(value) < 1e-12:
        return "0"
    return f"{value:+.{digits}f}".replace("-", "−")


def fmt_pct(value, digits=2):
    return signed(value, digits=digits) + "%"


def md_table(header, rows, align):
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join(align) + "|"]
    return "\n".join(lines + ["| " + " | ".join(str(c) for c in row) + " |" for row in rows])


def write_csv(path, rows):
    names = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def limit_failures(candidate, reference):
    """The team's fixed limits: waits may rise by max(1 s, 5%); pressure by 0.01."""
    failures = []
    for key, relative in (("mean_wait_s", LIMITS["mean_wait_relative_increase"]),
                          ("p95_wait_s", LIMITS["p95_wait_relative_increase"])):
        allowed = reference[key] + max(LIMITS["wait_absolute_floor_s"], relative * reference[key])
        if candidate[key] > allowed + 1e-12:
            failures.append(key)
    if (candidate["overload_host_time_fraction"]
            > reference["overload_host_time_fraction"] + LIMITS["pressure_absolute_increase"] + 1e-12):
        failures.append("pressure")
    return failures


# ---------- loading and scoring ----------

def load():
    committed = {(r["workload_groups"], r["power_curve"], r["policy"]): r
                 for r in json.loads(COMMITTED.read_text(encoding="utf-8"))}
    runs = {k: {"summary": r, "committed": True} for k, r in committed.items() if k[2] in ("first_fit", "best_fit")}
    new = {}
    for path in OUTPUT.rglob("*.json"):
        r = json.loads(path.read_text(encoding="utf-8"))
        new[(r["workload_groups"], r["power_curve"], r["policy"])] = r
    hashes = code_hashes()
    status = {"expected": len(jobs()), "present": sum(j in new for j in jobs()),
              "stale": sum(r["source_sha256"] != hashes for r in new.values()),
              "failed_validation": sum(not r["validation"]["passed"] for r in new.values()),
              "originals_expected": len(CASES) * len(ORIGINALS),
              "originals_reproduced": sum(bool(r.get("reproduces_committed_result")) and
                                          all(r["summary"][f] == committed[k].get(f) for f in r["summary"])
                                          for k, r in new.items() if k[2] in ORIGINALS)}
    if (status["present"] != status["expected"] or status["stale"] or status["failed_validation"]
            or status["originals_reproduced"] != status["originals_expected"]):
        raise ValueError(f"Runs incomplete or invalid: {status}")
    runs.update(new)
    return runs, new, status


def compare(runs):
    rows, verdicts = [], []
    for cid, policy, reference in COMPARISONS:
        group = []
        for size, curve in CASES:
            x, r = runs[(size, curve, policy)]["summary"], runs[(size, curve, reference)]["summary"]
            failures = limit_failures(x, r)
            group.append({"comparison": cid, "policy": policy, "reference": reference, "workload_groups": size,
                          "power_curve": curve, "policy_kwh": x["energy_kwh"], "reference_kwh": r["energy_kwh"],
                          "energy_change_pct": pct(x["energy_kwh"], r["energy_kwh"]),
                          "wins_energy": x["energy_kwh"] < r["energy_kwh"],
                          "mean_wait_change_s": x["mean_wait_s"] - r["mean_wait_s"],
                          "p95_wait_change_s": x["p95_wait_s"] - r["p95_wait_s"],
                          "pressure_change": x["overload_host_time_fraction"] - r["overload_host_time_fraction"],
                          "limit_failures": ";".join(failures), "within_limits": not failures})
        rows += group
        wins = [g for g in group if g["wins_energy"]]
        total_new, total_old = sum(g["policy_kwh"] for g in group), sum(g["reference_kwh"] for g in group)
        changes = [g["energy_change_pct"] for g in group]
        verdicts.append({"comparison": cid, "policy": policy, "reference": reference, "cases": len(group),
                         "energy_wins": len(wins), "total_energy_change_pct": pct(total_new, total_old),
                         **{f"mean_change_pct_{s}": statistics.fmean(g["energy_change_pct"] for g in group
                                                                     if g["workload_groups"] == s) for s in SIZES},
                         **{f"wins_{s}": sum(g["wins_energy"] for g in group if g["workload_groups"] == s)
                            for s in SIZES},
                         "best_case_pct": min(changes), "worst_case_pct": max(changes),
                         "cases_outside_limits": sum(not g["within_limits"] for g in group),
                         "wins_outside_limits": sum(not g["within_limits"] for g in wins),
                         "works_better": (len(wins) > len(group) / 2 and total_new < total_old
                                          and all(g["within_limits"] for g in wins))})
    return rows, verdicts


def lowest(runs):
    per_case = []
    for size, curve in CASES:
        kwh = {p: runs[(size, curve, p)]["summary"]["energy_kwh"] for p in ALL}
        per_case.append({"workload_groups": size, "power_curve": curve, "lowest": min(kwh, key=kwh.get),
                         "lowest_of_original_four": min(ALL[:4], key=kwh.get), **{f"{p}_kwh": kwh[p] for p in ALL}})
    counts = {p: sum(c["lowest"] == p for c in per_case) for p in ALL}
    originals_only = {p: sum(c["lowest_of_original_four"] == p for c in per_case) for p in ALL[:4]}
    return per_case, counts, originals_only


def size_rows(runs, reference="lr_mmt"):
    """Mean % energy change vs LR-MMT by size (mean of the 3 curves), and over all 9 cases."""
    out = []
    for policy in ("lr_mmt_memory", "lr_mmt_same_job", "lr_mmt_memory_same_job", "first_fit"):
        row = {"policy": policy, "reference": reference}
        new_total = old_total = 0.0
        for size in SIZES:
            changes = []
            for curve in CURVES:
                new, old = (runs[(size, curve, p)]["summary"]["energy_kwh"] for p in (policy, reference))
                changes.append(pct(new, old))
                new_total, old_total = new_total + new, old_total + old
            row[f"mean_change_pct_{size}"] = statistics.fmean(changes)
        row["total_energy_change_pct"] = pct(new_total, old_total)
        out.append(row)
    return out


def job_mix(new):
    out = []
    for name in NAMES:
        for size in SIZES:
            mixes = [new[(size, c, name)]["job_mix"] for c in CURVES]
            out.append({"policy": name, "workload_groups": size,
                        "mean_jobs_per_busy_server": statistics.fmean(m["mean_jobs_per_busy_server"] for m in mixes),
                        "single_job_server_share": statistics.fmean(m["single_job_server_share"] for m in mixes)})
    return out


def quality(runs, size=4000):
    return [{"policy": p, **{m: statistics.fmean(runs[(size, c, p)]["summary"][m] for c in CURVES)
                             for m in METRICS}}
            for p in ("lr_mmt", "lr_mmt_same_job", "lr_mmt_memory", "lr_mmt_memory_same_job", "first_fit")]


def splits(runs, size=4000):
    """Exact energy split (RUSHI_Task/accounting.py), each policy vs its original, mean of the 3 curves."""
    out = []
    for base, other in PAIRS:
        parts = defaultdict(list)
        for c in CURVES:
            for k, v in pair_gap(runs[(size, c, base)]["summary"], runs[(size, c, other)]["summary"],
                                 load_curve(c)).items():
                parts[k].append(v)
        out.append({"base": base, "other": other,
                    **{(k[:-2] + "_kwh" if k.endswith("_j") else k): (statistics.fmean(v) / 3.6e6 if k.endswith("_j")
                                                                      else statistics.fmean(v))
                       for k, v in parts.items()}})
    return out


def types(runs, size=4000):
    rows = []
    for policy in NAMES:
        bucket = defaultdict(lambda: defaultdict(list))
        for curve in CURVES:
            for skew, values in runs[(size, curve, policy)]["outcomes_by_task_type"].items():
                for key, value in values.items():
                    bucket[skew][key].append(value)
        for skew in ("balanced", "memory_heavy", "cpu_heavy"):
            values = bucket[skew]
            rows.append({"policy": policy, "task_type": skew,
                         "instances_per_case": statistics.fmean(values["instances"]),
                         "waited_pct": 100 * statistics.fmean(values["delayed_share"]),
                         "mean_wait_s": statistics.fmean(values["mean_wait_s"]),
                         "p95_wait_s": statistics.fmean(values["p95_wait_s"]),
                         "migrated_pct": 100 * statistics.fmean(
                             m / i for m, i in zip(values["migrated_instances"], values["instances"]))})
    return rows


def premise(size=4000, pairs_per_job=20, window_s=300, idle_timeout_s=60, seed=0):
    """Do tasks of the same job finish close together? All tasks of a job are released
    at the same time here, so finish-time gaps equal duration gaps. Compare pairs from the
    same job with pairs of different jobs released in the same 5-minute window. 60 s is
    the simulator's idle timeout; 5 minutes is its controller interval. A diagnostic only:
    no policy uses durations."""
    with (PACKAGE / f"workload_{size}.csv").open(newline="", encoding="utf-8") as f:
        groups = {r["task_group_id"] for r in csv.DictReader(f)}
    by_job, by_window = defaultdict(list), defaultdict(list)
    with (PACKAGE / "instances.csv").open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["task_group_id"] in groups:
                d, t = float(r["duration_s"]), float(r["arrival_time_s"])
                by_job[r["task_group_id"]].append(d)
                by_window[int(t // window_s)].append((r["task_group_id"], d))
    rng = random.Random(seed)
    same, other = [], []
    for durations in by_job.values():
        if len(durations) >= 2:
            for _ in range(min(pairs_per_job, len(durations) - 1)):
                a, b = rng.sample(durations, 2)
                same.append(abs(a - b))
    for members in by_window.values():
        if len({j for j, _ in members}) < 2:
            continue
        for _ in range(min(pairs_per_job * 5, len(members))):
            (ja, a), (jb, b) = rng.sample(members, 2)
            if ja != jb:
                other.append(abs(a - b))
    within = lambda gaps: 100 * sum(g <= idle_timeout_s for g in gaps) / len(gaps)
    return {"workload_groups": size, "seed": seed, "jobs_with_2plus_tasks": sum(len(d) >= 2 for d in by_job.values()),
            "same_job_pairs": len(same), "other_job_pairs": len(other),
            "same_job_median_gap_s": statistics.median(same), "other_job_median_gap_s": statistics.median(other),
            "same_job_within_idle_timeout_pct": within(same), "other_job_within_idle_timeout_pct": within(other)}


def premise_check():
    """Recompute the premise if the prepared inputs are present (they are git-ignored);
    otherwise reuse the committed reports/premise_check.json, so a fresh clone can still
    rebuild every report from committed files."""
    if (PACKAGE / "instances.csv").exists():
        return premise(), True
    print("Prepared inputs not found: using the committed reports/premise_check.json "
          "(prepare the inputs to recompute it; see RUSHI_Task/README.md).")
    return json.loads((REPORTS / "premise_check.json").read_text(encoding="utf-8")), False


def predictions(verdicts, mix):
    """Check each prediction written in DESIGN.md before the runs."""
    v = {r["comparison"]: r for r in verdicts}
    m = {(r["policy"], r["workload_groups"]): r["mean_jobs_per_busy_server"] for r in mix}
    fewer = all(m[(new, s)] < m[(old, s)] for old, new in PAIRS for s in SIZES)
    return [
        ("Mechanism: busy servers hold fewer different jobs, for both policies, at every size", fewer),
        ("S1 is small (within ±1.5% in total) and saves energy",
         abs(v["S1"]["total_energy_change_pct"]) <= 1.5 and v["S1"]["total_energy_change_pct"] < 0),
        ("S2 saves more than S1 on the largest workload",
         v["S2"]["mean_change_pct_4000"] < v["S1"]["mean_change_pct_4000"]),
        ("S5: memory-aware + rule still uses more energy than LR-MMT on the largest workload",
         v["S5"]["mean_change_pct_4000"] > 0),
        ("Side effects small: every S1 and S2 case within the team's limits",
         v["S1"]["cases_outside_limits"] == 0 and v["S2"]["cases_outside_limits"] == 0),
    ]


# ---------- charts ----------

def chart_energy(path, sizes):
    show = ("lr_mmt_memory", "lr_mmt_same_job", "lr_mmt_memory_same_job", "first_fit")
    rows = {r["policy"]: r for r in sizes}
    groups = []
    for size, label in zip(SIZES, ("250 groups (small)", "1,000 groups (medium)", "4,000 groups (large)")):
        groups.append({"label": label, "bars": [
            {"label": LONG[p], "value": rows[p][f"mean_change_pct_{size}"], "colour": COLOURS[p],
             "tip": f"{LONG[p]}, {label}: {signed(rows[p][f'mean_change_pct_{size}'], digits=2)}% vs LR-MMT"}
            for p in show]})
    C.bar_groups(path, "Energy compared with LR-MMT (team's 9 cases)",
                 "Mean change over the 3 server models of each size. Left of 0 = uses less energy than LR-MMT.",
                 groups, [(SHORT[p], COLOURS[p]) for p in show], "% energy change vs LR-MMT",
                 lambda v, tick=False: signed(v, tick) + ("" if tick else "%"),
                 note="Same Alibaba tasks, 64 servers and simulator settings in every run.")


def chart_servers(path, runs, curve="hpe_dl360_gen9", size=4000):
    show = ("lr_mmt", "lr_mmt_memory", "lr_mmt_memory_same_job")
    panels = [{"title": "Servers switched on", "y_format": lambda v: f"{v:.0f}", "series": []},
              {"title": "Average CPU load of servers running work", "y_format": lambda v: f"{100 * v:.0f}%",
               "series": []}]
    for policy in show:
        series = runs[(size, curve, policy)]["time_series"]
        busy = [l for l, n in zip(series["mean_cpu_of_hosts_running_work"], series["hosts_running_work"]) if n]
        blocks = defaultdict(lambda: {"on": [], "cpu": []})
        for t, on, load, n in zip(series["time_s"], series["powered_hosts"],
                                  series["mean_cpu_of_hosts_running_work"], series["hosts_running_work"]):
            block = blocks[int(t // 1800)]
            block["on"].append(on)
            if n:
                block["cpu"].append(load)
        keys = sorted(blocks)
        hours = [(k + 0.5) / 2 for k in keys]
        panels[0]["series"].append({"name": LONG[policy], "short": SHORT[policy], "colour": COLOURS[policy],
                                    "x": hours, "y": [statistics.fmean(blocks[k]["on"]) for k in keys],
                                    "average": statistics.fmean(series["powered_hosts"])})
        panels[1]["series"].append({"name": LONG[policy], "short": SHORT[policy], "colour": COLOURS[policy],
                                    "x": hours, "y": [statistics.fmean(blocks[k]["cpu"]) if blocks[k]["cpu"] else 0.0
                                                      for k in keys],
                                    "average": statistics.fmean(busy)})
    panels[0]["y_max"] = max(max(s["y"]) for s in panels[0]["series"]) * 1.1
    panels[1]["y_max"] = min(1.0, max(max(s["y"]) for s in panels[1]["series"]) * 1.15)
    C.line_panels(path, f"Servers on over the 12 hours (4,000 groups, {CURVE_NAMES[curve]})",
                  "30-minute averages of 5-minute samples. Short ticks on the right mark each policy's 12-hour average.",
                  panels, [(SHORT[p], COLOURS[p]) for p in show], "simulated time")


def chart_split(path, split_rows):
    labels = {("lr_mmt", "lr_mmt_same_job"): "LR-MMT → + rule",
              ("lr_mmt_memory", "lr_mmt_memory_same_job"): "Memory-aware → + rule"}
    parts = (("on_running_work_kwh", "Servers on longer, running work"),
             ("on_without_work_kwh", "Servers on longer, with no work"),
             ("load_dependent_kwh", "Load-dependent power"),
             ("wakeups_kwh", "Wake-ups (full power for 10 s each)"),
             ("total_kwh", "Net change"))
    groups = []
    for key, label in parts:
        bars = []
        for row in split_rows:
            value, name = row[key], labels[(row["base"], row["other"])]
            colour = C.NET if key == "total_kwh" else (C.ADDS if value > 0 else C.SAVES)
            bars.append({"label": name, "value": value, "colour": colour,
                         "tip": f"{label}, {name}: {signed(value, digits=3)} kWh"})
        groups.append({"label": label, "bars": bars})
    C.bar_groups(path, "Where the energy difference comes from (4,000 groups)",
                 "Mean over the 3 server models, split exactly by what the simulator charges for each server-second.",
                 groups, [("adds energy", C.ADDS), ("saves energy", C.SAVES), ("net change", C.NET)],
                 "kWh change when the rule is added", lambda v, tick=False: signed(v, tick, 2), width=1040,
                 note="Components add up exactly to the net change (checked per case).")


def chart_types(path, rows):
    show = ("lr_mmt", "lr_mmt_same_job", "lr_mmt_memory", "lr_mmt_memory_same_job")   # before/after pairs
    order = ("balanced", "memory_heavy", "cpu_heavy")
    series = [{"name": SHORT[p], "colour": COLOURS[p],
               "values": [next(r["waited_pct"] for r in rows if r["policy"] == p and r["task_type"] == t)
                          for t in order]} for p in show]
    columns(path, "Share of tasks that had to wait, by task type (4,000 groups)",
            "Mean over the 3 server models. A task waits if no running server has room or its server is waking.",
            [TYPE_NAMES[t] for t in order], series, "tasks that waited", lambda v: f"{v:.0f}%")


def columns(path, title, subtitle, categories, series, y_label, y_format, width=980):
    """Grouped columns whose axis always reaches the tallest bar."""
    left, right_pad, top, plot_h = 70, 30, 132, 260
    height = top + plot_h + 70
    y_max = max(v for s in series for v in s["values"])
    ticks = C.nice_ticks(0, y_max, 5)
    if ticks[-1] < y_max:
        ticks.append(ticks[-1] + (ticks[1] - ticks[0]))
    y_top = ticks[-1]
    plot_w = width - left - right_pad
    band = plot_w / len(categories)
    bar_w = min(24.0, (band * 0.6 - 2 * (len(series) - 1)) / len(series))
    y_base = top + plot_h
    sy = lambda v: y_base - v / y_top * plot_h
    parts = [C.text(24, 34, title, 20, C.INK, weight="bold"), C.text(24, 58, subtitle, 13, C.INK2)]
    parts += C.legend(24, 88, [(s["name"], s["colour"]) for s in series])
    for t in ticks:
        parts.append(f'<line x1="{left}" y1="{sy(t):.1f}" x2="{left + plot_w}" y2="{sy(t):.1f}" '
                     f'stroke="{C.GRID}" stroke-width="1"/>')
        parts.append(C.text(left - 8, sy(t) + 4, y_format(t), 12, C.MUTED, "end"))
    group_w = len(series) * bar_w + 2 * (len(series) - 1)
    for i, category in enumerate(categories):
        cx = left + band * i + band / 2
        x = cx - group_w / 2
        for s in series:
            value = s["values"][i]
            parts.append(C.vbar(x, y_base, sy(value), bar_w, s["colour"], f'{s["name"]}, {category}: {y_format(value)}'))
            parts.append(C.text(x + bar_w / 2, sy(value) - 6, y_format(value), 12, C.INK2, "middle"))
            x += bar_w + 2
        parts.append(C.text(cx, y_base + 18, category, 12, C.INK2, "middle"))
    parts.append(f'<line x1="{left}" y1="{y_base}" x2="{left + plot_w}" y2="{y_base}" stroke="{C.AXIS}" stroke-width="1"/>')
    parts.append(C.text(left + plot_w / 2, y_base + 44, y_label, 12, C.MUTED, "middle"))
    desc = subtitle + " " + "; ".join(
        f'{c}: ' + ", ".join(f'{s["name"]} {y_format(s["values"][i])}' for s in series) for i, c in enumerate(categories))
    path.write_text(C.document(width, height, title, desc, parts), encoding="utf-8", newline="\n")


# ---------- report ----------

def report(result):
    v, t, fmt = result["verdicts"], md_table, fmt_pct
    per_case, counts, originals_only = result["lowest"]
    pr = result["premise"]
    outside = [r for r in result["rows"] if not r["within_limits"]]
    words = {"pressure": lambda r: f"pressure {signed(100 * r['pressure_change'], digits=2)} points (limit +1.00)",
             "mean_wait_s": lambda r: f"mean wait {signed(r['mean_wait_change_s'], digits=2)} s",
             "p95_wait_s": lambda r: f"P95 wait {signed(r['p95_wait_change_s'], digits=2)} s"}
    lines = ["# The same-job rule on the team's 9 cases", "",
             "**Owner:** Rushi Jhala (D5 extension). Design, rule, comparisons and success criteria: "
             "[DESIGN.md](../DESIGN.md), fixed before any run. Generated by `python -m RUSHI_Task.same_job.analyze`. "
             "A from-scratch explanation is in [the guide](../../guide/EcoSched_Same_Job_Rule_Guide.pdf). "
             "Negative = less energy.", "",
             "**Data: only the team's.** The same 9 cases as `BASELINE_Comparison` (250 / 1,000 / 4,000 groups × 3 "
             "SPECpower curves), the same tasks, 64 hosts and simulator settings. First Fit and Best Fit use the team's "
             "committed results. This is an extension next to the frozen active comparison (AGENTS.md): it adds two "
             "policies and changes no workload, setting or existing result.", "",
             "## Verdicts", "",
             t(["ID", "Comparison", "Energy wins", "Total energy", *[f"{s:,}" for s in SIZES], "Outside limits",
                "Works better?"],
               [[r["comparison"], f"{LONG[r['policy']]} vs {LONG[r['reference']]}",
                 f"{r['energy_wins']}/{r['cases']}", fmt(r["total_energy_change_pct"]),
                 *[fmt(r[f"mean_change_pct_{s}"]) for s in SIZES], r["cases_outside_limits"],
                 "**yes**" if r["works_better"] else "no"] for r in v],
               ["---", "---", "---:", "---:", *["---:"] * len(SIZES), "---:", "---"]), "",
             "Size columns are the mean change over the 3 server models. *Works better* = less energy in more than "
             "half of the 9 cases, lower total energy, and every win within the team's limits (mean and P95 wait "
             "+max(1 s, 5%), pressure +0.01, from `POLICY_Improvement/config.json`).", "",
             *[f"- Outside the limits: {r['comparison']}, {r['workload_groups']:,} groups, "
               f"{CURVE_NAMES[r['power_curve']]}: energy {fmt(r['energy_change_pct'])}, but "
               + ", ".join(words[f](r) for f in r["limit_failures"].split(";")) + "."
               for r in outside], "",
             "## Least energy in each case", "",
             t(["Algorithm", "Lowest energy (of 6)", "Lowest energy (original 4 only)"],
               [[LONG[p], f"{counts[p]} of 9", f"{originals_only[p]} of 9" if p in originals_only else "–"]
                for p in ALL], ["---", "---:", "---:"]), "",
             t(["Groups", "Server model", *[LONG[p] for p in ALL]],
               [[f"{c['workload_groups']:,}", CURVE_NAMES[c["power_curve"]],
                 *[(f"**{c[p + '_kwh']:.3f}**" if c["lowest"] == p else f"{c[p + '_kwh']:.3f}") for p in ALL]]
                for c in per_case], ["---:", "---"] + ["---:"] * len(ALL)), "",
             "kWh per run; bold = lowest in that case.", "",
             "## Energy compared with LR-MMT, by size (mean of the 3 server models)", "",
             t(["Algorithm", *[f"{s:,} groups" for s in SIZES], "All 9 cases"],
               [[LONG[r["policy"]], *[fmt(r[f"mean_change_pct_{s}"]) for s in SIZES],
                 fmt(r["total_energy_change_pct"])] for r in result["sizes"]],
               ["---", *["---:"] * len(SIZES), "---:"]), "",
             "![Energy compared with LR-MMT](energy_vs_lr_mmt_by_size.svg)", "",
             "## Did servers hold fewer different jobs? (mean of the 3 server models)", "",
             t(["Policy", "Groups", "Different jobs per busy server", "Servers running a single job"],
               [[LONG[m["policy"]], f"{m['workload_groups']:,}", f"{m['mean_jobs_per_busy_server']:.2f}",
                 f"{100 * m['single_job_server_share']:.1f}%"] for m in result["job_mix"]],
               ["---", "---:", "---:", "---:"]), "",
             "## Largest workload: energy, waiting, crowding (mean of the 3 server models)", "",
             t(["Policy", "kWh", "Mean wait (s)", "P95 wait (s)", "Pressure", "Migrations", "Wake-ups", "Servers on"],
               [[LONG[x["policy"]], f"{x['energy_kwh']:.3f}", f"{x['mean_wait_s']:.2f}", f"{x['p95_wait_s']:.1f}",
                 f"{100 * x['overload_host_time_fraction']:.2f}%", f"{x['migrations']:,.0f}", f"{x['wakeups']:,.0f}",
                 f"{x['mean_active_hosts']:.2f}"] for x in result["quality"]],
               ["---", "---:", "---:", "---:", "---:", "---:", "---:", "---:"]), "",
             "![Servers on over time](servers_over_time.svg)", "",
             "## Where the difference comes from (4,000 groups, each policy vs its original, kWh)", "",
             "The exact split from D5 (`RUSHI_Task/accounting.py`); the parts add up to the net change.", "",
             t(["Policy", "On longer, running work", "On longer, no work", "Load-dependent", "Wake-ups", "Net",
                "Wake-ups before → after"],
               [[LONG[s["other"]], *[signed(s[k], digits=3) for k in
                                      ("on_running_work_kwh", "on_without_work_kwh", "load_dependent_kwh",
                                       "wakeups_kwh", "total_kwh")],
                 f"{s['base_wakeups']:,.0f} → {s['other_wakeups']:,.0f}"] for s in result["splits"]],
               ["---", "---:", "---:", "---:", "---:", "---:", "---:"]), "",
             "![Where the difference comes from](where_the_difference_comes_from.svg)", "",
             "## By task type (4,000 groups, mean of the 3 server models)", "",
             t(["Policy", "Task type", "Tasks per case", "Waited", "Mean wait (s)", "Migrated"],
               [[LONG[r["policy"]], TYPE_NAMES[r["task_type"]], f"{r['instances_per_case']:,.0f}",
                 f"{r['waited_pct']:.1f}%", f"{r['mean_wait_s']:.2f}", f"{r['migrated_pct']:.2f}%"]
                for r in result["types"]],
               ["---", "---", "---:", "---:", "---:", "---:"]), "",
             "![Waits by task type](waits_by_task_type.svg)", "",
             "## Premise check: do tasks of the same job finish close together? (team's 4,000-group sample)", "",
             "All tasks of a job are released at the same moment here, so the gap between their finish times is "
             "the gap between their durations. Pairs from the same job are compared with pairs from different "
             "jobs released in the same 5-minute window. 60 s is the simulator's idle timeout.", "",
             t(["Pairs of tasks", "Median finish gap", "Finish within 60 s of each other"],
               [["Same job", f"{pr['same_job_median_gap_s']:.0f} s", f"{pr['same_job_within_idle_timeout_pct']:.1f}%"],
                ["Different jobs, same 5 minutes", f"{pr['other_job_median_gap_s']:.0f} s",
                 f"{pr['other_job_within_idle_timeout_pct']:.1f}%"]],
               ["---", "---:", "---:"]), "",
             f"Based on {pr['same_job_pairs']:,} same-job pairs from {pr['jobs_with_2plus_tasks']:,} jobs and "
             f"{pr['other_job_pairs']:,} different-job pairs (fixed random seed {pr['seed']}). A diagnostic only: "
             "no policy sees durations.", "",
             "## Predictions (from DESIGN.md, written before the runs)", "",
             t(["Prediction", "Held?"], [[text, "yes" if held else "**no**"] for text, held in result["predictions"]],
               ["---", "---"]), "",
             "## Checks", "",
             f"- {result['status']['present']} of {result['status']['expected']} runs present, all passing "
             "`validate_run`, all on the committed code (SHA-256 recorded in every run).",
             f"- The {result['status']['originals_expected']} re-runs of Rohan's two policies (with the read-only "
             "observer) reproduced the team's committed results in every field.",
             "- With the rule off, the new code is Rohan's policy exactly (unit test).",
             "- Every energy split adds up to the simulator's own total (`pair_gap` raises otherwise).", "",
             "## Limits", "",
             "The same 9 cases were used in D5, so this is not a test on unseen data; the guards are that nothing was "
             "tuned and each policy ran once per case. Simulated requested resources and whole-server SPECpower "
             "curves, one 12-hour trace. The sizes are nested and the curves replay the same tasks, so the 9 cases "
             "are not independent replications. Pressure is a requested-resource warning sign, not a measured "
             "slowdown.", ""]
    (REPORTS / "REPORT.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def build():
    runs, new, status = load()
    rows, verdicts = compare(runs)
    mix = job_mix(new)
    checked, recomputed = premise_check()
    result = {"status": status, "runs": runs, "rows": rows, "verdicts": verdicts, "job_mix": mix,
              "lowest": lowest(runs), "sizes": size_rows(runs), "quality": quality(runs), "splits": splits(runs),
              "types": types(runs), "premise": checked, "predictions": predictions(verdicts, mix)}
    REPORTS.mkdir(parents=True, exist_ok=True)
    write_csv(REPORTS / "comparisons.csv", rows)
    write_csv(REPORTS / "verdicts.csv", verdicts)
    write_csv(REPORTS / "energy_by_case.csv", result["lowest"][0])
    write_csv(REPORTS / "energy_vs_lr_mmt_by_size.csv", result["sizes"])
    write_csv(REPORTS / "job_mix.csv", mix)
    write_csv(REPORTS / "quality_4000.csv", result["quality"])
    write_csv(REPORTS / "energy_split_4000.csv", result["splits"])
    write_csv(REPORTS / "by_task_type_4000.csv", result["types"])
    if recomputed:
        (REPORTS / "premise_check.json").write_text(json.dumps(result["premise"], indent=2) + "\n",
                                                    encoding="utf-8", newline="\n")
    (REPORTS / "validation.json").write_text(json.dumps(
        {"passed": True, **status, "data": "team's prepared inputs only (RAW_Alibaba/prepared)",
         "limits_source": "POLICY_Improvement/config.json success_limits", "limits": LIMITS,
         "energy_split_checked": "RUSHI_Task.accounting.pair_gap raises if parts do not add up",
         "code_sha256": code_hashes(),
         "predictions": [{"prediction": p, "held": h} for p, h in result["predictions"]]},
        indent=2) + "\n", encoding="utf-8", newline="\n")
    chart_energy(REPORTS / "energy_vs_lr_mmt_by_size.svg", result["sizes"])
    chart_servers(REPORTS / "servers_over_time.svg", runs)
    chart_split(REPORTS / "where_the_difference_comes_from.svg", result["splits"])
    chart_types(REPORTS / "waits_by_task_type.svg", result["types"])
    report(result)
    return result


def main():
    result = build()
    for r in result["verdicts"]:
        print(f"{r['comparison']} {r['policy']} vs {r['reference']}: wins {r['energy_wins']}/9, "
              f"total {r['total_energy_change_pct']:+.3f}%, outside limits {r['cases_outside_limits']}, "
              f"works better: {r['works_better']}")
    print("lowest of 6:", result["lowest"][1], " originals only:", result["lowest"][2])
    for text, held in result["predictions"]:
        print("prediction", "HELD" if held else "NOT HELD", "-", text)


if __name__ == "__main__":
    main()
