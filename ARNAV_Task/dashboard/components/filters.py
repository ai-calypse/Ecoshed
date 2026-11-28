"""Case selection never pools incompatible experiment conditions."""
import streamlit as st
from ARNAV_Task.dashboard.constants import POLICIES, PRIMARY, SIZES, CURVES, METRIC_LABELS, COMPARE_METRICS


def case_filters(data, key, *, primary=False, policy_selection=True, default_largest=False):
    columns = st.columns([1, 2])
    size = columns[0].selectbox("Workload size (task groups)", SIZES, index=2 if default_largest else 0,
                                key=f"{key}_size", format_func=lambda x: f"{x:,}")
    curve = columns[1].selectbox("SPECpower curve", CURVES, format_func=data.curve_labels.get, key=f"{key}_curve")
    allowed = PRIMARY if primary else POLICIES
    policies = st.multiselect("Scheduling policies", allowed, default=list(allowed),
                              format_func=data.policy_labels.get, key=f"{key}_policies") if policy_selection else list(allowed)
    return size, curve, policies


def baseline_filter(data, key):
    return st.selectbox("Baseline policy", POLICIES, index=2, format_func=data.policy_labels.get, key=f"{key}_baseline")


def metric_filter(key, options=COMPARE_METRICS, default="energy_kwh"):
    return st.selectbox("Comparison metric", options, index=list(options).index(default),
                         format_func=lambda name: METRIC_LABELS.get(name, name), key=f"{key}_metric")
