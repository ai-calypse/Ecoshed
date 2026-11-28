"""Chart construction uses validated Alibaba outputs and retains their units."""
import unittest
import plotly.io as pio

from ARNAV_Task.dashboard.data_service import DashboardData, pareto_frontier
from ARNAV_Task.dashboard.constants import POLICY_COLORS, CURVES, COMPARE_METRICS
from ARNAV_Task.dashboard.components import charts


class DashboardChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=DashboardData()
        cls.frame=cls.data.runs(sizes=[4000],curves=[CURVES[0]])

    def test_all_comparison_metrics_construct_serializable_charts(self):
        for metric in COMPARE_METRICS:
            with self.subTest(metric=metric):
                fig=charts.bar(self.frame,metric,'Recorded metric',self.data.policy_labels)
                self.assertEqual(len(fig.data),4)
                self.assertTrue(pio.to_json(fig))
                for trace in fig.data:
                    policy=next(p for p in POLICY_COLORS if self.data.policy_labels[p]==trace.name)
                    self.assertEqual(trace.marker.color,POLICY_COLORS[policy])

    def test_trend_preserves_individual_workload_points(self):
        fig=charts.trend(self.data.runs(curves=[CURVES[0]]),'p95_wait_s','Within-run P95',self.data.policy_labels)
        self.assertTrue(all(len(trace.y)==3 for trace in fig.data))
        self.assertIn('seconds',fig.layout.yaxis.title.text)

    def test_heatmap_retains_negative_findings_and_zero_center(self):
        frame=self.data.comparisons(primary=True)
        fig=charts.primary_heatmap(frame,self.data.curve_labels)
        self.assertEqual(fig.data[0].zmid,0)
        self.assertEqual(fig.data[0].zmin,-fig.data[0].zmax)
        self.assertTrue(all(row[-1]<0 for row in fig.data[0].z))
        self.assertEqual(sum(len(row) for row in fig.data[0].z),9)

    def test_reduction_bars_keep_correct_sign_and_units(self):
        frame=self.data.comparisons('lr_mmt',sizes=[4000],curves=[CURVES[0]])
        fig=charts.reductions(frame,'Energy reduction',self.data.policy_labels)
        self.assertIn('%',fig.layout.yaxis.title.text)
        self.assertEqual(list(fig.data[0].y),list(frame.energy_reduction_pct))

    def test_empty_and_missing_values_are_not_zero_bars(self):
        fig=charts.bar(self.frame.iloc[:0],'energy_kwh','Empty',self.data.policy_labels)
        self.assertEqual(len(fig.data),0)
        self.assertIn('No observations',fig.layout.annotations[0].text)
        missing=self.frame.copy();missing['p95_wait_s']=None
        self.assertEqual(len(charts.bar(missing,'p95_wait_s','Missing',self.data.policy_labels).data),0)

    def test_resource_skew_percent_axis(self):
        frame=self.data.skew(size=1000,curve=CURVES[0])
        fig=charts.bar(frame,'migrated_pct','Migration outcomes',self.data.policy_labels,x='category_label')
        self.assertIn('percent',fig.layout.yaxis.title.text)
        self.assertEqual(len(fig.data),2)

    def test_d5_decomposition_and_gap_figures(self):
        frame=self.data.d5('run_energy_breakdown',size=4000,curve=CURVES[0])
        fig=charts.stacked_energy(frame,self.data.policy_labels)
        self.assertEqual(len(fig.data),4)
        row=self.data.d5('pair_energy_gap',size=4000,curve=CURVES[0]).iloc[0]
        waterfall=charts.gap_waterfall(row)
        self.assertAlmostEqual(sum(waterfall.data[0].y),row.energy_change_kwh)
        self.assertIn('increase',waterfall.layout.yaxis.title.text)

    def test_recorded_timeline_keeps_two_supported_policies(self):
        frame=self.data.timelines(4000,CURVES[0])
        fig=charts.timeline(frame,'powered_hosts','Powered hosts',self.data.policy_labels)
        self.assertEqual(len(fig.data),2)
        self.assertEqual(len(fig.data[0].x),145)
        self.assertIn('offline',fig.layout.title.text)

    def test_pareto_scatter_constructs_without_aggregation(self):
        fig=charts.scatter(pareto_frontier(self.frame),'mean_wait_s',self.data.policy_labels)
        self.assertTrue(pio.to_json(fig))
        self.assertIn('minimize both',fig.layout.title.text)

    def test_coverage_counts(self):
        fig=charts.coverage(self.data.runs(),self.data.curve_labels)
        self.assertTrue(all(value==4 for row in fig.data[0].z for value in row))


if __name__=='__main__':unittest.main()
