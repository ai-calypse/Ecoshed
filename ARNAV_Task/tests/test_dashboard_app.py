"""Native Streamlit navigation and interactions, without starting any simulator."""
from pathlib import Path
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from ARNAV_Task.analysis.artifacts import ROOT, CURVES
from ARNAV_Task.dashboard.constants import PAGES, COMPARE_METRICS
from ARNAV_Task.dashboard.data_service import DashboardDataError

APP=ROOT/'ARNAV_Task/dashboard/app.py'


class DashboardAppTests(unittest.TestCase):
    def app(self,page=None):
        app=AppTest.from_file(str(APP),default_timeout=30).run()
        if page and page!='overview':app.switch_page(f'views/{page}.py').run()
        return app

    def assert_healthy(self,app):
        self.assertEqual([e.message for e in app.exception],[])

    def test_every_registered_page_renders_with_provenance_warning(self):
        app=self.app()
        for name,label in PAGES:
            with self.subTest(page=name):
                if name!='overview':app.switch_page(f'views/{name}.py').run()
                self.assert_healthy(app)
                self.assertTrue(any('Provenance unresolved' in w.value for w in app.warning))
                self.assertTrue(any(x.value==label for x in app.header))
                if name!='live_replay':self.assertGreaterEqual(len(app.get('plotly_chart')),1)

    def test_overview_kpis_are_visible(self):
        app=self.app();self.assert_healthy(app)
        values={m.label:m.value for m in app.metric}
        self.assertEqual(values['Active outcomes'],'36')
        self.assertEqual(values['Completed instance replays'],'5,559,312')
        self.assertEqual(values['Numerical validation'],'PASS')

    def test_comparison_filters_and_all_metrics(self):
        app=self.app('scheduler_comparison')
        app.selectbox(key='comparison_size').set_value(1000)
        app.selectbox(key='comparison_curve').set_value(CURVES[1])
        app.selectbox(key='comparison_baseline').set_value('first_fit')
        app.multiselect(key='comparison_policies').set_value(['lr_mmt','lr_mmt_memory']).run()
        for metric in COMPARE_METRICS:
            with self.subTest(metric=metric):
                app.selectbox(key='comparison_metric').set_value(metric).run();self.assert_healthy(app)
                self.assertEqual(len(app.dataframe[0].value),2)
        self.assertTrue(len(app.get('download_button')))

    def test_empty_policy_selection_is_a_clear_empty_state(self):
        for page,key in [('scheduler_comparison','comparison'),('energy_analysis','energy'),('performance_analysis','performance')]:
            with self.subTest(page=page):
                app=self.app(page)
                app.multiselect(key=f'{key}_policies').set_value([]).run()
                self.assert_healthy(app)

    def test_skew_absent_category_and_policy_restrictions(self):
        app=self.app('resource_skew')
        self.assertEqual(set(app.multiselect(key='skew_policies').options),
                         {'CPU-oriented LR-MMT','LR-MMT + CPU/Memory-Aware Placement'})
        app.multiselect(key='skew_categories').set_value(['cpu_heavy']).run()
        self.assert_healthy(app)
        self.assertTrue(any('No observations: CPU-heavy' in item.value for item in app.info))
        app.selectbox(key='skew_size').set_value(1000).run();self.assert_healthy(app)
        self.assertFalse(any('No observations: CPU-heavy' in item.value for item in app.info))

    def test_performance_objectives_and_stranded_resources(self):
        app=self.app('performance_analysis')
        for y in ['mean_wait_s','overload_host_time_fraction','migrations','mean_active_hosts']:
            app.selectbox(key='pareto_objective').set_value(y).run();self.assert_healthy(app)
        app.selectbox(key='performance_metric').set_value('memory_stranded_by_cpu_unit_seconds').run()
        self.assert_healthy(app)

    def test_research_recordings_and_original_figures(self):
        app=self.app('research_findings')
        for field in ['powered_hosts','hosts_running_work','mean_cpu_of_hosts_running_work','mean_memory_of_hosts_running_work']:
            app.selectbox(key='findings_timeline_metric').set_value(field).run();self.assert_healthy(app)
        for figure in ['energy_gap_breakdown.svg','servers_over_time.svg','who_picks_the_emptier_server.svg','wait_by_task_type.svg']:
            app.selectbox(key='d5_figure').set_value(figure).run();self.assert_healthy(app)

    def test_reproducibility_downloads_and_strict_warning(self):
        app=self.app('reproducibility');self.assert_healthy(app)
        self.assertTrue(any('Strict validation exits unsuccessfully' in w.value for w in app.warning))
        labels=[e.label for e in app.get('download_button')]
        self.assertIn('Download artifact validation JSON',labels)
        self.assertIn('Download provenance reconciliation',labels)

    def test_explicit_refresh_preserves_valid_page(self):
        app=self.app();app.button(key='refresh_artifacts').click().run();self.assert_healthy(app)

    def test_missing_evidence_shows_error_and_no_research_charts(self):
        with patch('ARNAV_Task.dashboard.data_service.get_data',side_effect=DashboardDataError('Missing summaries.json')):
            app=self.app()
        self.assert_healthy(app)
        self.assertIn('Missing summaries.json',app.error[0].value)
        self.assertEqual(len(app.get('plotly_chart')),0)


if __name__=='__main__':unittest.main()
