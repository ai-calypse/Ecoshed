"""Compatible-case scheduler comparison view."""
import streamlit as st
from ARNAV_Task.dashboard.data_service import get_data
from ARNAV_Task.dashboard.components.filters import case_filters, baseline_filter, metric_filter
from ARNAV_Task.dashboard.components.metrics import page_header
from ARNAV_Task.dashboard.components.charts import bar, reductions, show
from ARNAV_Task.dashboard.components.tables import research_table, sources
from ARNAV_Task.dashboard.constants import metric_title
from ARNAV_Task.analysis.metrics import METRICS

data = get_data()
page_header("Scheduler comparison", "Rank and compare schedulers within one workload and SPECpower curve.")
size, curve, policies = case_filters(data, "comparison", default_largest=True)
left, right = st.columns(2)
with left:
    baseline = baseline_filter(data, "comparison")
with right:
    metric = metric_filter("comparison")
frame = data.relative(metric, baseline, size=size, curve=curve, policies=policies)
show(bar(frame, metric, metric_title(metric), data.policy_labels), "comparison_metric", METRICS[metric][1])
show(reductions(frame, f"Energy reduction vs {data.policy_labels[baseline]}", data.policy_labels),
     "comparison_reduction", "Positive saves energy; negative consumes more. The reference is retained even when hidden from the displayed policies.")
st.subheader("Comparable outcomes and ranking")
st.caption(f"Rank minimizes the selected metric (completed instances is maximized). Missing values are unranked. "
           f"metric_delta = candidate − baseline, in {METRICS[metric][0]}; energy reduction uses the separate positive-savings convention.")
research_table(frame.sort_values("rank"), "scheduler_comparison", metric=metric, columns=list(dict.fromkeys([
    "policy", "policy_label", "workload_groups", "power_curve", metric, "rank", "baseline", "baseline_value",
    "metric_delta", "energy_reduction_pct", "source_individual_summary"])))
sources(frame)
