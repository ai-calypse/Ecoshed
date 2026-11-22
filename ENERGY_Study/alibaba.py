"""Active experiment runner: verified Alibaba-derived trace inputs only."""
import argparse
import csv
from dataclasses import replace
import json
import math
from pathlib import Path
import sys
import time

from ecosched import load_curve
from ecosched.__main__ import fingerprint, load_experiment, write_csv
from ROHAN_Task.policies import LRMMT
from ROHAN_Task.run import validate_run
from YAKSH_Task.scripts.load_workload import iter_instances
from .instrumentation import InstrumentedSimulator
from .policies import EnergyFirst

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CONFIG = HERE / "alibaba_config.json"
DEFAULT_OUTPUT = HERE / "alibaba_reports"


def manifest_check(package, relatives):
    package = Path(package).resolve()
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("official_sources", {}).get("repository") != "https://github.com/alibaba/clusterdata":
        raise ValueError("Dataset manifest does not identify the official Alibaba source")
    for relative in relatives:
        path = (package / relative).resolve()
        if package not in path.parents:
            raise ValueError("Input path escapes the Alibaba package")
        entry = manifest["outputs"].get(relative)
        if not entry or fingerprint(path) != entry["sha256"]:
            raise ValueError(f"Unverified or altered Alibaba-derived input: {relative}")
    return manifest


def inputs_for(size):
    package = ROOT / "YAKSH_Task"
    config_relative = f"config/experiment_{size}.json"
    relatives = [config_relative, "data/hosts_64.csv", f"data/workload_{size}.csv"]
    manifest_check(package, relatives)
    hosts, workload, simulation, provenance = load_experiment(package / config_relative)
    raw = json.loads((package / config_relative).read_text(encoding="utf-8"))
    if ((package / "config" / raw["hosts"]).resolve() != (package / "data/hosts_64.csv").resolve()
            or workload != (package / f"data/workload_{size}.csv").resolve()):
        raise ValueError("Experiment points outside the verified Alibaba-derived files")
    with workload.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != size:
        raise ValueError("Unexpected Alibaba task-group count")
    if not all(r.get("source_row") and r.get("job_id") and r.get("task_id") for r in rows):
        raise ValueError("Missing original trace-row identifiers")
    return hosts, workload, simulation, provenance, sum(int(r["instance_num"]) for r in rows)


def source_hashes():
    paths = list((ROOT / "ecosched").glob("*.py"))
    paths += [HERE / p for p in ("run.py", "verify.py", "alibaba.py", "policies.py", "instrumentation.py")]
    paths += [ROOT / "ROHAN_Task/policies.py", ROOT / "ROHAN_Task/run.py",
              ROOT / "YAKSH_Task/scripts/load_workload.py", ROOT / "ecosched/power_curves.json"]
    return {p.relative_to(ROOT).as_posix(): fingerprint(p) for p in sorted(paths)}


def make_policy(name, simulation, curve):
    if name in ("lr_mmt", "lr_mmt_memory"):
        return LRMMT(simulation, curve, memory_aware=name.endswith("memory"))
    if name in ("energy_first_cpu", "energy_first_memory"):
        return EnergyFirst(simulation, curve, memory_aware=name.endswith("memory"))
    raise ValueError(f"Unsupported policy {name}")


def comparisons(results):
    indexed = {(r["workload_groups"], r["power_curve"], r["policy"]): r for r in results}
    metrics = ("energy_kwh", "completed_instances", "rejected_instances", "unfinished_instances",
               "mean_wait_s", "p95_wait_s", "p95_turnaround_s", "migrations", "mean_active_hosts",
               "overload_host_time_fraction", "mean_fragmentation_index", "cpu_stranded_by_memory_core_seconds",
               "memory_stranded_by_cpu_unit_seconds", "sleep_energy_j", "waking_energy_j", "active_energy_j")
    rows = []
    for result in results:
        baseline_name = "energy_first_cpu" if result["policy"].startswith("energy_first") else "lr_mmt"
        baseline = indexed.get((result["workload_groups"], result["power_curve"], baseline_name))
        reduction = (100 * (baseline["energy_kwh"] - result["energy_kwh"]) / baseline["energy_kwh"]
                     if baseline else None)
        rows.append({"workload_groups": result["workload_groups"], "power_curve": result["power_curve"],
                     "policy": result["policy"], "data_source": result["data_source"],
                     **{key: result[key] for key in metrics}, "comparison_baseline": baseline_name,
                     "energy_reduction_vs_paired_cpu_pct": reduction})
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, choices=(250, 1000, 4000))
    parser.add_argument("--curves", nargs="+", choices=("hpe_dl360_gen9", "huawei_rh2288h_v3", "quanta_d51b_2u"))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--details", action="store_true")
    args = parser.parse_args(argv)
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    sizes, curves = args.sizes or raw["sizes"], args.curves or raw["curves"]
    hashes = source_hashes()
    results = []
    for size in sizes:
        pool, workload, original, provenance, expected = inputs_for(size)
        simulation = replace(original, **raw["simulation_overrides"])
        for curve_name in curves:
            for name in raw["policies"]:
                start = time.monotonic()
                curve = load_curve(curve_name)
                policy = make_policy(name, simulation, curve)
                engine = InstrumentedSimulator(pool, simulation, curve, policy)
                result = engine.run(iter_instances(workload))
                validation = validate_run(engine, result, expected)
                components = sum(result[k] for k in ("sleep_energy_j", "waking_energy_j", "active_energy_j",
                                                     "wake_transition_extra_energy_j", "migration_extra_energy_j"))
                if not math.isclose(components, result["energy_j"], rel_tol=1e-10, abs_tol=1e-5):
                    raise ValueError("Energy breakdown does not reconcile")
                result.update({"workload_groups": size, "data_source": raw["data_source"],
                               "source_repository": raw["source_repository"], "fresh_raw_archive_replay": False,
                               "synthetic_workload": False, "preparation_package": "YAKSH_Task",
                               "inputs": provenance, "validation": validation,
                               "study_sources_sha256": hashes, "study_config_sha256": fingerprint(CONFIG),
                               "python_version": sys.version.split()[0]})
                directory = args.output / f"workload_{size}" / curve_name / name
                directory.mkdir(parents=True, exist_ok=True)
                (directory / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                if args.details:
                    write_csv(directory / "instances.csv", engine.records)
                    write_csv(directory / "host_samples.csv", engine.samples)
                    write_csv(directory / "migrations.csv", engine.migration_log)
                results.append(result)
                print(f"ALIBABA {size} / {curve_name} / {name}: {result['completed_instances']} completed, "
                      f"{result['energy_kwh']:.6f} kWh ({time.monotonic()-start:.1f}s)", flush=True)
    if source_hashes() != hashes:
        raise RuntimeError("Experiment sources changed during replay")
    write_csv(args.output / "comparison.csv", comparisons(results))
    print(f"Validated {len(results)} Alibaba-derived runs; no synthetic fallback.", flush=True)


def verify(source, output, require_full=True):
    import itertools
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in Path(source).rglob("summary.json")]
    if not rows:
        raise ValueError("No Alibaba run results found")
    keys = [(r["workload_groups"], r["power_curve"], r["policy"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate experiment results")
    expected = set(itertools.product(raw["sizes"], raw["curves"], raw["policies"]))
    if require_full and set(keys) != expected:
        raise ValueError("Expected identical complete Alibaba matrix separately for each curve")
    hashes = source_hashes()
    for row in rows:
        if row.get("synthetic_workload") is not False or row["data_source"] != raw["data_source"]:
            raise ValueError("Non-Alibaba or unverified dataset result rejected")
        if row["study_sources_sha256"] != hashes or row["study_config_sha256"] != fingerprint(CONFIG):
            raise ValueError("Experiment source/config changed")
        _, _, original, provenance, count = inputs_for(row["workload_groups"])
        from dataclasses import asdict
        if row["inputs"] != provenance or row["config"] != asdict(replace(original, **raw["simulation_overrides"])):
            raise ValueError("Dataset provenance or common assumptions changed")
        if not row["validation"]["passed"] or row["completed_instances"] != count or row["rejected_instances"] or row["unfinished_instances"]:
            raise ValueError("Alibaba replay failed work conservation")
    rows.sort(key=lambda r: (r["workload_groups"], r["power_curve"], r["policy"]))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "comparison.csv", comparisons(rows))
    (output / "summaries.json").write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result = {"passed": True, "runs": len(rows), "data_source": raw["data_source"],
              "synthetic_runs": 0, "fresh_raw_archive_replay": False,
              "total_completed_instance_replays": sum(r["completed_instances"] for r in rows),
              "per_curve_runs": {c: sum(r["power_curve"] == c for r in rows) for c in raw["curves"]},
              "checks": ["manifest-verified Alibaba-derived inputs", "no generated workload substitution",
                         "same complete grid independently per power curve", "source/config provenance",
                         "identical paired hosts, trace rows and assumptions", "work conservation"]}
    (output / "validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


def verify_main(argv=None):
    parser = argparse.ArgumentParser(description="Verify Alibaba-only experiment outputs")
    parser.add_argument("--reports", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args(argv)
    verify(args.source or args.reports, args.reports, require_full=not args.allow_partial)


if __name__ == "__main__":
    main()
