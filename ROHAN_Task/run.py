"""Reproducible D3 policy runs using Yaksh's inputs and Brave's unmodified engine."""
import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
import time

from ecosched import Simulator, load_curve
from ecosched.__main__ import CURVES, fingerprint, load_experiment, write_csv
from ecosched.policies import FirstFit
from YAKSH_Task.scripts.load_workload import iter_instances
from .policies import BestFit, LRMMT, PolicyConfig

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = Path(__file__).with_name("config") / "default.json"
POLICIES = ("first_fit", "best_fit", "lr_mmt", "lr_mmt_memory")


def make_policy(name, simulation, curve, options):
    if name == "first_fit":
        return FirstFit()
    if name == "best_fit":
        return BestFit()
    if name in ("lr_mmt", "lr_mmt_memory"):
        return LRMMT(simulation, curve, options, memory_aware=name == "lr_mmt_memory")
    raise ValueError(f"Unknown policy {name}")


def validate_run(engine, result, expected):
    """Reconcile every instance/group; verify sampled reservations and migrations."""
    if result["arrived_instances"] != expected:
        raise ValueError("Replay lost or added instances")
    if result["completed_instances"] != expected or result["rejected_instances"] or result["unfinished_instances"]:
        raise ValueError("Prepared workload did not complete fully")
    records = engine.records
    if len(records) != expected or len({r["instance_id"] for r in records}) != expected:
        raise ValueError("Instance outcome IDs do not reconcile")
    if any(not r["arrival_s"] <= r["start_s"] < r["finish_s"] for r in records):
        raise ValueError("Invalid completion timing")
    if abs(sum(result["host_energy_j"].values()) - result["energy_j"]) > 1e-5:
        raise ValueError("Host and total energy do not reconcile")
    for sample in engine.samples:
        if not (-1e-9 <= sample["cpu_used"] <= sample["cpu_capacity"] + 1e-8
                and -1e-12 <= sample["memory_used"] <= sample["memory_capacity"] + 1e-10):
            raise ValueError("Sampled capacity violation")
    if len(engine.migration_log) != result["migrations"]:
        raise ValueError("Migration log does not reconcile")
    if engine.running or engine.waiting or any(h.reservations for h in engine.hosts.values()):
        raise ValueError("Drain left reservations or queued work")
    return {"passed": True, "checked_instances": expected,
            "checked_host_samples": len(engine.samples), "checked_migrations": len(engine.migration_log)}


def comparison_rows(summaries):
    by_key = {(r["workload_groups"], r["power_curve"], r["policy"]): r for r in summaries}
    rows = []
    metrics = ("completed_instances", "rejected_instances", "unfinished_instances", "energy_kwh",
               "wh_per_completed_instance", "mean_wait_s", "max_wait_s", "stop_time_s", "drain_time_s",
               "mean_active_hosts", "peak_active_hosts", "migrations", "migration_pause_instance_seconds",
               "overload_host_time_fraction")
    for result in summaries:
        key = (result["workload_groups"], result["power_curve"])
        baseline = by_key.get((*key, "first_fit"))
        cpu = by_key.get((*key, "lr_mmt"))
        row = {"workload_groups": key[0], "power_curve": key[1], "policy": result["policy"],
               **{m: result[m] for m in metrics}}
        for name, reference in (("first_fit", baseline), ("lr_mmt", cpu)):
            row[f"energy_reduction_vs_{name}_pct"] = (
                100 * (reference["energy_kwh"] - result["energy_kwh"]) / reference["energy_kwh"]
                if reference and reference["energy_kwh"] > 0 else None)
        rows.append(row)
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--sizes", nargs="+", type=int, choices=(250, 1000, 4000))
    parser.add_argument("--curves", nargs="+", choices=CURVES)
    parser.add_argument("--policies", nargs="+", choices=POLICIES)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("results"))
    parser.add_argument("--details", action="store_true", help="Also persist per-instance and host sample CSVs")
    args = parser.parse_args(argv)
    raw = json.loads(args.config.read_text(encoding="utf-8"))
    options = PolicyConfig(**raw["policy"])
    sizes, curves, names = args.sizes or raw["sizes"], args.curves or raw["curves"], args.policies or raw["policies"]
    summaries = []
    source_hashes = {p.name: fingerprint(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
    for size in sizes:
        hosts, workload, original, inputs = load_experiment(ROOT / f"YAKSH_Task/config/experiment_{size}.json")
        simulation = replace(original, **raw["simulation_overrides"])
        # Count without expanding to retain the original multiplicity contract.
        import csv
        with workload.open(newline="") as f:
            expected = sum(int(r["instance_num"]) for r in csv.DictReader(f))
        for curve_name in curves:
            for name in names:
                started = time.monotonic()
                curve = load_curve(curve_name)
                policy = make_policy(name, simulation, curve, options)
                engine = Simulator(hosts, simulation, curve, policy)
                result = engine.run(iter_instances(workload))
                validation = validate_run(engine, result, expected)
                if result["completed_task_groups"] != size:
                    raise ValueError("Group completion count does not reconcile")
                result.update({"workload_groups": size, "inputs": inputs,
                               "policy_config": asdict(options) if name.startswith("lr_mmt") else None,
                               "rohan_sources_sha256": source_hashes,
                               "runner_config_sha256": fingerprint(args.config),
                               "assumptions": raw["assumptions"], "validation": validation,
                               "policy_diagnostics": dict(getattr(policy, "diagnostics", {})),
                               "python_version": sys.version.split()[0]})
                directory = args.output / f"workload_{size}" / curve_name / name
                directory.mkdir(parents=True, exist_ok=True)
                (directory / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True,
                                                                  allow_nan=False) + "\n", encoding="utf-8")
                write_csv(directory / "migrations.csv", engine.migration_log)
                write_csv(directory / "decisions.csv", getattr(policy, "decisions", []))
                if args.details:
                    write_csv(directory / "instances.csv", engine.records)
                    write_csv(directory / "host_samples.csv", engine.samples)
                summaries.append(result)
                print(f"{size} / {curve_name} / {name}: {result['completed_instances']} completed, "
                      f"{result['energy_kwh']:.6f} kWh, {result['migrations']} migrations "
                      f"({time.monotonic() - started:.1f}s)", flush=True)
    # Rebuild the aggregate from the invocation's exact selected matrix.
    write_csv(args.output / "comparison.csv", comparison_rows(summaries))
    (args.output / "summaries.json").write_text(json.dumps(summaries, indent=2, sort_keys=True,
                                                        allow_nan=False) + "\n", encoding="utf-8")
    print(f"Validated {len(summaries)} runs. Comparison: {args.output / 'comparison.csv'}", flush=True)


if __name__ == "__main__":
    main()
