"""Sortable, downloadable tables retain identifiers, units and evidence paths."""
import streamlit as st
from ARNAV_Task.analysis.metrics import METRICS, SKEW_METRICS
from ARNAV_Task.dashboard.constants import metric_title, METRIC_LABELS


def column_label(name, metric=None):
    """Presentation headers only: the original fields and values remain intact."""
    labels = {"policy": "Policy ID", "policy_label": "Scheduler", "power_curve": "Power curve ID",
              "power_curve_label": "SPECpower curve", "workload_groups": "Workload (task groups)",
              "baseline": "Baseline policy ID", "baseline_label": "Baseline scheduler",
              "energy_reduction_pct": "Energy reduction (%) · positive saves",
              "baseline_energy_kwh": "Baseline energy (kWh)",
              "pressure_delta_percentage_points": "Pressure change (percentage points)",
              "pareto_efficient": "Non-dominated in selected case", "task_type": "Resource category ID",
              "category_label": "Resource category", "rank": "Rank in selected case",
              "source_individual_summary": "Source · individual summary", "source_table": "Source · D5 table"}
    if name in labels:
        return labels[name]
    if name in ("metric_delta", "baseline_value") and metric:
        unit = METRICS[metric][0]
        return f"{'Change vs baseline' if name == 'metric_delta' else 'Baseline value'} ({unit})"
    if name in METRICS:
        return metric_title(name)
    if name in SKEW_METRICS:
        return f"{METRIC_LABELS.get(name, name.replace('_', ' ').capitalize())} ({SKEW_METRICS[name][0]})"
    title = name.replace("_", " ").capitalize()
    for suffix, unit in (("_kwh", "kWh"), ("_pct", "%"), ("_s", "seconds")):
        if name.endswith(suffix):
            return f"{name[:-len(suffix)].replace('_', ' ').capitalize()} ({unit})"
    return title


def download_frame(frame, metric=None):
    return frame.rename(columns={name: column_label(name, metric) for name in frame})


def research_table(frame, key, *, columns=None, metric=None):
    if frame.empty:
        st.info("No observations for this selection. Change the filters to inspect supported cases.")
        return
    shown = frame.loc[:, columns] if columns else frame
    st.dataframe(shown, hide_index=True, width="stretch", alt=f"Research table: {key.replace('_', ' ')}",
                 column_config={name: st.column_config.Column(column_label(name, metric)) for name in shown})
    st.download_button("Download table as CSV", download_frame(shown, metric).to_csv(index=False).encode("utf-8"),
                       file_name=f"ecosched_{key}.csv", mime="text/csv", key=f"download_{key}")


def sources(frame):
    names = [name for name in frame if name.startswith("source_")
             and all(isinstance(value, str) for value in frame[name].dropna())]
    if names:
        with st.expander("Artifact sources and metric units"):
            st.dataframe(frame[names].drop_duplicates(), hide_index=True, width="stretch", alt="Artifact source references")
            st.caption("Values retain original artifact units. CSV downloads include source references where provided.")
