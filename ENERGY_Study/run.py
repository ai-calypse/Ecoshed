"""Execute a frozen, data-independent mechanism/holdout/sensitivity protocol."""
import argparse
from collections import defaultdict
from dataclasses import asdict, replace
import hashlib
import json
import math
from pathlib import Path
import sys

from ecosched import SimulationConfig, Simulator, load_curve
from ROHAN_Task.policies import LRMMT
from .instrumentation import InstrumentedSimulator
from .policies import EnergyFirst
from .statistics import assess_pair, paired_bootstrap
from .workloads import MIXES, generate, hosts, witness, workload_hash

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "config.json"
POLICIES = ("energy_first_cpu", "energy_first_memory")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def csv_write(path, rows):
    import csv
    if not rows:
        return
    names = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names)
        writer.writeheader()
        writer.writerows(rows)


def plan(config):
    for curve in config["curves"]:
        yield {"phase": "mechanism", "scenario": "known_two_host_packing", "seed": 0,
               "mix": "designed_witness", "lifetime": "long", "curve": curve, "overrides": {}}
    for phase, seeds in (("development", config["development_seeds"]), ("heldout", config["heldout_seeds"])):
        for mix in config["mixes"]:
            for lifetime in config["lifetimes"]:
                for seed in seeds:
                    yield {"phase": phase, "scenario": "base", "seed": seed, "mix": mix,
                           "lifetime": lifetime, "curve": config["curves"][0], "overrides": {}}
    for curve in config["curves"][1:]:
        for seed in config["heldout_seeds"]:
            yield {"phase": "power_sensitivity", "scenario": "base", "seed": seed,
                   "mix": "mixed", "lifetime": "long", "curve": curve, "overrides": {}}
    for field, values in config["sensitivity"].items():
        for value in values:
            for seed in config["heldout_seeds"]:
                yield {"phase": "assumption_sensitivity", "scenario": f"{field}={value}",
                       "seed": seed, "mix": "mixed", "lifetime": "long",
                       "curve": config["curves"][0], "overrides": {field: value}}


def run_one(case, policy_name, config):
    simulation = SimulationConfig(**config["base_simulation"])
    simulation = replace(simulation, **case["overrides"])
    mechanism = case["phase"] == "mechanism"
    if mechanism:
        simulation = replace(simulation, arrival_window_s=1000, control_interval_s=2000,
                             wake_latency_s=0, idle_timeout_s=0)
    tasks = witness() if mechanism else generate(case["seed"], case["mix"], case["lifetime"], config["instance_count"])
    pool = hosts(4 if mechanism else config["host_count"])
    curve = load_curve(case["curve"])
    if policy_name.startswith("legacy"):
        policy = LRMMT(simulation, curve, memory_aware=policy_name.endswith("memory"))
        policy.name = policy_name
    else:
        policy = EnergyFirst(simulation, curve, memory_aware=policy_name.endswith("memory"), controller=not mechanism)
    engine = InstrumentedSimulator(pool, simulation, curve, policy)
    result = engine.run(tasks)
    if result["completed_instances"] != len(tasks) or result["rejected_instances"] or result["unfinished_instances"]:
        raise AssertionError("Work conservation failed")
    if engine.running or engine.waiting or any(h.reservations for h in engine.hosts.values()):
        raise AssertionError("Reservations remain after drain")
    components = sum(result[k] for k in ("sleep_energy_j", "waking_energy_j", "active_energy_j",
                                         "wake_transition_extra_energy_j", "migration_extra_energy_j"))
    if not math.isclose(components, result["energy_j"], abs_tol=1e-6, rel_tol=1e-10):
        raise AssertionError("Energy components do not reconcile")
    request_map = {t.instance_id: t for t in tasks}
    pauses = defaultdict(float)
    for migration in engine.migration_log:
        pauses[migration["instance_id"]] += migration["pause_s"]
    if len(engine.records) != len(tasks) or len({r["instance_id"] for r in engine.records}) != len(tasks):
        raise AssertionError("Outcome IDs do not reconcile")
    for record in engine.records:
        expected = request_map[record["instance_id"]].duration_s + pauses[record["instance_id"]]
        if not math.isclose(record["finish_s"] - record["start_s"], expected, abs_tol=1e-6):
            raise AssertionError("Completion time does not include exact migration pause")
    for sample in engine.samples:
        if sample["cpu_used"] > sample["cpu_capacity"] + 1e-8 or sample["memory_used"] > sample["memory_capacity"] + 1e-10:
            raise AssertionError("Sampled capacity violation")
    result.update({**{k: v for k, v in case.items() if k != "overrides"},
                   "data_source": "synthetic", "workload_sha256": workload_hash(tasks),
                   "workload_cpu_heavy_fraction": MIXES[case["mix"]][0] if not mechanism else None,
                   "policy_diagnostics": dict(policy.diagnostics), "validation_passed": True,
                   "controller_enabled": not mechanism})
    # Keep outcome, migration and capacity traces for the analytic mechanism;
    # other runs retain summaries to keep the study compact.
    details = {"instances": engine.records, "migrations": engine.migration_log,
               "samples": engine.samples} if mechanism else None
    return result, details


def summarize_pairs(results, config):
    grouped = defaultdict(dict)
    for result in results:
        if result["policy"] in POLICIES:
            key = tuple(result[k] for k in ("phase", "scenario", "mix", "lifetime", "curve", "seed"))
            grouped[key][result["policy"]] = result
    pairs = []
    for key, policies in grouped.items():
        if set(policies) != set(POLICIES):
            raise AssertionError("Incomplete policy pair")
        cpu, memory = [policies[p] for p in POLICIES]
        pairs.append({**dict(zip(("phase", "scenario", "mix", "lifetime", "curve", "seed"), key)),
                      **assess_pair(cpu, memory, config["acceptance"]),
                      "cpu_energy_kwh": cpu["energy_kwh"], "memory_energy_kwh": memory["energy_kwh"],
                      "cpu_migrations": cpu["migrations"], "memory_migrations": memory["migrations"],
                      "cpu_mean_wait_s": cpu["mean_wait_s"], "memory_mean_wait_s": memory["mean_wait_s"],
                      "cpu_fragmentation": cpu["mean_fragmentation_index"], "memory_fragmentation": memory["mean_fragmentation_index"]})
    episodes = defaultdict(list)
    for pair in pairs:
        if pair["phase"] in ("heldout", "power_sensitivity", "assumption_sensitivity"):
            key = tuple(pair[k] for k in ("phase", "scenario", "mix", "lifetime", "curve"))
            episodes[key].append(pair)
    intervals = []
    for key, values in episodes.items():
        stats = paired_bootstrap([v["energy_reduction_pct"] for v in values],
                                  **{("repetitions" if k == "resamples" else k): v for k, v in config["bootstrap"].items()})
        intervals.append({**dict(zip(("phase", "scenario", "mix", "lifetime", "curve"), key)), **stats,
                          "accepted_episodes": sum(v["accepted"] for v in values),
                          "positive_energy_episodes": sum(v["energy_reduction_pct"] > 0 for v in values),
                          "ci_excludes_zero_in_savings_direction": stats["ci_lower_pct"] > 0})
    return pairs, intervals


def main(argv=None):
    from RAW_Alibaba.run import main as raw_main
    return raw_main(argv)


def historical_synthetic_main(argv=None):
    raise RuntimeError("Synthetic experiments are disabled; archived outcomes are diagnostic-only. Use the Alibaba runner.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "reports")
    parser.add_argument("--phase", choices=("all", "mechanism", "development", "heldout", "power_sensitivity", "assumption_sensitivity"), default="all")
    args = parser.parse_args(argv)
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if set(config["development_seeds"]) & set(config["heldout_seeds"]):
        raise ValueError("Development and heldout seeds overlap")
    cases = [c for c in plan(config) if args.phase == "all" or c["phase"] == args.phase]
    if not cases:
        raise ValueError("Empty study")
    args.output.mkdir(parents=True, exist_ok=True)
    root = HERE.parent
    sources = list(HERE.glob("*.py")) + list((root / "ecosched").glob("*.py")) + [root / "ROHAN_Task/policies.py", root / "ecosched/power_curves.json"]
    hashes = {str(p.relative_to(root)).replace('\\', '/'): digest(p) for p in sorted(sources)}
    frozen = {"protocol": config, "config_sha256": digest(CONFIG), "source_sha256": hashes,
              "planned_cases": len(cases), "policy_frozen_before_evaluation": True,
              "parameter_selection_performed": False, "python_version": sys.version.split()[0]}
    (args.output / "frozen_protocol.json").write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    results = []
    for i, case in enumerate(cases):
        names = POLICIES + ("legacy_lr_mmt", "legacy_lr_mmt_memory") if case["phase"] == "development" else POLICIES
        for name in names:
            result, details = run_one(case, name, config)
            results.append(result)
            if details:
                folder = args.output / "mechanism" / case["curve"] / name
                folder.mkdir(parents=True, exist_ok=True)
                for label, records in details.items():
                    csv_write(folder / f"{label}.csv", records)
        if (i + 1) % 10 == 0 or i + 1 == len(cases):
            print(f"Cases {i+1}/{len(cases)}; validated runs {len(results)}; phase {case['phase']}", flush=True)
    for source, value in hashes.items():
        if digest(root / source) != value:
            raise RuntimeError("Study source changed during evaluation")
    pairs, intervals = summarize_pairs(results, config)
    # Analytics and raw summaries remain separate; nested metrics stay in JSON.
    scalar = [{k: v for k, v in r.items() if not isinstance(v, (dict, list))} for r in results]
    csv_write(args.output / "runs.csv", scalar)
    csv_write(args.output / "paired_comparisons.csv", pairs)
    csv_write(args.output / "confidence_intervals.csv", intervals)
    (args.output / "summaries.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validation = {"passed": True, "planned_cases": len(cases), "completed_runs": len(results),
                  "paired_comparisons": len(pairs), "heldout_comparisons": sum(p["phase"] == "heldout" for p in pairs),
                  "all_runs_conserved_work": all(r["validation_passed"] for r in results),
                  "total_completed_instances": sum(r["completed_instances"] for r in results),
                  "raw_alibaba_replay_performed": False, "yaksh_data_used": False,
                  "checks": ["source/config frozen before evaluation", "disjoint development/heldout seeds",
                             "identical paired workloads/config", "unique outcomes and full drain", "energy components reconcile",
                             "completion durations plus migration pauses", "sampled capacity limits"]}
    (args.output / "validation.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validation, indent=2), flush=True)


if __name__ == "__main__":
    main()
