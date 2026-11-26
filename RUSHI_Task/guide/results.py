"""Values and tables for Parts C4 and E-F of the guide, from RUSHI_Task/same_job/analyze.py."""
from RUSHI_Task.same_job import analyze as S

CHARTS = ("energy_vs_lr_mmt_by_size.svg", "servers_over_time.svg", "where_the_difference_comes_from.svg",
          "waits_by_task_type.svg")
QUESTIONS = {"S1": "Does the rule improve LR-MMT?",
             "S2": "Does the rule improve the memory-aware version?",
             "S3": "Does LR-MMT + rule beat First Fit?",
             "S4": "Does memory-aware + rule beat First Fit?",
             "S5": "Does the proposal (memory-aware + rule) beat LR-MMT?",
             "S6": "With the rule on both, does caring about memory help?"}
YES, NO = '<span class="yes">yes</span>', '<span class="no">no</span>'
SIZE_WORDS = {250: "small", 1000: "medium", 4000: "largest"}


def pct(value, digits=2):
    return S.fmt_pct(value, digits)


def points(fraction_change):
    return f"{100 * fraction_change:.2f}"


def values(result):
    v, t = {}, {}
    ver = {r["comparison"]: r for r in result["verdicts"]}
    v.update({cid: {"wins": r["energy_wins"], "total": pct(r["total_energy_change_pct"]),
                    "large": pct(r["mean_change_pct_4000"]), "works": r["works_better"],
                    "outside": r["cases_outside_limits"]} for cid, r in ver.items()})
    t["verdict_table"] = S.md_table(
        ["ID", "Question", "Energy wins", "Total energy", "Largest workload", "Cases outside limits", "Works better?"],
        [[r["comparison"], QUESTIONS[r["comparison"]], f"{r['energy_wins']} of {r['cases']}",
          pct(r["total_energy_change_pct"]), pct(r["mean_change_pct_4000"]), r["cases_outside_limits"],
          YES if r["works_better"] else NO] for r in result["verdicts"]],
        ["---", "---", "---:", "---:", "---:", "---:", "---"])

    # Cases outside the team's limits, in words (S2 is the main comparison that has one).
    rows = result["rows"]
    s2_out = [r for r in rows if r["comparison"] == "S2" and not r["within_limits"]]
    if not s2_out:
        v["s2_fail_text"] = "Every S2 case stayed within the team's limits."
    else:
        failed = {f for r in s2_out for f in r["limit_failures"].split(";")}
        if failed != {"pressure"}:
            raise ValueError(f"Guide text assumes S2 fails only on pressure: {failed}")
        others = [r for r in rows if r["comparison"] == "S2" and r["within_limits"] and r["workload_groups"] == 4000]
        cases = "; ".join(f"{SIZE_WORDS[r['workload_groups']]} workload, {S.CURVE_NAMES[r['power_curve']]}: "
                          f"+{points(r['pressure_change'])} points" for r in s2_out)
        v["s2_fail_text"] = (
            f"in {len(s2_out)} of the 9 cases ({cases}), crowding rose by more than the team allows "
            f"(+1.00 points)."
            + (f" The other large cases rose by "
               + " and ".join(f"+{points(r['pressure_change'])}" for r in others) + " points, just inside."
               if others else ""))
        v["s2_over_by"] = f"{max(100 * (r['pressure_change'] - S.LIMITS['pressure_absolute_increase']) for r in s2_out):.2f}"
    v["s2_outside"] = len(s2_out)

    per_case, counts, originals_only = result["lowest"]
    t["lowest_table"] = S.md_table(
        ["Algorithm", "Least energy, original four only", "Least energy, all six"],
        [[S.LONG[p], f"{originals_only[p]} of 9" if p in originals_only else "–", f"{counts[p]} of 9"] for p in S.ALL],
        ["---", "---:", "---:"])
    v["ff_before"] = originals_only["first_fit"]
    v["ff_after"] = counts["first_fit"]
    v["mem_rule_lowest"] = counts["lr_mmt_memory_same_job"]
    sizes_won = sorted({c["workload_groups"] for c in per_case if c["lowest"] == "lr_mmt_memory_same_job"})
    v["mem_rule_lowest_sizes"] = " and ".join(SIZE_WORDS[s] for s in sizes_won)
    ff_sizes = sorted({c["workload_groups"] for c in per_case if c["lowest"] == "first_fit"})
    v["ff_after_sizes"] = " and ".join(SIZE_WORDS[s] for s in ff_sizes)

    sizes = {r["policy"]: r for r in result["sizes"]}
    t["size_table"] = S.md_table(
        ["Algorithm (vs LR-MMT)", "Small (250)", "Medium (1,000)", "Large (4,000)", "All 9 cases"],
        [[S.LONG[p]] + [pct(sizes[p][f"mean_change_pct_{s}"]) for s in S.SIZES]
         + [pct(sizes[p]["total_energy_change_pct"])] for p in sizes],
        ["---", "---:", "---:", "---:", "---:"])
    v["size"] = {p: {**{f"s{s}": pct(r[f"mean_change_pct_{s}"]) for s in S.SIZES},
                     "total": pct(r["total_energy_change_pct"])} for p, r in sizes.items()}

    labels = {"lr_mmt_same_job": "LR-MMT", "lr_mmt_memory_same_job": "Memory-aware LR-MMT"}
    split = {r["other"]: r for r in result["splits"]}
    t["split_table"] = S.md_table(
        ["Rule added to", "Time on, running work", "Time on, no work", "Load-dependent", "Wake-ups", "Net (kWh)"],
        [[labels[p]] + [S.signed(split[p][k], digits=2) for k in
                        ("on_running_work_kwh", "on_without_work_kwh", "load_dependent_kwh", "wakeups_kwh",
                         "total_kwh")] for p in labels],
        ["---", "---:", "---:", "---:", "---:", "---:"])
    mem = split["lr_mmt_memory_same_job"]
    v["split"] = {"mem_net": f"{-mem['total_kwh']:.2f}", "mem_running": f"{-mem['on_running_work_kwh']:.2f}",
                  "mem_running_share": f"{100 * mem['on_running_work_kwh'] / mem['total_kwh']:.0f}%",
                  "mem_wakes": f"{mem['base_wakeups']:,.0f} → {mem['other_wakeups']:,.0f}",
                  "mem_wake_cost": f"{mem['wakeups_kwh']:+.2f}".replace("-", "−"),
                  "lr_net": f"{-split['lr_mmt_same_job']['total_kwh']:.2f}"}

    mix = {(m["policy"], m["workload_groups"]): m for m in result["job_mix"]}
    t["mix_table"] = S.md_table(
        ["Workload", "LR-MMT", "LR-MMT + rule", "Memory-aware", "Memory-aware + rule"],
        [[f"{s:,} groups"] + [f"{mix[(p, s)]['mean_jobs_per_busy_server']:.2f}" for p in
                              ("lr_mmt", "lr_mmt_same_job", "lr_mmt_memory", "lr_mmt_memory_same_job")]
         for s in S.SIZES],
        ["---", "---:", "---:", "---:", "---:"])
    big = lambda p: mix[(p, 4000)]
    v["mix"] = {"lr_before": f"{big('lr_mmt')['mean_jobs_per_busy_server']:.2f}",
                "lr_after": f"{big('lr_mmt_same_job')['mean_jobs_per_busy_server']:.2f}",
                "mem_before": f"{big('lr_mmt_memory')['mean_jobs_per_busy_server']:.2f}",
                "mem_after": f"{big('lr_mmt_memory_same_job')['mean_jobs_per_busy_server']:.2f}",
                "mem_single_before": f"{100 * big('lr_mmt_memory')['single_job_server_share']:.0f}%",
                "mem_single_after": f"{100 * big('lr_mmt_memory_same_job')['single_job_server_share']:.0f}%"}

    q = {r["policy"]: r for r in result["quality"]}
    t["quality_table"] = S.md_table(
        ["Algorithm", "Energy (kWh)", "Mean wait", "P95 wait", "Pressure", "Migrations", "Wake-ups", "Servers on"],
        [[S.LONG[p], f"{q[p]['energy_kwh']:.2f}", f"{q[p]['mean_wait_s']:.1f} s", f"{q[p]['p95_wait_s']:.0f} s",
          f"{100 * q[p]['overload_host_time_fraction']:.1f}%", f"{q[p]['migrations']:,.0f}", f"{q[p]['wakeups']:,.0f}",
          f"{q[p]['mean_active_hosts']:.1f}"] for p in q],
        ["---", "---:", "---:", "---:", "---:", "---:", "---:", "---:"])
    v["servers"] = {p: f"{q[p]['mean_active_hosts']:.1f}" for p in q}
    v["pressure"] = {p: f"{100 * q[p]['overload_host_time_fraction']:.1f}%" for p in q}
    v["wait"] = {p: f"{q[p]['mean_wait_s']:.1f}" for p in q}
    v["wait_change_lr"] = S.signed(q["lr_mmt_same_job"]["mean_wait_s"] - q["lr_mmt"]["mean_wait_s"], digits=1)
    v["wait_change_mem"] = S.signed(q["lr_mmt_memory_same_job"]["mean_wait_s"] - q["lr_mmt_memory"]["mean_wait_s"],
                                    digits=1)
    v["extra_servers"] = f"{q['lr_mmt_memory']['mean_active_hosts'] - q['lr_mmt_memory_same_job']['mean_active_hosts']:.0f}"
    v["migrations_change"] = {p: pct(S.pct(q[n]["migrations"], q[p]["migrations"]), 0)
                              for p, n in (("lr_mmt", "lr_mmt_same_job"), ("lr_mmt_memory", "lr_mmt_memory_same_job"))}
    v["migrations_fall"] = all(q[n]["migrations"] < q[p]["migrations"]
                               for p, n in (("lr_mmt", "lr_mmt_same_job"), ("lr_mmt_memory", "lr_mmt_memory_same_job")))

    types = {(r["policy"], r["task_type"]): r for r in result["types"]}
    t["types_table"] = S.md_table(
        ["Task type", "Algorithm", "Tasks per case", "Waited", "Mean wait", "Moved at least once"],
        [[S.TYPE_NAMES[k], S.LONG[p], f"{types[(p, k)]['instances_per_case']:,.0f}",
          f"{types[(p, k)]['waited_pct']:.1f}%", f"{types[(p, k)]['mean_wait_s']:.1f} s",
          f"{types[(p, k)]['migrated_pct']:.1f}%"]
         for k in ("balanced", "memory_heavy", "cpu_heavy")
         for p in ("lr_mmt", "lr_mmt_same_job", "lr_mmt_memory", "lr_mmt_memory_same_job")],
        ["---", "---", "---:", "---:", "---:", "---:"])
    change = {(p, k): types[(n, k)]["waited_pct"] - types[(p, k)]["waited_pct"]
              for p, n in (("lr_mmt", "lr_mmt_same_job"), ("lr_mmt_memory", "lr_mmt_memory_same_job"))
              for k in ("balanced", "memory_heavy", "cpu_heavy")}
    v["types"] = {f"{p}_{k}": {"before": f"{types[(p, k)]['waited_pct']:.1f}%",
                               "after": f"{types[(n, k)]['waited_pct']:.1f}%",
                               "change": S.signed(change[(p, k)], digits=1)}
                  for p, n in (("lr_mmt", "lr_mmt_same_job"), ("lr_mmt_memory", "lr_mmt_memory_same_job"))
                  for k in ("balanced", "memory_heavy", "cpu_heavy")}
    v["types_lr_max"] = f"{max(abs(change[('lr_mmt', k)]) for k in ('balanced', 'memory_heavy', 'cpu_heavy')):.1f}"
    kinds = ("balanced", "memory_heavy", "cpu_heavy")
    wait_shift = max(abs(types[(n, k)]["mean_wait_s"] - types[(p, k)]["mean_wait_s"]) for k in kinds
                     for p, n in (("lr_mmt", "lr_mmt_same_job"), ("lr_mmt_memory", "lr_mmt_memory_same_job")))
    if not (all(c > 0 for c in change.values()) and types[("lr_mmt_memory_same_job", "memory_heavy")]["waited_pct"]
            < types[("lr_mmt", "memory_heavy")]["waited_pct"]):
        raise ValueError("The task-type sentence no longer matches the data; rewrite it")
    mem = lambda k: f"from {v['types'][f'lr_mmt_memory_{k}']['before']} to {v['types'][f'lr_mmt_memory_{k}']['after']}"
    v["types_sentence"] = (
        "With the rule, more tasks have to wait at all, because fewer servers are kept on and more of them must "
        f"be woken (E4). For the memory-aware version, the share that waited rises {mem('balanced')} for balanced "
        f"tasks and {mem('memory_heavy')} for memory-heavy tasks; for LR-MMT it rises by at most "
        f"{v['types_lr_max']} points. The waits stay short: no task type's mean wait changes by more than "
        f"{wait_shift:.2f} s. Memory-aware + rule still makes fewer tasks wait than LR-MMT "
        f"({types[('lr_mmt_memory_same_job', 'memory_heavy')]['waited_pct']:.1f}% against "
        f"{types[('lr_mmt', 'memory_heavy')]['waited_pct']:.1f}% of memory-heavy tasks).")

    held = result["predictions"]
    t["predictions_table"] = S.md_table(
        ["Prediction, written before the first run", "Did it hold?"],
        [[text, "**yes**" if ok else "**no**"] for text, ok in held], ["---", "---"])
    v["pred_held"] = sum(ok for _, ok in held)
    v["pred_total"] = len(held)

    pr = result["premise"]
    v["premise"] = {"same_gap": f"{pr['same_job_median_gap_s']:.0f} s", "other_gap": f"{pr['other_job_median_gap_s']:.0f} s",
                    "same_within": f"{pr['same_job_within_idle_timeout_pct']:.0f}%",
                    "other_within": f"{pr['other_job_within_idle_timeout_pct']:.0f}%",
                    "pairs": f"{pr['same_job_pairs']:,}", "jobs": f"{pr['jobs_with_2plus_tasks']:,}"}
    v["runs"] = result["status"]["expected"]
    v["originals_reproduced"] = result["status"]["originals_reproduced"]

    s1, s2 = ver["S1"], ver["S2"]
    penalty = [S.pct(result["runs"][(4000, c, "lr_mmt_memory")]["summary"]["energy_kwh"],
                     result["runs"][(4000, c, "lr_mmt")]["summary"]["energy_kwh"]) for c in S.CURVES]
    v["story"] = (
        f"The memory-aware LR-MMT our proposal promised used {min(penalty):.0f}–{max(penalty):.0f}% more energy than "
        "plain LR-MMT on the team's largest workload, because its balance score spreads tasks onto extra servers "
        "(my D5 analysis). "
        "This guide adds one new placement rule: put each task next to tasks of its own job, because a server can "
        "only sleep when its last task leaves, and in this trace tasks of the same job finish a median of "
        f"{v['premise']['same_gap']} apart. "
        "The rule needs no prediction and adds no tuned numbers, and we fixed the plan in git before running it "
        "once on the team's own 9 cases. "
        f"It made both algorithms use less energy in all 9 cases: {pct(s1['total_energy_change_pct'])} for LR-MMT "
        f"and {pct(s2['total_energy_change_pct'])} for the "
        f"memory-aware version ({pct(s2['mean_change_pct_4000'], 1)} on the largest workload). "
        f"With the rule, the memory-aware version used the least energy of all six algorithms in "
        f"{v['mem_rule_lowest']} of the 9 cases, but First Fit still wins the largest workload, and one large case "
        "went just over the team's crowding limit. "
        "This is a simulation of one 12-hour trace with the same data used throughout, so the results are "
        "promising rather than proven.")
    missed = [text for text, ok in held if not ok]
    if not (s1["energy_wins"] == s2["energy_wins"] == 9 and v["s2_outside"] == 1
            and len(missed) == 1 and missed[0].startswith("Side effects")):
        raise ValueError("The guide's text no longer matches the results; rewrite it")
    return {"v": v, "t": t, "charts": list(CHARTS)}
