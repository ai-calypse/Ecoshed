"""Replay freshly prepared Alibaba raw records, with no Yaksh data-loader import."""
import argparse
from collections import Counter, defaultdict
import csv
import itertools
import json
import math
from pathlib import Path
import sys
import time

from ecosched import SimulationConfig, load_curve
from ecosched.policies import FirstFit
from ROHAN_Task.policies import BestFit, LRMMT
from ENERGY_Study.instrumentation import InstrumentedSimulator
from ENERGY_Study.policies import EnergyFirst
from .data import HERE, PACKAGE, verified_manifest, load_hosts, iter_instances
from .extract import digest

ROOT = HERE.parent
CONFIG = HERE / "config.json"
DEFAULT_REPORTS = HERE / "reports"


def write_csv(path, rows):
    if not rows:
        return
    names = list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def source_hashes():
    files = list(HERE.glob("*.py")) + list((ROOT / "ecosched").glob("*.py"))
    files += [ROOT / "ENERGY_Study/instrumentation.py", ROOT / "ENERGY_Study/policies.py",
              ROOT / "ROHAN_Task/policies.py", ROOT / "ecosched/power_curves.json"]
    return {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(files)}


def make_policy(name, config, curve):
    if name == "first_fit":
        return FirstFit()
    if name == "best_fit":
        return BestFit()
    if name in ("lr_mmt", "lr_mmt_memory"):
        return LRMMT(config, curve, memory_aware=name.endswith("memory"))
    if name in ("energy_first_cpu", "energy_first_memory"):
        return EnergyFirst(config, curve, memory_aware=name.endswith("memory"))
    raise ValueError(f"Unknown policy: {name}")


def validate_run(engine, result, tasks, size):
    count = len(tasks)
    if (result["arrived_instances"] != count or result["completed_instances"] != count
            or result["completed_task_groups"] != size or result["rejected_instances"] or result["unfinished_instances"]):
        raise ValueError("Fresh raw replay did not conserve offered work")
    if engine.running or engine.waiting or any(h.reservations for h in engine.hosts.values()):
        raise ValueError("Reservations/queue remain after drain")
    if len(engine.records) != count or len({r["instance_id"] for r in engine.records}) != count:
        raise ValueError("Duplicate or missing replay outcomes")
    expected = {t.instance_id: t for t in tasks}
    pause = Counter()
    for transfer in engine.migration_log:
        pause[transfer["instance_id"]] += transfer["pause_s"]
    for outcome in engine.records:
        original = expected[outcome["instance_id"]]
        elapsed = outcome["finish_s"] - outcome["start_s"]
        if not math.isclose(elapsed, original.duration_s + pause[original.instance_id], abs_tol=1e-6):
            raise ValueError("Observed runtime or migration pause changed during replay")
        if outcome["start_s"] < original.arrival_time_s:
            raise ValueError("Instance started before its source-derived release")
    components = sum(result[k] for k in ("sleep_energy_j", "waking_energy_j", "active_energy_j",
                                         "wake_transition_extra_energy_j", "migration_extra_energy_j"))
    if not math.isclose(components, result["energy_j"], abs_tol=1e-5, rel_tol=1e-10):
        raise ValueError("Energy components do not reconcile")
    for sample in engine.samples:
        if sample["cpu_used"] > sample["cpu_capacity"] + 1e-8 or sample["memory_used"] > sample["memory_capacity"] + 1e-10:
            raise ValueError("Sampled physical capacity violation")
    return {"passed": True, "checked_outcomes": count, "individual_runtime_plus_migration_pause": True,
            "checked_host_samples": len(engine.samples), "full_drain": True}


def comparison_rows(results):
    index = {(r["workload_groups"], r["power_curve"], r["policy"]): r for r in results}
    metrics = ("energy_kwh", "completed_instances", "rejected_instances", "unfinished_instances",
               "wh_per_completed_instance", "mean_wait_s", "p95_wait_s", "p95_turnaround_s", "migrations",
               "migration_pause_instance_seconds", "mean_active_hosts", "peak_active_hosts", "overload_host_time_fraction",
               "mean_fragmentation_index", "stop_time_s", "drain_time_s")
    rows = []
    for result in results:
        baseline = "energy_first_cpu" if result["policy"].startswith("energy_first") else "lr_mmt"
        reference = index.get((result["workload_groups"], result["power_curve"], baseline))
        rows.append({"workload_groups": result["workload_groups"], "power_curve": result["power_curve"],
                     "policy": result["policy"], "data_source": result["data_source"],
                     **{k: result[k] for k in metrics}, "paired_cpu_baseline": baseline,
                     "energy_reduction_vs_paired_cpu_pct": (100 * (reference["energy_kwh"] - result["energy_kwh"]) / reference["energy_kwh"] if reference else None)})
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, choices=(250, 1000, 4000))
    parser.add_argument("--curves", nargs="+", choices=("hpe_dl360_gen9", "huawei_rh2288h_v3", "quanta_d51b_2u"))
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORTS)
    parser.add_argument("--details", action="store_true")
    args = parser.parse_args(argv)
    manifest = verified_manifest()
    data_validation = json.loads((HERE / "data_validation.json").read_text(encoding="utf-8"))
    if not data_validation["passed"] or data_validation.get("manifest_sha256") != digest(PACKAGE / "manifest.json"):
        raise ValueError("Independent raw-row validation must pass before replay")
    config = manifest["config"]
    pool = load_hosts()
    settings = SimulationConfig(**config["simulation"])
    frozen_sources = source_hashes()
    manifest_sha = digest(PACKAGE / "manifest.json")
    results = []
    for size in args.sizes or config["workload_group_counts"]:
        tasks = list(iter_instances(size))
        expected_count = next(r["instances"] for r in manifest["workloads"] if r["task_groups"] == size)
        if len(tasks) != expected_count:
            raise ValueError("Raw loader did not preserve declared multiplicity")
        for curve_name in args.curves or config["power_curves"]:
            for name in config["policies"]:
                start = time.monotonic()
                curve = load_curve(curve_name)
                engine = InstrumentedSimulator(pool, settings, curve, make_policy(name, settings, curve))
                result = engine.run(iter(tasks))
                validation = validate_run(engine, result, tasks, size)
                result.update({"workload_groups": size, "data_source": "fresh_user_archive_alibaba_v2017",
                               "fresh_raw_archive_processing": True, "uses_yaksh_prepared_inputs": False,
                               "synthetic_workload": False, "runtime_model": config["runtime_model"],
                               "archive_sha256": manifest["archive"]["archive_sha256"],
                               "published_legacy_archive_hash_matches": manifest["archive"]["matches_published_legacy_archive"],
                               "manifest_sha256": manifest_sha, "source_sha256": frozen_sources,
                               "validation": validation, "python_version": sys.version.split()[0]})
                directory = args.output / f"workload_{size}" / curve_name / name
                directory.mkdir(parents=True, exist_ok=True)
                (directory / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                if args.details:
                    write_csv(directory / "instances.csv", engine.records)
                    write_csv(directory / "migrations.csv", engine.migration_log)
                results.append(result)
                print(f"RAW ALIBABA {size} / {curve_name} / {name}: {len(tasks):,} completed, "
                      f"{result['energy_kwh']:.6f} kWh ({time.monotonic()-start:.1f}s)", flush=True)
    if source_hashes() != frozen_sources or digest(PACKAGE / "manifest.json") != manifest_sha:
        raise ValueError("Replay source or input manifest changed during execution")
    write_csv(args.output / "comparison.csv", comparison_rows(results))
    print(f"Completed {len(results)} fresh raw-archive simulation runs.", flush=True)


def verify(source, output, allow_partial=False):
    manifest = verified_manifest()
    config = manifest["config"]
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in Path(source).rglob("summary.json")]
    if not rows:
        raise ValueError("No raw-archive results found")
    keys = [(r["workload_groups"], r["power_curve"], r["policy"]) for r in rows]
    expected = set(itertools.product(config["workload_group_counts"], config["power_curves"], config["policies"]))
    if len(keys) != len(set(keys)) or (not allow_partial and set(keys) != expected):
        raise ValueError("Incomplete, duplicate or unequal per-curve raw experiment grid")
    hashes = source_hashes()
    for row in rows:
        if (row["data_source"] != "fresh_user_archive_alibaba_v2017" or not row["fresh_raw_archive_processing"]
                or row["uses_yaksh_prepared_inputs"] or row["synthetic_workload"]):
            raise ValueError("Only independently prepared raw-archive inputs are allowed")
        if row["source_sha256"] != hashes or row["manifest_sha256"] != digest(PACKAGE / "manifest.json"):
            raise ValueError("Raw replay inputs or implementation changed")
        count = next(x["instances"] for x in manifest["workloads"] if x["task_groups"] == row["workload_groups"])
        if row["completed_instances"] != count or row["completed_task_groups"] != row["workload_groups"] or not row["validation"]["passed"]:
            raise ValueError("Raw replay completion validation failed")
        if row["rejected_instances"] or row["unfinished_instances"]:
            raise ValueError("Raw replay left rejected/unfinished work")
    rows.sort(key=lambda r: (r["workload_groups"], r["power_curve"], r["policy"]))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "comparison.csv", comparison_rows(rows))
    (output / "summaries.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = {"passed": True, "runs": len(rows), "fresh_raw_archive_processing": True,
              "uses_yaksh_prepared_inputs": False, "synthetic_runs": 0,
              "total_completed_instance_replays": sum(r["completed_instances"] for r in rows),
              "per_curve_runs": dict(Counter(r["power_curve"] for r in rows)),
              "archive_sha256": manifest["archive"]["archive_sha256"],
              "published_legacy_archive_hash_matches": manifest["archive"]["matches_published_legacy_archive"],
              "all_gzip_and_member_integrity_checks_passed": manifest["archive"]["gzip_crc_and_tar_members_valid"],
              "checks": ["independent raw-table preparation", "actual per-attempt durations",
                         "original complete-group multiplicity", "single curve per fresh simulator",
                         "identical full grid per curve", "source/input hashes", "full work conservation"]}
    (output / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


def verify_main(argv=None):
    parser = argparse.ArgumentParser(description="Verify fresh raw-archive Alibaba experiments")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--reports", type=Path, default=DEFAULT_REPORTS)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args(argv)
    verify(args.source or args.reports, args.reports, args.allow_partial)


if __name__ == "__main__":
    main()
