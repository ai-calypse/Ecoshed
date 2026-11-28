"""D5 findings and offline recordings view."""
import streamlit as st
from ARNAV_Task.dashboard.data_service import get_data, DashboardDataError
from ARNAV_Task.dashboard.components.filters import case_filters
from ARNAV_Task.dashboard.components.metrics import page_header, kpis
from ARNAV_Task.dashboard.components.charts import gap_waterfall, timeline, show
from ARNAV_Task.dashboard.components.tables import research_table

data = get_data()
page_header("Research findings", "Rushi Jhala's merged D5 analysis · existing accounting and recorded observations.")
pairs = data.comparisons(primary=True)
wins = pairs[pairs.energy_reduction_pct > 0]
st.write(f"The memory-aware variant saves modeled energy in {len(wins)} of {len(pairs)} cases. "
         "The table below retains both savings and losses; case selection does not imply independent replication.")
with st.expander("Cases with positive modeled energy reduction"):
    research_table(wins, "positive_primary_cases", columns=["workload_groups", "power_curve", "energy_reduction_pct", "source_comparison"])
size, curve, _ = case_filters(data, "findings", primary=True, policy_selection=False, default_largest=True)
gap = data.d5("pair_energy_gap", size=size, curve=curve).iloc[0]
score = data.d5("placement_score_arithmetic", curve=curve).iloc[0]
cpu, mem = (data.artifacts.index[(size, curve, p)] for p in ("lr_mmt", "lr_mmt_memory"))
reduction = data.comparisons(primary=True, sizes=[size], curves=[curve]).iloc[0].energy_reduction_pct
kpis([("Energy reduction", f"{reduction:+.3f}%", "Memory-aware versus CPU LR-MMT; negative adds consumption"),
      ("Mean active hosts", f"{cpu['mean_active_hosts']:.2f} → {mem['mean_active_hosts']:.2f}", "Time-weighted, including waking hosts"),
      ("Mean wait (s)", f"{cpu['mean_wait_s']:.2f} → {mem['mean_wait_s']:.2f}", "Initial wait, separate from migration pause")])
interpretation, recordings, evidence = st.tabs(["Energy and placement", "Offline host timelines", "D5 source evidence"])
with interpretation:
    show(gap_waterfall(gap), "findings_gap",
         "Positive components increase energy; negative components offset it. These are D5's existing exact gap components, not a new energy model.")
    if gap.energy_change_kwh > 0:
        share = 100 * gap.on_running_work_kwh / gap.energy_change_kwh
        st.write(f"In this case, the extra on-time while running work accounts for {share:.1f}% of the net energy gap. "
                 f"Total powered-host time changes by {gap.servers_on_hours_change:+.2f} host-hours.")
    else:
        st.write("This case saves energy. The same accounting includes gains and losses without extrapolating the large-workload explanation to every case.")
    st.subheader("How the balance score changes placement")
    st.write(f"The implemented memory-aware rule adds {score.memory_balance_weight:g} × |CPU fraction − memory fraction| "
             "to normalized incremental power. D5's recorded score arithmetic shows the relative strength of that term among already powered hosts.")
    st.write(f"For the selected curve's largest-workload score example, the balance advantage over the busy-server power advantage "
             f"is {score.balance_advantage_over_power_advantage:.2f}×. This helps explain spreading across more powered servers.")
    st.caption("Score arithmetic uses D5's largest-workload reference snapshot, regardless of the case selected above. "
               "The read-only observer records choices; no policy or weight is tuned here.")
    research_table(data.d5("placement_score_arithmetic", curve=curve), "placement_score")
    st.subheader("Controller activity and performance trade-offs")
    research_table(data.d5("controller_diagnostics", size=size, curve=curve), "controller_diagnostics")
    research_table(data.d5("tradeoffs", size=size, curve=curve), "d5_tradeoffs")
    st.caption("Lower reservation pressure and waiting can accompany higher energy. Pressure remains a modeled overload/SLA proxy; these outcomes do not identify a universally superior scheduler.")
with recordings:
    frame = data.timelines(size, curve)
    fields = {"powered_hosts": "Powered hosts", "hosts_running_work": "Hosts running work",
              "mean_cpu_of_hosts_running_work": "Mean requested CPU of busy hosts",
              "mean_memory_of_hosts_running_work": "Mean requested memory of busy hosts"}
    field = st.selectbox("Recorded host metric", list(fields), format_func=fields.get, key="findings_timeline_metric")
    times = sorted(frame.time_s.unique().tolist())
    start, end = st.select_slider("Recorded time window (simulation seconds)", options=times,
                                  value=(times[0], times[-1]), key="findings_time_window")
    shown = frame[frame.time_s.between(start, end)]
    show(timeline(shown, field, fields[field], data.policy_labels), "findings_timeline",
         f"Previously recorded simulation outputs sampled at control ticks. {len(times)} timestamps per policy in this case. "
         "These are offline observations, not live scheduler execution; sample means differ from event-time-weighted means.")
    research_table(shown, "offline_host_recordings")
with evidence:
    figures = {"energy_gap_breakdown.svg": "Energy-gap breakdown", "servers_over_time.svg": "Servers over time",
               "who_picks_the_emptier_server.svg": "Placement disagreement", "wait_by_task_type.svg": "Waiting by task type"}
    name = st.selectbox("Original D5 figure", list(figures), format_func=figures.get, key="d5_figure")
    try:
        st.image(data.asset(name), caption=f"Rushi's original D5 figure · RUSHI_Task/reports/{name}", width="stretch")
        st.download_button("Download original SVG", data.asset(name), name, mime="image/svg+xml", key="download_d5_svg")
        st.download_button("Download D5 report", data.asset("REPORT.md"), "EcoSched_D5_REPORT.md", mime="text/markdown", key="download_d5_report")
    except DashboardDataError as exc:
        st.warning(str(exc))
    st.caption("Source: RUSHI_Task/reports/REPORT.md, accounting tables, placement observations and recordings. "
               "The same-job extension is excluded. D5 result reproduction excludes Python version and manifest hash; it does not resolve lineage.")
