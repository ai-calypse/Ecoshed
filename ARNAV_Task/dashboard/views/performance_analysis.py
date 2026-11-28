"""Performance costs and descriptive Pareto view."""
import streamlit as st
from ARNAV_Task.dashboard.data_service import get_data, pareto_frontier
from ARNAV_Task.dashboard.components.filters import case_filters, metric_filter
from ARNAV_Task.dashboard.components.metrics import page_header
from ARNAV_Task.dashboard.components.charts import bar, scatter, show
from ARNAV_Task.dashboard.components.tables import research_table
from ARNAV_Task.dashboard.constants import METRIC_LABELS

data = get_data()
page_header("Performance analysis", "Performance costs and descriptive energy/performance trade-offs within one comparable case.")
size, curve, policies = case_filters(data, "performance", default_largest=True)
frame = data.runs(policies=policies, sizes=[size], curves=[curve])
options = ("mean_wait_s", "p95_wait_s", "migrations", "migration_pause_instance_seconds", "mean_active_hosts",
           "peak_active_hosts", "overload_host_time_fraction", "mean_fragmentation_index",
           "cpu_stranded_by_memory_core_seconds", "memory_stranded_by_cpu_unit_seconds")
metric = metric_filter("performance", options, "mean_wait_s")
show(bar(frame, metric, METRIC_LABELS[metric], data.policy_labels), "performance_metric",
     "Initial wait includes queueing and wake delay; migration pause is separate. P95 is a within-run percentile and is never averaged across cases.")
st.caption("Reservation pressure is a modeled overload/SLA proxy based on reservations, not observed application SLA failures. "
           "Stranded-resource diagnostics use the recorded core-seconds and normalized-memory-unit-seconds.")
st.subheader("Descriptive Pareto comparison")
y = st.selectbox("Performance objective to minimize", ("mean_wait_s", "overload_host_time_fraction", "migrations", "mean_active_hosts"),
                 format_func=METRIC_LABELS.get, key="pareto_objective")
frontier = pareto_frontier(frame, y=y)
show(scatter(frontier, y, data.policy_labels), "performance_scatter",
     "Both modeled energy and the selected performance objective are minimized. Diamonds are non-dominated among the displayed policies only; this is not a global optimum.")
research_table(frontier, "performance_tradeoff", columns=["policy", "workload_groups", "power_curve", "energy_kwh", y,
                "pareto_efficient", "source_individual_summary"])
