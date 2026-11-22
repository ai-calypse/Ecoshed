"""Run from repository root: python -m ecosched --help."""
import argparse
import csv
from dataclasses import fields
import hashlib
import json
from pathlib import Path
import sys

from YAKSH_Task.scripts.load_workload import iter_instances
from .engine import Simulator, SimulationConfig
from .models import HostSpec
from .power import CURVE_FILE, load_curve

CURVES = tuple(json.loads(CURVE_FILE.read_text(encoding="utf-8"))["curves"])


def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_experiment(path):
    path = Path(path).resolve()
    raw = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "background_online_load": False, "replay_source_host_failures": False,
        "completion_policy": "drain_after_last_arrival",
        "demand_model": "constant_requested_cpu_and_memory",
        "scheduling_unit": "individual_instance",
        "instance_runtime_model": "task_mean_completed_first_attempt_duration",
    }
    for key, expected in required.items():
        if raw.get(key) != expected:
            raise ValueError(f"Unsupported experiment assumption {key}: expected {expected!r}")
    hosts_path = (path.parent / raw["hosts"]).resolve()
    workload_path = (path.parent / raw["workload"]).resolve()
    with hosts_path.open(newline="", encoding="utf-8") as f:
        hosts = [HostSpec(r["machine_id"], float(r["cpu_capacity_cores"]),
                          float(r["memory_capacity_normalized"])) for r in csv.DictReader(f)]
    options = dict(raw.get("simulator", {}))
    allowed = {f.name for f in fields(SimulationConfig)} - {"arrival_window_s"}
    if set(options) - allowed:
        raise ValueError(f"Unknown simulator options: {sorted(set(options) - allowed)}")
    config = SimulationConfig(arrival_window_s=raw["arrival_window_s"], **options)
    inputs = {"experiment_config_sha256": fingerprint(path),
              "hosts_sha256": fingerprint(hosts_path), "workload_sha256": fingerprint(workload_path),
              "power_curves_sha256": fingerprint(CURVE_FILE), "seed": raw["seed"],
              "hosts_file": hosts_path.name, "workload_file": workload_path.name}
    inputs["simulator_sources_sha256"] = {
        source.name: fingerprint(source) for source in sorted(Path(__file__).parent.glob("*.py"))
    }
    manifest = path.parent.parent / "manifest.json"
    if manifest.exists():
        inputs["data_manifest_sha256"] = fingerprint(manifest)
    return hosts, workload_path, config, inputs


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    names = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("YAKSH_Task/config/experiment_250.json"))
    parser.add_argument("--curve", choices=CURVES, default=CURVES[0])
    parser.add_argument("--all-curves", action="store_true", help="Replay identical inputs using each curve")
    parser.add_argument("--output", type=Path, default=Path("BRAVE_Task/results"))
    args = parser.parse_args(argv)
    try:
        hosts, workload, config, inputs = load_experiment(args.config)
        for name in CURVES if args.all_curves else (args.curve,):
            simulator = Simulator(hosts, config, load_curve(name))
            result = simulator.run(iter_instances(workload))
            result["inputs"] = inputs
            result["python_version"] = sys.version.split()[0]
            directory = args.output / workload.stem / name
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True,
                                                              allow_nan=False) + "\n", encoding="utf-8")
            write_csv(directory / "instances.csv", simulator.records)
            write_csv(directory / "host_samples.csv", simulator.samples)
            write_csv(directory / "migrations.csv", simulator.migration_log)
            print(f"{workload.stem} / {name}: {result['completed_instances']} completed, "
                  f"{result['rejected_instances']} rejected, {result['energy_kwh']:.6f} modeled kWh; {directory}")
    except (ValueError, KeyError, OSError, RuntimeError) as exc:
        parser.exit(2, f"ecosched: {exc}\n")


if __name__ == "__main__":
    main()
