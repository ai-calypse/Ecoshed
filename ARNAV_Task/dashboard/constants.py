"""Presentation constants only; no experimental measurements or result claims."""
from ARNAV_Task.analysis.artifacts import POLICIES, PRIMARY, SIZES, CURVES, SKEWS
from ARNAV_Task.analysis.metrics import METRICS

POLICY_COLORS = dict(zip(POLICIES, ("#82A9D0", "#D2A56A", "#32B5A4", "#BA92CE")))
SKEW_LABELS = {"balanced": "Balanced", "cpu_heavy": "CPU-heavy", "memory_heavy": "Memory-heavy"}
SKEW_COLORS = {"balanced": "#82A9D0", "cpu_heavy": "#D2A56A", "memory_heavy": "#BA92CE"}
METRIC_LABELS = {
    "energy_kwh": "Modeled energy", "wh_per_completed_instance": "Energy per completed instance",
    "mean_active_hosts": "Mean active hosts", "peak_active_hosts": "Peak active hosts",
    "migrations": "Migration count", "migration_pause_instance_seconds": "Migration pause",
    "mean_wait_s": "Mean waiting time", "p95_wait_s": "P95 waiting time",
    "overload_host_time_fraction": "Reservation pressure (modeled SLA proxy)",
    "rejected_instances": "Rejected instances", "unfinished_instances": "Unfinished instances",
    "completed_instances": "Completed instances", "mean_fragmentation_index": "Fragmentation index",
    "queue_instance_seconds": "Queue time", "p95_turnaround_s": "P95 turnaround",
    "max_wait_s": "Maximum waiting time", "stop_time_s": "Simulation duration", "drain_time_s": "Drain time",
    "cpu_stranded_by_memory_core_seconds": "CPU capacity stranded by memory",
    "memory_stranded_by_cpu_unit_seconds": "Memory capacity stranded by CPU",
    "migrated_pct": "Instances migrated at least once", "delayed_pct": "Instances with initial wait",
}
EXTRA_UNITS = {"cpu_stranded_by_memory_core_seconds": "core-seconds",
               "memory_stranded_by_cpu_unit_seconds": "normalized-memory-unit-seconds",
               "migrated_pct": "percent", "delayed_pct": "percent"}
COMPARE_METRICS = tuple(k for k in METRICS if k not in ("stop_time_s", "drain_time_s", "p95_turnaround_s", "queue_instance_seconds", "max_wait_s"))
PAGES = (
    ("overview", "Research overview"), ("scheduler_comparison", "Scheduler comparison"),
    ("energy_analysis", "Energy analysis"), ("performance_analysis", "Performance analysis"),
    ("resource_skew", "Resource-skew analysis"), ("research_findings", "Research findings"),
    ("reproducibility", "Reproducibility"),
    ("live_replay", "Live Workload Replay"),
)
PLOT_CONFIG = {"displaylogo": False, "responsive": True,
               "toImageButtonOptions": {"format": "svg", "filename": "ecosched-research", "height": None, "width": None}}


def metric_title(name):
    unit = METRICS[name][0] if name in METRICS else EXTRA_UNITS.get(name, "")
    return f"{METRIC_LABELS.get(name, name)} ({unit})" if unit else METRIC_LABELS.get(name, name)
