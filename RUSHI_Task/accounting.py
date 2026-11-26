"""Exact energy accounting for one simulator run and for a policy pair.

Brave's engine (ecosched/engine.py) charges every host for every simulated
second in exactly one state:

    sleep   -> sleep_watts (5 W in the active config)
    waking  -> the curve's 100 % watts, for wake_latency_s after each wake-up
    active  -> curve.power(requested CPU / CPU capacity); P(0) when it has no work

So the energy of a run can be written as

    E = Ps*S + Pfull*W + P0*A + D + X

where S, W and A are sleep, waking and active host-seconds, D is the extra
load-dependent energy above P(0) while active, and X is any per-event extra
energy (wake transition / migration watts; both are 0 in the active config).
Because S + W + A = hosts * stop_time, the energy difference between two runs
on the same curve is exactly

    dE = Ps*d(hosts*stop) + (P0-Ps)*dA + (Pfull-Ps)*dW + dD + dX

and dA splits further into hosts that were running work and hosts that were
powered on with nothing to run (waiting for the idle timeout).  Every number
here comes from fields the simulator already saved in summary.json.
"""
import math

TOLERANCE_J = 1e-3  # 1 mJ on totals of ~10^7-10^8 J; float rounding only


def _close(a, b, scale=1.0):
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=TOLERANCE_J * max(1.0, scale))


def run_breakdown(summary, curve):
    """Split one run's host-time and energy into the states the engine charges."""
    config = summary["config"]
    sleep_watts, idle_watts, full_watts = config["sleep_watts"], curve.watts[0], curve.watts[-1]
    hosts = len(summary["host_energy_j"])
    total_s = hosts * summary["stop_time_s"]
    waking_s = summary["waking_energy_j"] / full_watts if full_watts else 0.0
    powered_s = summary["active_host_seconds"]  # engine counts every state except sleep
    on_s = powered_s - waking_s
    sleep_s = total_s - powered_s
    idle_on_s = summary["powered_idle_host_seconds"]
    running_s = on_s - idle_on_s
    extra_j = summary["wake_transition_extra_energy_j"] + summary["migration_extra_energy_j"]
    idle_floor_j = idle_watts * on_s
    dynamic_j = summary["active_energy_j"] - idle_floor_j

    if not _close(waking_s, summary["wakeups"] * config["wake_latency_s"]):
        raise ValueError("Waking time does not equal wake-ups x wake latency")
    if not _close(sleep_s * sleep_watts, summary["sleep_energy_j"], summary["sleep_energy_j"]):
        raise ValueError("Sleep energy does not equal sleep host-seconds x sleep watts")
    if not _close(running_s + waking_s, summary["busy_host_seconds"], summary["busy_host_seconds"]):
        raise ValueError("Busy host-seconds do not reconcile with running + waking time")
    if running_s < -1e-6 or dynamic_j < -TOLERANCE_J:
        raise ValueError("Negative running time or load-dependent energy")
    rebuilt = sleep_watts * sleep_s + full_watts * waking_s + idle_watts * on_s + dynamic_j + extra_j
    if not _close(rebuilt, summary["energy_j"], summary["energy_j"]):
        raise ValueError("Energy components do not add up to the run total")

    return {
        "sleep_watts": sleep_watts, "idle_watts": idle_watts, "full_watts": full_watts,
        "hosts": hosts, "total_host_s": total_s, "sleep_s": sleep_s, "waking_s": waking_s,
        "on_s": on_s, "running_s": running_s, "idle_on_s": idle_on_s,
        "energy_j": summary["energy_j"], "idle_floor_j": idle_floor_j,
        "dynamic_j": dynamic_j, "extra_j": extra_j,
    }


# Order matters: this is the row order used in tables and charts.
GAP_PARTS = (
    ("on_running_work_j", "Servers switched on longer: running work"),
    ("on_without_work_j", "Servers switched on longer: no work, waiting to sleep"),
    ("load_dependent_j", "Load-dependent power (same work, different load per server)"),
    ("wakeups_j", "Wake-ups (each one runs at full power for 10 s)"),
    ("longer_run_j", "Different simulated run length"),
    ("extra_transition_j", "Extra transition energy (configured as 0)"),
)


def pair_gap(base, other, curve):
    """Exact decomposition of other.energy - base.energy (same curve and config)."""
    if base["config"] != other["config"] or base["power_curve"] != other["power_curve"]:
        raise ValueError("Only runs with the same curve and simulator config can be compared")
    a, b = run_breakdown(base, curve), run_breakdown(other, curve)
    ps, p0, pfull = a["sleep_watts"], a["idle_watts"], a["full_watts"]
    parts = {
        "on_running_work_j": (p0 - ps) * (b["running_s"] - a["running_s"]),
        "on_without_work_j": (p0 - ps) * (b["idle_on_s"] - a["idle_on_s"]),
        "load_dependent_j": b["dynamic_j"] - a["dynamic_j"],
        "wakeups_j": (pfull - ps) * (b["waking_s"] - a["waking_s"]),
        "longer_run_j": ps * (b["total_host_s"] - a["total_host_s"]),
        "extra_transition_j": b["extra_j"] - a["extra_j"],
    }
    total = b["energy_j"] - a["energy_j"]
    if not _close(sum(parts.values()), total, max(a["energy_j"], b["energy_j"])):
        raise ValueError("Pair decomposition does not add up to the energy difference")
    return {"total_j": total, **parts,
            "base_on_hours": a["on_s"] / 3600, "other_on_hours": b["on_s"] / 3600,
            "base_running_hours": a["running_s"] / 3600, "other_running_hours": b["running_s"] / 3600,
            "base_idle_on_hours": a["idle_on_s"] / 3600, "other_idle_on_hours": b["idle_on_s"] / 3600,
            "base_wakeups": base["wakeups"], "other_wakeups": other["wakeups"]}


def band_slopes(curve):
    """Watts added by each +10 % CPU band of the SPECpower curve."""
    return [{"band": f"{10 * i}-{10 * (i + 1)}%", "added_watts": curve.watts[i + 1] - curve.watts[i]}
            for i in range(10)]


def wake_score_cost(curve, sleep_watts):
    """Extra LR-MMT power score for waking a sleeping host instead of using an
    empty powered-on host. In ROHAN_Task/policies.py the score is
    (P(after) - P(before)) / max(1, Pfull - P0); before is sleep_watts for a
    sleeping host and P(0) for an empty powered-on host, so the difference is
    (P0 - sleep_watts) / scale whatever the task size."""
    scale = max(1.0, curve.watts[-1] - curve.watts[0])
    return (curve.watts[0] - sleep_watts) / scale


def break_even_imbalance(curve, sleep_watts, weight):
    """Smallest improvement in |CPU% - memory%| (0..1) that the memory term
    would need to outweigh one wake-up's power score. Above 1.0 is impossible."""
    return wake_score_cost(curve, sleep_watts) / weight if weight > 0 else math.inf


def small_task_score_gap(curve, cpu_fraction, busy_utilization):
    """Power-score difference between an empty powered-on host and a host already
    at busy_utilization, for a task needing cpu_fraction of one host's CPU."""
    scale = max(1.0, curve.watts[-1] - curve.watts[0])
    empty = curve.power(min(1.0, cpu_fraction)) - curve.power(0.0)
    after = min(1.0, busy_utilization + cpu_fraction)
    busy = curve.power(after) - curve.power(busy_utilization)
    return (empty - busy) / scale
