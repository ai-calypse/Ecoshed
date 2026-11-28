"""Presentation regression checks; underlying Phase 1 observations remain the authority."""
import io
import json
import tomllib
import unittest
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from ARNAV_Task.analysis.artifacts import ROOT, CURVES, SIZES
from ARNAV_Task.dashboard.data_service import DashboardData
from ARNAV_Task.dashboard.constants import POLICY_COLORS
from ARNAV_Task.dashboard.components.charts import bar, primary_heatmap, coverage
from ARNAV_Task.dashboard.components.tables import column_label, download_frame

APP = ROOT / "ARNAV_Task/dashboard/app.py"


class DashboardRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = DashboardData()

    def test_app_local_theme_is_dark_and_matches_scheduler_palette(self):
        config = tomllib.loads((APP.parent / ".streamlit/config.toml").read_text())
        self.assertEqual(config["theme"]["base"], "dark")
        self.assertEqual(config["theme"]["chartCategoricalColors"], list(POLICY_COLORS.values()))
        self.assertEqual(config["theme"]["primaryColor"], config["theme"]["sidebar"]["primaryColor"])

    def test_figures_have_dark_or_transparent_surfaces(self):
        figures = [bar(self.data.runs(sizes=[4000], curves=[CURVES[0]]), "energy_kwh", "Energy", self.data.policy_labels),
                   primary_heatmap(self.data.comparisons(primary=True), self.data.curve_labels),
                   coverage(self.data.runs(), self.data.curve_labels)]
        for fig in figures:
            self.assertEqual(fig.layout.paper_bgcolor, "rgba(0,0,0,0)")
            self.assertEqual(fig.layout.plot_bgcolor, "rgba(0,0,0,0)")
            self.assertNotEqual(fig.layout.font.color, "#233449")

    def test_readable_csv_headers_preserve_numeric_values_and_sources(self):
        frame = self.data.relative("energy_kwh", "lr_mmt", size=4000, curve=CURVES[0])
        columns = ["policy", "energy_kwh", "wh_per_completed_instance", "p95_wait_s", "baseline_value",
                   "metric_delta", "energy_reduction_pct", "source_individual_summary"]
        source = frame[columns]
        pretty = download_frame(source, "energy_kwh")
        self.assertIn("Modeled energy (kWh)", pretty)
        self.assertIn("Change vs baseline (kWh)", pretty)
        self.assertIn("P95 waiting time (seconds)", pretty)
        reread = pd.read_csv(io.StringIO(pretty.to_csv(index=False)))
        self.assertEqual(reread["Policy ID"].tolist(), source.policy.tolist())
        for actual, expected in zip(reread["Modeled energy (kWh)"], source.energy_kwh):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(reread["Source · individual summary"].tolist(), source.source_individual_summary.tolist())

    def test_reservation_pressure_fraction_is_not_relabeled_as_percent(self):
        self.assertIn("fraction", column_label("overload_host_time_fraction"))
        self.assertIn("modeled SLA proxy", column_label("overload_host_time_fraction"))

    def test_all_36_cases_match_phase1_export(self):
        exported = pd.read_csv(ROOT / "ARNAV_Task/reports/experiment_summary.csv")
        for size in SIZES:
            for curve in CURVES:
                shown = self.data.runs(sizes=[size], curves=[curve])
                expected = exported[(exported.workload_groups == size) & (exported.power_curve == curve)]
                self.assertEqual(len(shown), len(expected))
                for policy in shown.policy:
                    for metric in ("energy_kwh", "wh_per_completed_instance", "p95_wait_s", "migrations"):
                        self.assertAlmostEqual(shown.loc[shown.policy == policy, metric].iloc[0],
                                               expected.loc[expected.policy == policy, metric].iloc[0])

    def test_overview_surfaces_all_nine_cases_and_selected_tradeoff(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        self.assertFalse(app.exception)
        self.assertTrue(any(m.label == "Energy reduction" for m in app.metric))
        charts = [json.loads(p.proto.spec) for p in app.get("plotly_chart")]
        self.assertTrue(any("nine primary" in f["layout"]["title"]["text"] for f in charts))
        self.assertTrue(any("flowchart LR" in item.value for item in app.markdown))
        self.assertTrue(any("Provenance unresolved" in warning.value for warning in app.warning))

    def test_comparison_chart_updates_after_baseline_change(self):
        app = AppTest.from_file(str(APP), default_timeout=30).run()
        app.switch_page("views/scheduler_comparison.py").run()
        before = app.get("plotly_chart")[1].proto.spec
        app.selectbox(key="comparison_baseline").set_value("first_fit").run()
        self.assertFalse(app.exception)
        self.assertNotEqual(before, app.get("plotly_chart")[1].proto.spec)
        self.assertTrue((app.dataframe[0].value.baseline == "first_fit").all())


if __name__ == "__main__":
    unittest.main()
