"""Pure Plotly figures over validated rows; no experiment aggregation or imputation."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ARNAV_Task.dashboard.constants import (POLICY_COLORS, SKEW_COLORS, POLICIES, SIZES,
                                             PLOT_CONFIG, metric_title)


def finish(fig, title, *, y=None, labels=None, height=370):
    fig.update_layout(template="plotly_dark", title=dict(text=title, font=dict(size=16), x=0, xanchor="left"),
                      height=height, margin=dict(l=18, r=18, t=54, b=48),
                      font=dict(family="Arial, sans-serif", size=12, color="#CBD9E8"),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      legend=dict(title_text="", orientation="h", y=-.2, x=0, font=dict(size=11)),
                      hoverlabel=dict(namelength=-1, bgcolor="#17283B", bordercolor="#4C667F", font_color="#E5EDF6"),
                      hovermode="closest", colorway=list(POLICY_COLORS.values()),
                      modebar=dict(bgcolor="rgba(0,0,0,0)", color="#8FA8BF", activecolor="#63CFBF"))
    fig.update_xaxes(showgrid=False, automargin=True, linecolor="#35485E", tickfont=dict(color="#A8BED1"))
    fig.update_yaxes(gridcolor="#253549", zerolinecolor="#4A6076", automargin=True, tickfont=dict(color="#A8BED1"))
    for annotation in fig.layout.annotations:
        annotation.font.color = "#CBD9E8"
    if y:
        fig.update_yaxes(title_text=y)
    if labels:
        for trace in fig.data:
            trace.name = labels.get(trace.name, trace.name)
    return fig


def empty(title):
    fig = go.Figure()
    fig.add_annotation(text="No observations for this selection", showarrow=False, x=.5, y=.5, xref="paper", yref="paper")
    return finish(fig, title)


def bar(frame, metric, title, labels, *, x="policy_label", x_title="Scheduler"):
    if frame.empty or metric not in frame or frame[metric].notna().sum() == 0:
        return empty(title)
    hover = [k for k in ("workload_groups", "power_curve", "policy_label") if k in frame]
    fig = px.bar(frame.dropna(subset=[metric]), x=x, y=metric, color="policy", barmode="group",
                 color_discrete_map=POLICY_COLORS, category_orders={"policy": list(POLICIES)},
                 hover_data=hover, labels={metric: metric_title(metric), x: x_title,
                                          "workload_groups": "Task groups", "power_curve": "Curve", "policy": "Policy ID"})
    fig.update_yaxes(rangemode="tozero")
    if x == "policy_label":
        # Full policy names remain in the legend and hover; short IDs keep axes readable.
        fig.update_xaxes(tickvals=[labels[p] for p in POLICIES], ticktext=["First Fit", "Best Fit", "LR-MMT", "LR-MMT + memory"])
    return finish(fig, title, labels=labels)


def trend(frame, metric, title, labels):
    if frame.empty or frame[metric].notna().sum() == 0:
        return empty(title)
    fig = px.line(frame.sort_values("workload_groups"), x="workload_groups", y=metric,
                  color="policy", markers=True, color_discrete_map=POLICY_COLORS,
                  category_orders={"policy": list(POLICIES)},
                  hover_data=["power_curve"],
                  labels={"workload_groups": "Workload size (task groups)", "power_curve": "Curve", metric: metric_title(metric)})
    fig.update_xaxes(tickvals=list(SIZES), type="linear")
    fig.update_yaxes(rangemode="tozero")
    return finish(fig, title, labels=labels)


def reductions(frame, title, labels):
    if frame.empty:
        return empty(title)
    fig = px.bar(frame, x="policy_label", y="energy_reduction_pct", color="energy_reduction_pct",
                 color_continuous_scale=["#CD7680", "#1C2C3F", "#32B5A4"], color_continuous_midpoint=0,
                 hover_data=["policy", "baseline", "energy_kwh", "baseline_energy_kwh"],
                 labels={"policy_label": "Scheduler", "energy_reduction_pct": "Energy reduction (%)"})
    fig.add_hline(y=0, line_color="#8b9aaa")
    fig.update_xaxes(tickvals=[labels[p] for p in POLICIES], ticktext=["First Fit", "Best Fit", "LR-MMT", "LR-MMT + memory"])
    fig.update_layout(coloraxis_showscale=False)
    return finish(fig, title)


def primary_heatmap(frame, curve_labels):
    if frame.empty:
        return empty("Primary placement comparison")
    table = frame.pivot(index="power_curve", columns="workload_groups", values="energy_reduction_pct").reindex(index=list(curve_labels))
    bound = max(float(table.abs().max().max()), .01)
    fig = go.Figure(go.Heatmap(z=table.to_numpy(), x=[f"{s:,} groups" for s in table.columns],
                              y=[curve_labels[c] for c in table.index], zmin=-bound, zmax=bound, zmid=0,
                              colorscale=[[0, "#CD7680"], [.5, "#1C2C3F"], [1, "#32B5A4"]],
                              xgap=4, ygap=4,
                              text=table.to_numpy(), texttemplate="%{text:+.3f}%", textfont=dict(size=14, color="#F3F7FC"),
                              colorbar=dict(title="Reduction %"),
                              hovertemplate="%{y}<br>%{x}<br>Energy reduction %{z:+.4f}%<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    return finish(fig, "Energy reduction across the nine primary conditions", height=290)


def coverage(frame, curve_labels):
    table = frame.groupby(["power_curve", "workload_groups"]).size().unstack().reindex(index=list(curve_labels))
    fig = go.Figure(go.Heatmap(z=table.to_numpy(), x=[f"{x:,} groups" for x in table.columns],
                              y=[curve_labels[x] for x in table.index], colorscale=[[0,"#142235"],[1,"#235E62"]],
                              zmin=0, zmax=frame.policy.nunique(), showscale=False,
                              xgap=4, ygap=4, textfont=dict(color="#D5EEE9"),
                              text=table.to_numpy(), texttemplate="%{text} policies",
                              hovertemplate="%{y}<br>%{x}<br>%{z} active policy outcomes<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    return finish(fig, "Experiment matrix · separate outcomes in each cell", height=245)


def scatter(frame, y, labels):
    if frame.empty:
        return empty("Energy / performance trade-off")
    shown = frame.dropna(subset=["energy_kwh", y])
    fig = px.scatter(shown, x="energy_kwh", y=y, color="policy", color_discrete_map=POLICY_COLORS,
                     symbol="pareto_efficient", symbol_map={True: "diamond", False: "circle"},
                     hover_data=["policy_label", "workload_groups", "power_curve"],
                     labels={"energy_kwh": metric_title("energy_kwh"), y: metric_title(y), "pareto_efficient": "Non-dominated"})
    fig.update_traces(marker=dict(size=13, line=dict(width=1, color="#101D2C")))
    frontier = shown[shown.pareto_efficient.fillna(False)].sort_values("energy_kwh")
    if len(frontier) > 1:
        fig.add_trace(go.Scatter(x=frontier.energy_kwh, y=frontier[y], mode="lines", name="Descriptive frontier",
                                 line=dict(dash="dot", color="#607d8b"), hoverinfo="skip"))
    # Preserve symbols while replacing the policy portion of compound legend labels.
    for trace in fig.data:
        for policy, label in labels.items():
            if trace.name.startswith(policy + ","):
                trace.name = trace.name.replace(policy + ",", label + " ·", 1)
    return finish(fig, "Energy / performance · minimize both axes")


def stacked_energy(frame, labels):
    columns = {"idle_floor_kwh": "Active idle floor", "load_dependent_kwh": "Load-dependent power",
               "waking_kwh": "Waking", "asleep_kwh": "Sleeping"}
    long = frame.melt(id_vars=["policy", "policy_label"], value_vars=list(columns), var_name="component", value_name="kwh")
    long["component"] = long.component.map(columns)
    fig = px.bar(long, x="policy_label", y="kwh", color="component", barmode="stack",
                 color_discrete_sequence=["#5679A6", "#AA64B4", "#AD7C39", "#87AAA8"],
                 labels={"policy_label": "Scheduler", "kwh": "Modeled energy (kWh)"}, hover_data=["policy"])
    fig.update_xaxes(tickvals=[labels[p] for p in POLICIES], ticktext=["First Fit", "Best Fit", "LR-MMT", "LR-MMT + memory"])
    return finish(fig, "D5 energy decomposition · recorded run components")


def gap_waterfall(row):
    parts = {"on_running_work_kwh": "On with work", "on_without_work_kwh": "On without work",
             "load_dependent_kwh": "Load-dependent", "wakeups_kwh": "Wake-ups",
             "longer_run_kwh": "Longer run", "extra_transition_kwh": "Transitions"}
    fig = go.Figure(go.Waterfall(x=list(parts.values()) + ["Net gap"],
                                y=[row[k] for k in parts] + [0],
                                measure=["relative"] * len(parts) + ["total"],
                                increasing=dict(marker_color="#CD7680"), decreasing=dict(marker_color="#32B5A4"),
                                totals=dict(marker_color="#82A9D0"),
                                hovertemplate="%{x}<br>%{y:+.5f} kWh<extra></extra>"))
    return finish(fig, "D5 energy gap · memory-aware minus CPU LR-MMT", y="Energy increase (kWh)")


def timeline(frame, field, title, labels):
    if frame.empty:
        return empty(title)
    shown = frame.copy()
    shown["time_hours"] = shown.time_s / 3600
    unit = "fraction" if field.startswith("mean_") else "hosts"
    fig = px.line(shown, x="time_hours", y=field, color="policy", color_discrete_map=POLICY_COLORS,
                  hover_data=["time_s", "source_recording"],
                  labels={"time_hours": "Recorded simulation time (hours)", field: f"{title} ({unit})"})
    fig.update_traces(connectgaps=False)
    return finish(fig, title + " · offline sampled simulation", labels=labels)


def show(fig, key, context):
    st.plotly_chart(fig, width="stretch", theme=None, config=PLOT_CONFIG, key=f"plot_{key}", alt=fig.layout.title.text)
    st.caption(context)
