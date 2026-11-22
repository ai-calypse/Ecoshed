"""Paired bootstrap across generated episodes, not across correlated tasks."""
import math
import random
from .instrumentation import percentile


def paired_bootstrap(values, repetitions=2000, seed=560, confidence=.95):
    if not values:
        raise ValueError("Need paired episode values")
    if not 0 < confidence < 1 or repetitions < 1:
        raise ValueError("Invalid bootstrap settings")
    if any(not math.isfinite(v) for v in values):
        raise ValueError("Bootstrap values must be finite")
    rng = random.Random(seed)
    n = len(values)
    means = [sum(rng.choice(values) for _ in range(n)) / n for _ in range(repetitions)]
    alpha = (1 - confidence) / 2
    return {"episodes": n, "mean_energy_reduction_pct": sum(values) / n,
            "ci_lower_pct": percentile(means, alpha), "ci_upper_pct": percentile(means, 1 - alpha),
            "confidence": confidence, "bootstrap_resamples": repetitions,
            "statistical_unit": "paired independently generated synthetic episode"}


def assess_pair(cpu, memory, budgets):
    if cpu["workload_sha256"] != memory["workload_sha256"] or cpu["config"] != memory["config"]:
        raise ValueError("Paired runs must share workload and simulator settings")
    reduction = 100 * (cpu["energy_kwh"] - memory["energy_kwh"]) / cpu["energy_kwh"]
    checks = {
        "energy": reduction >= budgets["minimum_energy_reduction_pct"],
        "same_completed_work": cpu["completed_instances"] == memory["completed_instances"] and not (
            cpu["rejected_instances"] or memory["rejected_instances"] or cpu["unfinished_instances"] or memory["unfinished_instances"]),
        "mean_wait": memory["mean_wait_s"] <= cpu["mean_wait_s"] + max(
            budgets["wait_tolerance_floor_s"], cpu["mean_wait_s"] * budgets["maximum_mean_wait_increase_fraction"]),
        "p95_wait": memory["p95_wait_s"] <= cpu["p95_wait_s"] + max(
            budgets["wait_tolerance_floor_s"], cpu["p95_wait_s"] * budgets["maximum_p95_wait_increase_fraction"]),
        "migrations": memory["migrations"] <= cpu["migrations"] + max(
            budgets["migration_tolerance_floor_count"], math.ceil(cpu["migrations"] * budgets["maximum_migration_increase_fraction"])),
        "pressure_proxy": memory["overload_host_time_fraction"] <= cpu["overload_host_time_fraction"] + budgets["maximum_overload_fraction_increase"],
    }
    return {"energy_reduction_pct": reduction, "accepted": all(checks.values()),
            **{f"passes_{name}": value for name, value in checks.items()}}
