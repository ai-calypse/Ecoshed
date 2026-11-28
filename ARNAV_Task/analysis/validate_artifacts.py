"""Validate committed research evidence; normal mode is offline, --strict checks lineage."""
import argparse
import itertools
import json
import math
from pathlib import Path

from .artifacts import (ArtifactError, ResearchArtifacts, ROOT, POLICIES, PRIMARY, SIZES, CURVES,
                        index_rows, require_keys, run_key, output_path)
from .metrics import METRICS, SKEW_METRICS, definitions, number, wh_per_completed_instance, energy_reduction
from .provenance import assess, reconciliation_markdown, sha256


def equal(actual, expected, label):
    if actual is None or expected is None:
        if actual is not expected:
            raise ArtifactError(f"{label}: missing value differs ({actual!r} != {expected!r})")
    elif (isinstance(actual, bool) or not isinstance(actual, (int, float))
          or not math.isfinite(actual) or not math.isfinite(expected)
          or not math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-8)):
        raise ArtifactError(f"{label}: {actual!r} != {expected!r}")


def require(condition, message):
    if not condition:
        raise ArtifactError(message)


def finite_tree(value, label):
    if isinstance(value, float) and not math.isfinite(value):
        raise ArtifactError(f"Nonfinite value in {label}")
    if isinstance(value, dict):
        for key, item in value.items():
            finite_tree(item, f"{label}.{key}")
    elif isinstance(value, (list, tuple)):
        for item in value:
            finite_tree(item, label)


def _run_check(a, r, workloads):
    key = run_key(r)
    finite_tree(r, str(key))
    number(r["workload_groups"], "workload_groups", integer=True)
    require(r["data_source"] == a.manifest["data_source"] == "fresh_user_archive_alibaba_v2017",
            "Run is not the independent Alibaba raw study")
    require(r["synthetic_workload"] is False and r["uses_yaksh_prepared_inputs"] is False
            and r["fresh_raw_archive_processing"] is True, "Wrong recorded study provenance")
    require(r["runtime_model"] == a.raw_config["runtime_model"], "Runtime model changed")
    require(r["config"] == a.manifest["config"]["simulation"] == a.raw_config["simulation"],
            "Simulation settings differ")
    count = workloads[r["workload_groups"]]["instances"]
    for name in ("arrived_instances", "started_instances", "completed_instances", "rejected_instances",
                 "unfinished_instances", "arrived_task_groups", "completed_task_groups", "unfinished_task_groups"):
        number(r[name], name, integer=True)
    for name in ("arrived_instances", "started_instances", "completed_instances"):
        equal(r[name], count, name)
    for name in ("arrived_task_groups", "completed_task_groups"):
        equal(r[name], r["workload_groups"], name)
    for name in ("rejected_instances", "unfinished_instances", "unfinished_task_groups", "capacity_violation_host_seconds"):
        equal(r[name], 0, name)
    require(r["validation"]["passed"] is True and r["validation"]["full_drain"] is True,
            "Recorded run validation failed")
    equal(r["validation"]["checked_outcomes"], count, "validated outcome count")
    for name in METRICS:
        if r.get(name) is not None:
            number(r[name], name, integer=name in {"completed_instances", "rejected_instances", "unfinished_instances",
                                                   "migrations", "peak_active_hosts"},
                   maximum=1 if name in {"overload_host_time_fraction", "mean_fragmentation_index"} else None)
    for name in ("energy_j", "energy_kwh", "completed_instances", "stop_time_s"):
        number(r[name], name)
        require(r[name] > 0, f"{name} must be positive for a completed study run")
    equal(r["energy_kwh"], r["energy_j"] / 3_600_000, "joules to kWh")
    if r.get("wh_per_completed_instance") is not None:
        equal(r["wh_per_completed_instance"], wh_per_completed_instance(r), "Wh/completed instance")
    require(len(r["host_energy_j"]) == a.raw_config["host_count"], "Host energy coverage differs")
    for host, value in r["host_energy_j"].items():
        number(value, f"host energy {host}")
    equal(sum(r["host_energy_j"].values()), r["energy_j"], "per-host energy sum")
    parts = ("active_energy_j", "sleep_energy_j", "waking_energy_j",
             "wake_transition_extra_energy_j", "migration_extra_energy_j")
    for name in parts:
        number(r[name], name)
    equal(sum(r[name] for name in parts), r["energy_j"], "energy component sum")
    hosts = a.raw_config["host_count"]
    if r.get("mean_active_hosts") is not None:
        equal(r["mean_active_hosts"], r["active_host_seconds"] / r["stop_time_s"], "time-weighted mean active hosts")
    require(r.get("peak_active_hosts", hosts) <= hosts, "Peak hosts exceed pool")
    if r.get("mean_active_hosts") is not None and r.get("peak_active_hosts") is not None:
        require(r["mean_active_hosts"] <= r["peak_active_hosts"], "Mean active hosts exceed peak")
    if r.get("overload_host_time_fraction") is not None:
        equal(r["overload_host_time_fraction"], r["overload_host_seconds"] / (hosts * r["stop_time_s"]),
              "reservation-pressure fraction")
    equal(r["drain_time_s"], max(0, r["stop_time_s"] - r["config"]["arrival_window_s"]), "drain time")
    require(r["stop_time_s"] >= r["config"]["arrival_window_s"], "Run stops before horizon")
    if r.get("p95_wait_s") is not None and r.get("max_wait_s") is not None:
        require(r["p95_wait_s"] <= r["max_wait_s"], "P95 wait exceeds maximum wait")
    curve = a.curve_data["curves"][r["power_curve"]]
    require(r["power_source"] == curve["source"], "SPECpower source differs")


def _pairs_check(a):
    cases = set(itertools.product(SIZES, CURVES))
    ix = index_rows(a.primary_pairs, "primary pairs", ("workload_groups", "power_curve"))
    require_keys(ix, cases, "nine primary LR-MMT pairs")
    for case, row in ix.items():
        cpu, mem = (a.index[(*case, policy)] for policy in PRIMARY)
        equal(row["cpu_energy_kwh"], cpu["energy_kwh"], "primary CPU energy")
        equal(row["proposed_energy_kwh"], mem["energy_kwh"], "primary memory energy")
        equal(-row["proposed_energy_increase_pct"], energy_reduction(mem, cpu), "primary reduction sign")
        require(row["proposed_energy_win"] == (mem["energy_kwh"] < cpu["energy_kwh"]), "Primary win flag differs")
        for prefix, run in (("cpu", cpu), ("proposed", mem)):
            for suffix, name in (("mean_wait_s", "mean_wait_s"), ("p95_wait_s", "p95_wait_s"),
                                 ("migrations", "migrations"), ("mean_active_hosts", "mean_active_hosts"),
                                 ("pressure_fraction", "overload_host_time_fraction")):
                equal(row[f"{prefix}_{suffix}"], run.get(name), f"primary {prefix} {name}")
    pairs = index_rows(a.policy_pairs, "policy pairs", ("workload_groups", "power_curve", "policy", "baseline"))
    require_keys(pairs, set(itertools.product(SIZES, CURVES, POLICIES, POLICIES)), "144 ordered policy comparisons")
    for expected in a.comparisons():
        row = pairs[(*run_key(expected), expected["baseline"])]
        for key in ("energy_kwh", "mean_wait_delta_s", "p95_wait_delta_s", "migrations", "pressure_delta_percentage_points"):
            equal(row[key], expected[key], f"policy pair {key}")
        equal(row["energy_saving_pct"], expected["energy_reduction_pct"], "policy pair reduction")
    raw = index_rows(a.raw_comparison, "raw comparison")
    require_keys(raw, set(a.index), "raw comparison active subset")
    for key, row in raw.items():
        run = a.index[key]
        for field in row:
            if field in run:
                if isinstance(run[field], (int, float)) and not isinstance(run[field], bool):
                    equal(row[field], run[field], f"raw comparison {field}")
                else:
                    require(row[field] == run[field], f"Raw comparison {field} differs")
        require(row["paired_cpu_baseline"] == PRIMARY[0], "Wrong raw comparison baseline")
        equal(row["energy_reduction_vs_paired_cpu_pct"], energy_reduction(run, a.index[(*key[:2], PRIMARY[0])]),
              "raw comparison reduction")


def _d5_check(a, workloads):
    primary_keys = set(itertools.product(SIZES, CURVES, PRIMARY))
    expected_skews = {(size, curve, policy, skew) for size, curve, policy in primary_keys
                      for skew, count in workloads[size]["instance_resource_skew_counts"].items() if count}
    outcomes = index_rows(a.d5_tables["outcomes_by_task_type"], "D5 skew outcomes",
                          ("workload_groups", "power_curve", "policy", "task_type"))
    require_keys(outcomes, expected_skews, "D5 observed skew outcomes")
    require(a.d5_validation["passed"] is True and a.d5_validation["decision_recordings"] == len(primary_keys),
            "D5 recorded validation or recording coverage differs")
    for key, rec in a.d5_recordings.items():
        run = a.index[key]
        finite_tree(rec, f"D5 {key}")
        require(rec["reproduces_committed_summary"] is True and rec["differing_fields"] == [],
                f"D5 recording does not reproduce compared fields: {key}")
        require(rec["decisions"]["own_rule_recompute_mismatches"] == 0, "D5 observer recomputation differs")
        for field in ("energy_kwh", "mean_wait_s", "mean_active_hosts", "migrations", "wakeups"):
            equal(rec[field], run[field], f"D5 recording {field}")
        equal(rec["decisions"]["placements"], run["completed_instances"], "D5 placements")
        require(rec["committed_result_manifest_sha256"] == run["manifest_sha256"], "D5 original manifest reference differs")
        equal(sum(r["instances"] for r in rec["outcomes_by_skew"].values()), run["completed_instances"], "D5 category total")
        equal(sum(r["migrations"] for r in rec["outcomes_by_skew"].values()), run["migrations"], "D5 category migrations")
        weighted_wait = 0
        for skew, observed in rec["outcomes_by_skew"].items():
            row = outcomes[(*key, skew)]
            for field in SKEW_METRICS:
                number(row[field], f"D5 {field}", integer=field == "instances",
                       maximum=100 if field.endswith("_pct") else None)
            equal(row["instances"], workloads[key[0]]["instance_resource_skew_counts"][skew], "D5 category population")
            for field in ("instances", "mean_wait_s", "p95_wait_s"):
                equal(row[field], observed[field], f"D5 category {field}")
            equal(row["delayed_pct"], 100 * observed["delayed_share"], "D5 delayed percent")
            equal(row["migrated_pct"], 100 * observed["migrated_instances"] / observed["instances"], "D5 migrated percent")
            destinations = rec["decisions"]["by_skew"][skew]["destinations"]
            equal(row["placed_on_asleep_or_waking_server_pct"],
                  100 * (destinations["sleeping"] + destinations["waking"]) / observed["instances"], "D5 wake placement percent")
            weighted_wait += observed["instances"] * observed["mean_wait_s"]
        equal(weighted_wait / run["completed_instances"], run["mean_wait_s"], "D5 instance-weighted mean wait")
        series = rec["time_series"]
        times = series["time_s"]
        require(times and times == sorted(set(times)), "D5 sample timestamps must be unique and increasing")
        require(all(len(values) == len(times) for values in series.values()), "D5 sampled series lengths differ")
        require(times[0] >= 0 and times[-1] <= run["stop_time_s"], "D5 sample time outside run")
        for name, values in series.items():
            for value in values:
                number(value, f"D5 sampled {name}", maximum=1 if name.startswith("mean_") else None)

    mix = index_rows(a.d5_tables["workload_mix"], "D5 workload mix", ("workload_groups",))
    require_keys(mix, {(s,) for s in SIZES}, "D5 workload mix")
    for (size,), row in mix.items():
        equal(row["instances"], workloads[size]["instances"], "D5 workload count")
        for skew in ("balanced", "memory_heavy", "cpu_heavy"):
            count = workloads[size]["instance_resource_skew_counts"].get(skew, 0)
            equal(row[f"{skew}_instances"], count, "D5 workload skew count")
            equal(row[f"{skew}_pct"], 100 * count / row["instances"], "D5 workload skew percent")
    breakdown = index_rows(a.d5_tables["run_energy_breakdown"], "D5 run breakdown")
    require_keys(breakdown, set(a.index), "D5 run breakdown")
    for key, row in breakdown.items():
        run = a.index[key]
        equal(row["energy_kwh"], run["energy_kwh"], "D5 breakdown energy")
        equal(sum(row[k] for k in ("idle_floor_kwh", "load_dependent_kwh", "waking_kwh", "asleep_kwh"))
              + (run["wake_transition_extra_energy_j"] + run["migration_extra_energy_j"]) / 3_600_000,
              run["energy_kwh"], "D5 breakdown components")
    gaps = index_rows(a.d5_tables["pair_energy_gap"], "D5 energy gaps", ("workload_groups", "power_curve"))
    require_keys(gaps, set(itertools.product(SIZES, CURVES)), "D5 energy gaps")
    for case, row in gaps.items():
        cpu, mem = (a.index[(*case, p)] for p in PRIMARY)
        equal(row["energy_change_kwh"], mem["energy_kwh"] - cpu["energy_kwh"], "D5 energy gap")
        equal(row["energy_change_pct"], -energy_reduction(mem, cpu), "D5 energy sign")
        equal(sum(row[k] for k in ("on_running_work_kwh", "on_without_work_kwh", "load_dependent_kwh",
                                  "wakeups_kwh", "longer_run_kwh", "extra_transition_kwh")),
              row["energy_change_kwh"], "D5 gap decomposition")
    for name in ("controller_diagnostics", "servers_running_work", "placement_decisions"):
        require_keys(index_rows(a.d5_tables[name], f"D5 {name}"), primary_keys, f"D5 {name}")
    require_keys(index_rows(a.d5_tables["placement_load_bands"], "D5 placement load bands",
                           ("workload_groups", "power_curve", "policy", "task_type")), expected_skews, "D5 placement load bands")
    require_keys(index_rows(a.d5_tables["tradeoffs"], "D5 tradeoffs", ("workload_groups", "power_curve")),
                 set(itertools.product(SIZES, CURVES)), "D5 tradeoffs")
    require_keys(index_rows(a.d5_tables["placement_score_arithmetic"], "D5 score arithmetic", ("power_curve",)),
                 {(c,) for c in CURVES}, "D5 score arithmetic")
    require(len(a.d5_tables["curve_band_watts"]) == 10 * len(CURVES), "D5 power-band coverage differs")
    finite_tree(a.d5_tables, "D5 tables")


def validate(artifacts):
    """Numerical verification only; missing inputs/lineage are reported elsewhere."""
    checks, errors = [], []
    def check(label, callback):
        try:
            callback()
            checks.append(label)
        except (ValueError, KeyError, TypeError, ZeroDivisionError) as exc:
            errors.append({"check": label, "error": str(exc)})
    workloads = {r["task_groups"]: r for r in artifacts.manifest["workloads"]}
    def workload_check():
        require(set(workloads) == set(SIZES) and len(artifacts.manifest["workloads"]) == len(SIZES), "Manifest workload coverage differs")
        for row in workloads.values():
            number(row["instances"], "manifest instances", integer=True)
            require(row["instances"] > 0, "Manifest has no instances")
            equal(sum(row["instance_resource_skew_counts"].values()), row["instances"], "manifest skew count")
        require(artifacts.raw_validation["passed"] is True and artifacts.baseline_validation["passed"] is True,
                "Recorded validation reports did not pass")
        require(artifacts.manifest["config"] == artifacts.raw_config, "Manifest raw configuration differs")
        require(artifacts.manifest["uses_yaksh_prepared_inputs"] is False
                and artifacts.manifest["uses_synthetic_workloads"] is False, "Manifest has the wrong study provenance")
        require(artifacts.data_validation["passed"] is True
                and artifacts.data_validation["independent_raw_row_verification"] is True
                and artifacts.data_validation["uses_yaksh_cleaned_inputs"] is False
                and artifacts.data_validation["synthetic_workloads"] is False, "Recorded independent data validation failed")
        original_grid = set(itertools.product(artifacts.raw_config["workload_group_counts"],
                                              artifacts.raw_config["power_curves"], artifacts.raw_config["policies"]))
        require(artifacts.raw_keys == original_grid, "Original source result collection is incomplete")
        equal(artifacts.raw_validation["runs"], len(original_grid), "recorded original run count")
        equal(artifacts.baseline_validation["unique_runs"], len(artifacts.rows), "recorded active run count")
        require(set(artifacts.baseline_validation["active_policies"]) == set(POLICIES), "Recorded active policies differ")
    check("manifest and recorded validation coverage", workload_check)
    for row in artifacts.rows:
        check(f"run {run_key(row)}: counts, units, energy, timing and assumptions", lambda row=row: _run_check(artifacts, row, workloads))
    check("nine primary pairs, 144 ordered comparisons and raw CSV consistency", lambda: _pairs_check(artifacts))
    check("D5 recordings, resource-skew outcomes, sampled series and energy accounting", lambda: _d5_check(artifacts, workloads))
    return {"passed": not errors, "checks_passed": len(checks), "checks": checks, "errors": errors,
            "active_outcomes": len(artifacts.rows), "primary_comparisons": len(artifacts.primary_pairs),
            "policy_comparisons": len(artifacts.policy_pairs),
            "completed_instance_replays": sum(r["completed_instances"] for r in artifacts.rows),
            "rejected_instances": sum(r["rejected_instances"] for r in artifacts.rows),
            "unfinished_instances": sum(r["unfinished_instances"] for r in artifacts.rows),
            "per_curve_outcomes": {c: sum(r["power_curve"] == c for r in artifacts.rows) for c in CURVES},
            "d5": {"recordings": len(artifacts.d5_recordings),
                   "resource_skew_rows": len(artifacts.resource_skew()),
                   "table_rows": {k: len(v) for k, v in artifacts.d5_tables.items()}},
            "missing_optional_metrics": {str(run_key(r)): [m for m in METRICS if r.get(m) is None]
                                         for r in artifacts.rows if any(r.get(m) is None for m in METRICS)}}


def make_report(artifacts, *, strict=False, check_history=True):
    numerical = validate(artifacts)
    provenance = assess(artifacts, check_history=check_history)
    return {"schema_version": 1, "mode": "strict" if strict else "offline",
            "passed": numerical["passed"] and (not strict or provenance["strict_prerequisites_passed"]),
            "numerical": numerical, "provenance": provenance,
            "active_scope": {"policies": list(POLICIES), "workload_sizes": list(SIZES), "power_curves": list(CURVES)},
            "metric_definitions": definitions(),
            "artifact_sha256": {p: sha256(artifacts.root / p) for p in sorted(artifacts.source_paths)},
            "new_simulations": 0, "raw_archive_processing_in_this_phase": False}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--strict", action="store_true", help="Fail if input/source/lineage prerequisites remain unresolved")
    args = parser.parse_args(argv)
    output = args.output or args.source_root / "ARNAV_Task/reports/artifact_validation.json"
    try:
        output = output_path(args.source_root, output)
    except ArtifactError as exc:
        parser.error(str(exc))
    try:
        report = make_report(ResearchArtifacts(args.source_root, args.config), strict=args.strict)
    except (ArtifactError, KeyError, TypeError, ValueError) as exc:
        report = {"schema_version": 1, "passed": False, "mode": "strict" if args.strict else "offline",
                  "numerical": {"passed": False, "errors": [{"check": "artifact loading", "error": str(exc)}]},
                  "provenance": {"status": "not_assessed", "end_to_end_reproducibility": {"verified": False}},
                  "new_simulations": 0}
    write_json(output, report)
    if "discrepancies" in report["provenance"]:
        (output.parent / "provenance_reconciliation.md").write_text(
            reconciliation_markdown(report["provenance"]), encoding="utf-8", newline="\n")
    print(json.dumps({"passed": report["passed"], "numerical_passed": report["numerical"]["passed"],
                      "provenance_status": report["provenance"]["status"], "report": str(output)}))
    if not report["passed"]:
        for error in report["numerical"].get("errors", []):
            print(f"ERROR: {error['check']}: {error['error']}")
        if args.strict and report["numerical"]["passed"]:
            print("ERROR: strict input/lineage prerequisites unresolved; see provenance in the report.")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
