"""Metric contracts; no cross-run percentile aggregation or invented observations."""
import math


METRICS = {
    "energy_kwh": ("kWh", "Modeled whole-cluster energy, including sleep and wake power."),
    "wh_per_completed_instance": ("Wh/instance", "1000 * energy_kwh / completed_instances; not per task group."),
    "mean_active_hosts": ("hosts", "Time-weighted powered hosts, including waking hosts."),
    "peak_active_hosts": ("hosts", "Maximum number of powered hosts, including waking hosts."),
    "migrations": ("transfers", "Number of stop-and-copy migrations."),
    "migration_pause_instance_seconds": ("instance-seconds", "Sum of instance pauses, including destination wake delay."),
    "mean_wait_s": ("seconds", "Instance-weighted initial wait, including queueing and wake delay."),
    "p95_wait_s": ("seconds", "Within-run 95th percentile; never average across runs or categories."),
    "max_wait_s": ("seconds", "Maximum initial instance wait."),
    "overload_host_time_fraction": ("fraction", "Modeled SLA proxy: CPU-or-memory reservation pressure above the configured threshold; not measured SLA violations."),
    "rejected_instances": ("instances", "Offered instances rejected by the simulator."),
    "unfinished_instances": ("instances", "Arrived instances neither completed nor rejected at the stopping rule."),
    "completed_instances": ("instances", "Completed independent instances, not task groups."),
    "mean_fragmentation_index": ("fraction", "Event-integrated normalized residual-resource fragmentation index."),
    "queue_instance_seconds": ("instance-seconds", "Queue time before dispatch, excluding subsequent wake delay."),
    "p95_turnaround_s": ("seconds", "Within-run 95th percentile of completion minus release."),
    "stop_time_s": ("seconds", "Maximum of arrival horizon and final completion."),
    "drain_time_s": ("seconds", "Simulation time beyond the arrival horizon."),
}
SKEW_METRICS = {
    "instances": ("instances", "Observed category count; an absent category has no outcome row."),
    "mean_wait_s": METRICS["mean_wait_s"],
    "p95_wait_s": METRICS["p95_wait_s"],
    "delayed_pct": ("percent", "Category instances with positive initial wait."),
    "placed_on_asleep_or_waking_server_pct": ("percent", "Category placements on asleep or waking hosts."),
    "migrated_pct": ("percent", "Category instances migrated at least once; not migration count."),
}


def definitions():
    """JSON-ready metadata shared by validation, exports and future dashboard."""
    return {
        "run_metrics": {k: {"unit": unit, "definition": definition}
                        for k, (unit, definition) in METRICS.items()},
        "energy_reduction_pct": {
            "unit": "percent",
            "definition": "100 * (baseline energy - candidate energy) / baseline energy; positive saves energy.",
        },
        "resource_skew_metrics": {k: {"unit": unit, "definition": definition}
                                  for k, (unit, definition) in SKEW_METRICS.items()},
        "missing_values": "JSON null / empty CSV field; no imputation.",
        "comparison_scope": "Identical workload size, SPECpower curve, simulation config and input-manifest reference.",
        "resource_skew_scope": "D5 primary LR-MMT pair only; no category energy allocation.",
        "percentiles": "Never averaged or pooled from summary percentiles.",
    }


def number(value, label, *, integer=False, maximum=None):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0
            or (integer and int(value) != value)
            or (maximum is not None and value > maximum)):
        raise ValueError(f"{label}: expected a finite nonnegative {'integer' if integer else 'number'}"
                         + (f" <= {maximum}" if maximum is not None else ""))
    return value


def metric(row, name):
    """Return an existing supported observation, or None; never substitute zero."""
    if name not in METRICS:
        raise ValueError(f"Unsupported run metric: {name}")
    value = row.get(name)
    if value is not None:
        number(value, name)
    return value


def wh_per_completed_instance(row):
    energy, completed = row.get("energy_kwh"), row.get("completed_instances")
    if energy is None or completed is None:
        return None
    number(energy, "energy_kwh")
    number(completed, "completed_instances", integer=True)
    return 1000 * energy / completed if completed else None


def energy_reduction(candidate, baseline):
    """Compare the same experimental case; a missing energy stays missing."""
    for key in ("workload_groups", "power_curve"):
        if key not in candidate or key not in baseline or candidate[key] != baseline[key]:
            raise ValueError(f"Cannot compare different or missing {key}")
    for key in ("config", "manifest_sha256"):
        if candidate.get(key) != baseline.get(key):
            raise ValueError(f"Cannot compare different {key}")
    a, b = candidate.get("energy_kwh"), baseline.get("energy_kwh")
    if a is None or b is None:
        return None
    number(a, "candidate energy_kwh")
    number(b, "baseline energy_kwh")
    if b == 0:
        raise ValueError("Baseline energy must be positive to calculate a reduction")
    return 100 * (b - a) / b


def difference(candidate, baseline, name):
    a, b = metric(candidate, name), metric(baseline, name)
    return a - b if a is not None and b is not None else None
