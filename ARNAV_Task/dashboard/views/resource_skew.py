"""Supported D5 task-type outcomes view."""
import plotly.express as px
import streamlit as st
from ARNAV_Task.dashboard.data_service import get_data
from ARNAV_Task.dashboard.constants import SKEW_LABELS, SKEW_COLORS, PRIMARY
from ARNAV_Task.dashboard.components.filters import case_filters
from ARNAV_Task.dashboard.components.metrics import page_header
from ARNAV_Task.dashboard.components.charts import bar, finish, show
from ARNAV_Task.dashboard.components.tables import research_table

data = get_data()
page_header("Resource-skew analysis", "Composition and supported task-type outcomes from Rushi's D5 analysis.")
size, curve, policies = case_filters(data, "skew", primary=True)
st.caption("D5 supports only the primary LR-MMT pair. First Fit and Best Fit have no recorded category-level outcomes.")
composition = data.composition(size)
fig = px.bar(composition, x="category_label", y="instances", color="task_type", color_discrete_map=SKEW_COLORS,
             hover_data=["share_pct", "source_table"], labels={"category_label": "Resource category", "instances": "Instances"})
show(finish(fig, f"Workload resource composition · {size:,} groups", labels=SKEW_LABELS), "skew_composition",
     "Composition counts are observed workload totals. A zero category count is distinct from an unavailable performance observation.")
st.caption("Let r = (requested CPU / median sampled host CPU) ÷ (requested memory / median sampled host memory). "
           "CPU-heavy: r > 2; memory-heavy: r < 0.5; otherwise balanced. Memory is normalized, not GB. Source: RAW_Alibaba/prepare.py.")
categories = st.multiselect("Resource categories", list(SKEW_LABELS), default=list(SKEW_LABELS),
                            format_func=SKEW_LABELS.get, key="skew_categories")
absent = composition[(composition.instances == 0) & composition.task_type.isin(categories)]
for label in absent.category_label:
    st.info(f"No observations: {label} has no instances in this workload. No waiting or migration outcome is assigned.")
outcomes = data.skew(size=size, curve=curve, policies=policies, categories=categories)
metric = st.selectbox("Category outcome", ("mean_wait_s", "p95_wait_s", "migrated_pct", "delayed_pct"),
                      format_func={"mean_wait_s": "Mean waiting time (seconds)", "p95_wait_s": "P95 waiting time (seconds)",
                                   "migrated_pct": "Instances migrated at least once (%)", "delayed_pct": "Instances with initial wait (%)"}.get,
                      key="skew_metric")
show(bar(outcomes, metric, "Recorded outcomes by resource category", data.policy_labels,
         x="category_label", x_title="Observed category"), "skew_outcomes",
     "P95 values remain separate by policy and category. Migrated percentage counts distinct instances; repeated transfers are not counted as additional instances.")
st.caption("Whole-run energy is not attributed to categories. No category-level energy model is supplied by these artifacts.")
research_table(outcomes, "resource_skew_outcomes")
with st.expander("Workload composition table"):
    research_table(composition, "workload_composition")
