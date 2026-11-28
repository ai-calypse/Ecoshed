"""Energy and power-model sensitivity view."""
import pandas as pd
import plotly.express as px
import streamlit as st
from ARNAV_Task.dashboard.data_service import get_data
from ARNAV_Task.dashboard.components.filters import case_filters, baseline_filter
from ARNAV_Task.dashboard.components.metrics import page_header
from ARNAV_Task.dashboard.components.charts import (trend, reductions, primary_heatmap, stacked_energy, show, finish)
from ARNAV_Task.dashboard.components.tables import research_table
from ARNAV_Task.dashboard.constants import POLICY_COLORS

data = get_data()
page_header("Energy analysis", "Modeled energy, efficiency, baseline-relative savings and D5 accounting.")
size, curve, policies = case_filters(data, "energy", default_largest=True)
baseline = baseline_filter(data, "energy")
curves = data.runs(policies=policies, curves=[curve])
show(trend(curves, "energy_kwh", f"Workload-size sensitivity · {data.curve_labels[curve]}", data.policy_labels),
     "energy_sizes", "Each point is an individual run. The selected curve is held fixed; these samples overlap.")
show(trend(curves, "wh_per_completed_instance", "Energy efficiency per completed instance", data.policy_labels),
     "energy_efficiency", "Wh per completed instance includes the complete simulated energy window; task groups are not the denominator.")
pairs = data.comparisons(baseline, sizes=[size], curves=[curve], policies=policies)
show(reductions(pairs, f"Energy reduction vs {data.policy_labels[baseline]}", data.policy_labels), "energy_reductions",
     "Energy reduction = 100 × (baseline − candidate) / baseline. Positive saves; negative adds consumption.")
show(primary_heatmap(data.comparisons(primary=True), data.curve_labels), "energy_primary",
     "All nine primary comparisons. The diverging scale is symmetric around zero, retaining the large-workload penalties.")
st.subheader("Power-curve sensitivity")
sensitivity = data.runs(policies=policies, sizes=[size])
fig = px.bar(sensitivity, x="power_curve_label", y="energy_kwh", color="policy", barmode="group",
             color_discrete_map=POLICY_COLORS,
             hover_data=["workload_groups"],
             labels={"power_curve_label": "Separate SPECpower curve", "energy_kwh": "Modeled energy (kWh)"})
show(finish(fig, f"Separate power models · {size:,} groups", labels=data.policy_labels), "energy_sensitivity",
     "Each curve is an alternative surrogate model in a fresh simulator. No cross-curve average or replication-based uncertainty is inferred.")
watts = []
for name, row in data.artifacts.curve_data["curves"].items():
    for i, value in enumerate(row["watts"]):
        watts.append({"curve": data.curve_labels[name], "target_load_pct": 100 * i / (len(row["watts"]) - 1),
                      "watts": value, "source": row["source"]})
power = pd.DataFrame(watts)
fig = px.line(power, x="target_load_pct", y="watts", color="curve", markers=True, hover_data=["source"],
              labels={"target_load_pct": "SPEC target load / modeled requested CPU (%)", "watts": "Whole-server AC power (W)"})
show(finish(fig, "Measured SPECpower points and linear interpolation"), "power_curves",
     "Active Idle is the zero-load measurement, not sleep. The selected curve applies uniformly to source host CPU fractions; no memory-power term is invented.")
decomposition = data.d5("run_energy_breakdown", size=size, curve=curve, policies=policies)
if decomposition.empty:
    st.info("No D5 decomposition rows for this selection.")
else:
    show(stacked_energy(decomposition, data.policy_labels), "energy_decomposition",
         "D5's existing accounting separates active idle floor, load-dependent, waking and sleeping energy. Components reconcile to the recorded modeled energy.")
with st.expander("Download energy comparisons and accounting"):
    research_table(pairs, "energy_pairs")
    research_table(decomposition, "energy_decomposition")
    research_table(power, "specpower_points")
