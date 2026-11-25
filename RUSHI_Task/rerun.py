"""Re-run the primary LR-MMT pair with a read-only decision recorder.

Needs the prepared raw-archive inputs in RAW_Alibaba/prepared/ (see README.md).
Uses exactly the RAW_Alibaba replay setup: same verified inputs, simulator
config, fresh simulator per curve, InstrumentedSimulator and validate_run.
Each run must reproduce the committed RAW_Alibaba summary field-for-field,
which proves the recorder did not change any decision. Only compact JSON is
written (per-instance outputs stay in memory), so results can be committed.

    python -m RUSHI_Task.rerun                       # 3 sizes x 3 curves x 2 policies
    python -m RUSHI_Task.rerun --sizes 250 --curves hpe_dl360_gen9
"""
import argparse
import csv
import json
from pathlib import Path
import statistics
import sys
import time

from ecosched import SimulationConfig, load_curve
from ENERGY_Study.instrumentation import InstrumentedSimulator
from RAW_Alibaba.data import HERE as RAW, PACKAGE, iter_instances, load_hosts, verified_manifest
from RAW_Alibaba.extract import digest
from RAW_Alibaba.run import make_policy, source_hashes, validate_run
from .observer import DecisionObserver, outcomes_by_skew, time_series

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "reports" / "runs"
COMMITTED = ROOT / "RAW_Alibaba" / "reports" / "summaries.json"
PAIR = ("lr_mmt", "lr_mmt_memory")
SIZES = (250, 1000, 4000)
CURVES = ("hpe_dl360_gen9", "huawei_rh2288h_v3", "quanta_d51b_2u")
# python_version is provenance, not a result. manifest_sha256 is reported separately:
# the committed manifest.json was regenerated after the committed runs (see README).
IGNORED_FIELDS = {"python_version", "manifest_sha256"}


def load_skews(size):
    with (PACKAGE / f"workload_{size}.csv").open(newline="", encoding="utf-8") as f:
        return {r["task_group_id"]: r["resource_skew"] for r in csv.DictReader(f)}


def differing_fields(result, committed):
    keys = (set(result) | set(committed)) - IGNORED_FIELDS
    return sorted(k for k in keys if result.get(k) != committed.get(k))


def run_one(size, curve_name, name, tasks, pool, settings, skew_of, committed, manifest_sha):
    curve = load_curve(curve_name)
    policy = make_policy(name, settings, curve)
    other = make_policy(PAIR[1] if name == PAIR[0] else PAIR[0], settings, curve)
    observer = DecisionObserver(policy, other, skew_of)
    engine = InstrumentedSimulator(pool, settings, curve, observer)
    result = engine.run(iter(tasks))
    validation = validate_run(engine, result, tasks, size)
    # Same provenance fields RAW_Alibaba.run adds, so the whole summary can be compared.
    manifest = verified_manifest()
    result.update({"workload_groups": size, "data_source": "fresh_user_archive_alibaba_v2017",
                   "fresh_raw_archive_processing": True, "uses_yaksh_prepared_inputs": False,
                   "synthetic_workload": False, "runtime_model": manifest["config"]["runtime_model"],
                   "archive_sha256": manifest["archive"]["archive_sha256"],
                   "published_legacy_archive_hash_matches": manifest["archive"]["matches_published_legacy_archive"],
                   "manifest_sha256": manifest_sha, "source_sha256": source_hashes(),
                   "validation": validation, "python_version": sys.version.split()[0]})
    reference = committed[(size, curve_name, name)]
    differences = differing_fields(result, reference)
    decisions = observer.report()
    if decisions["own_rule_recompute_mismatches"]:
        raise RuntimeError("Recorder recomputation disagreed with the policy; recorder is wrong")
    return {
        "workload_groups": size, "power_curve": curve_name, "policy": name,
        "reproduces_committed_summary": not differences, "differing_fields": differences,
        "committed_summary_source": "RAW_Alibaba/reports/summaries.json",
        "energy_kwh": result["energy_kwh"], "mean_wait_s": result["mean_wait_s"],
        "migrations": result["migrations"], "wakeups": result["wakeups"],
        "mean_active_hosts": result["mean_active_hosts"],
        "input_manifest_sha256": manifest_sha,
        "committed_result_manifest_sha256": reference["manifest_sha256"],
        "python_version": sys.version.split()[0],
        "simulator_source_sha256": result["source_sha256"],
        "recorder_source_sha256": {p.relative_to(ROOT).as_posix(): digest(p)
                                   for p in (HERE / "observer.py", HERE / "rerun.py")},
        "decisions": decisions,
        "controller_diagnostics": dict(sorted(policy.diagnostics.items())),
        "outcomes_by_skew": outcomes_by_skew(engine.records, engine.migration_log, skew_of),
        "time_series": time_series(engine.samples),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sizes", nargs="+", type=int, choices=SIZES, default=list(SIZES))
    parser.add_argument("--curves", nargs="+", choices=CURVES, default=list(CURVES))
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    manifest = verified_manifest()  # raises unless prepared CSVs match the committed manifest
    data_validation = json.loads((RAW / "data_validation.json").read_text(encoding="utf-8"))
    manifest_sha = digest(PACKAGE / "manifest.json")
    largest = max(manifest["workloads"], key=lambda w: w["task_groups"])
    if (not data_validation["passed"] or data_validation["checked_instances"] != largest["instances"]
            or data_validation["checked_groups"] != largest["task_groups"]):
        raise ValueError("Raw-row data validation must have passed for the full prepared workload")
    committed = {(r["workload_groups"], r["power_curve"], r["policy"]): r
                 for r in json.loads(COMMITTED.read_text(encoding="utf-8"))}
    recorded = {r["manifest_sha256"] for r in committed.values()} | {data_validation["manifest_sha256"]}
    if recorded != {manifest_sha}:
        print(f"NOTE: committed results/data validation record manifest {sorted(recorded)}, but "
              f"RAW_Alibaba/prepared/manifest.json is {manifest_sha}. Prepared CSVs still match the "
              "committed manifest; field-for-field reproduction below is the deciding check.", flush=True)
    settings = SimulationConfig(**manifest["config"]["simulation"])
    pool = load_hosts()
    median_cpu = statistics.median(h.cpu for h in pool)
    median_memory = statistics.median(h.memory for h in pool)
    frozen = source_hashes()

    for size in args.sizes:
        tasks = list(iter_instances(size))
        expected = next(w["instances"] for w in manifest["workloads"] if w["task_groups"] == size)
        if len(tasks) != expected:
            raise ValueError("Loader did not preserve declared multiplicity")
        skew_of = load_skews(size)
        task_size = {
            "median_cpu_fraction_of_median_host": statistics.median(t.cpu_request_cores for t in tasks) / median_cpu,
            "median_memory_fraction_of_median_host": statistics.median(t.memory_request_normalized for t in tasks) / median_memory,
        }
        for curve_name in args.curves:
            for name in PAIR:
                start = time.monotonic()
                row = run_one(size, curve_name, name, tasks, pool, settings, skew_of, committed, manifest_sha)
                row["task_size"] = task_size
                target = args.output / curve_name / f"workload_{size}" / f"{name}.json"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(row, indent=1, sort_keys=True) + "\n", encoding="utf-8")
                status = "reproduces committed summary" if row["reproduces_committed_summary"] else \
                    f"DIFFERS in {row['differing_fields']}"
                print(f"{size} / {curve_name} / {name}: {row['energy_kwh']:.6f} kWh, {status} "
                      f"({time.monotonic() - start:.0f}s)", flush=True)
    if source_hashes() != frozen or digest(PACKAGE / "manifest.json") != manifest_sha:
        raise ValueError("Simulator source or inputs changed during the rerun")


if __name__ == "__main__":
    main()
