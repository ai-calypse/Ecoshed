"""Research overview view."""
import streamlit as st
from ARNAV_Task.dashboard.data_service import get_data
from ARNAV_Task.dashboard.components.metrics import kpis, page_header
from ARNAV_Task.dashboard.components.filters import case_filters
from ARNAV_Task.dashboard.components.charts import show, coverage, bar, primary_heatmap
from ARNAV_Task.dashboard.components.tables import research_table

data = get_data()
page_header("Research overview", "A controlled placement ablation on existing Alibaba-derived simulation outcomes.")
with st.container(border=True, key="research_question", gap="xsmall"):
    st.caption("RESEARCH QUESTION")
    st.subheader("Can memory-aware placement save energy without shifting the cost to performance?")
    st.caption("Same workload and hosts. Same LR detector, MMT selector and power model. Only placement scoring changes.")
k = data.kpis()
kpis([("Active outcomes", f"{k['runs']:,}", "Separate policy/workload/power-curve runs"),
      ("Scheduling policies", str(k['policies']), "Only the approved active policies"),
      ("Workload sizes", str(k['sizes']), "Task groups preserve original instance multiplicity"),
      ("SPECpower curves", str(k['curves']), "Separate surrogate power models")])
kpis([("Completed instance replays", f"{k['completed']:,}", "Sum across experimental cases; not unique production instances"),
      ("Rejected / unfinished", f"{k['rejected']:,} / {k['unfinished']:,}", "Recorded work conservation"),
      ("Primary energy wins / losses", f"{k['wins']} / {k['losses']}", f"Memory-aware placement versus CPU LR-MMT across {k['primary_pairs']} cases"),
      ("Numerical validation", "PASS" if data.validation['numerical']['passed'] else "FAIL", "Independent of full lineage verification")])
st.subheader("Primary energy–performance trade-off")
size, curve, policies = case_filters(data, "overview", default_largest=True)
runs = data.runs(policies=policies, sizes=[size], curves=[curve])
primary = data.comparisons(primary=True, sizes=[size], curves=[curve]).iloc[0]
cpu = data.artifacts.index[(size, curve, "lr_mmt")]
memory = data.artifacts.index[(size, curve, "lr_mmt_memory")]
st.badge("Additional energy consumption" if primary.energy_reduction_pct < 0 else "Modeled energy saving",
         color="red" if primary.energy_reduction_pct < 0 else "green")
for col, label, value in zip(st.columns(4, gap="small"),
        ("Energy reduction", "Mean wait change", "Mean active-host change", "Pressure change"),
        (f"{primary.energy_reduction_pct:+.3f}%", f"{primary.mean_wait_delta_s:+.2f} s",
         f"{memory['mean_active_hosts'] - cpu['mean_active_hosts']:+.2f} hosts",
         f"{primary.pressure_delta_percentage_points:+.2f} pp")):
    col.metric(label, value, border=True)
st.caption("Memory-aware minus CPU LR-MMT for performance changes; negative means lower. Energy reduction is positive for savings. "
           "Pressure is a modeled reservation-pressure/SLA proxy, not measured violations. "
           "This primary contrast is shown independently of the policies selected for the case energy chart.")
pairs = data.comparisons(primary=True)
large = pairs[pairs.workload_groups == pairs.workload_groups.max()]
show(primary_heatmap(pairs, data.curve_labels), "overview_primary",
     "Nine primary conditions, with separate power curves. Teal saves energy; rose adds energy. The symmetric scale retains every adverse outcome.")
st.write(f"Memory-aware placement saves energy in {k['wins']} of {k['primary_pairs']} cases and uses more in {k['losses']}. "
         f"On the largest sample its energy change is an increase of {(-large.energy_reduction_pct).min():.2f}–"
         f"{(-large.energy_reduction_pct).max():.2f}% across the separate curves.")
st.caption("These deterministic, overlapping cases do not establish independent statistical replications or production electricity savings.")
case_tab, method_tab = st.tabs(["Case energy and table", "Experiment coverage and architecture"])
with case_tab:
    show(bar(runs, "energy_kwh", "Modeled energy by scheduler", data.policy_labels), "overview_energy",
         "Offline experimental results; identical workload and selected power curve. Lower energy does not imply better performance on every metric.")
with method_tab:
    show(coverage(data.runs(), data.curve_labels), "coverage", "Each cell counts separate policy outcomes. Curves are never blended within a simulation.")
    st.subheader("From trace to evidence")
    st.mermaid_chart('''%%{init: {"theme":"base","themeVariables":{"primaryColor":"#132B3D","primaryTextColor":"#DDEAF5","primaryBorderColor":"#2D6E70","lineColor":"#63CFBF","fontSize":"13px"}}}%%
flowchart LR
    A[Alibaba trace] --> B[Prepare & validate]
    B --> C[Fixed workload & hosts]
    C --> D[Shared simulation]
    D --> E[SPECpower energy]
    E --> F[Results & D5 analysis]
''', alt="Alibaba trace passes through independent preparation, fixed workloads, simulation, SPECpower energy and validated research analysis")
    st.caption("The primary pair shares LR/MMT control and migration/sleep mechanics. First Fit and Best Fit are additional baselines.")
with st.expander("Download the selected research outcomes"):
    research_table(runs, "overview_runs", columns=["workload_groups", "power_curve", "policy", "energy_kwh",
                   "wh_per_completed_instance", "completed_instances", "source_individual_summary"])
