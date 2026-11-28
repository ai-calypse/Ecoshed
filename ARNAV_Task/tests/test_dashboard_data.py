"""Dashboard views use actual evidence; small Pareto mappings are unit fixtures only."""
from pathlib import Path
import os
import tempfile
import unittest

import pandas as pd

from ARNAV_Task.analysis.artifacts import ROOT, POLICIES, CURVES
from ARNAV_Task.dashboard.data_service import (DashboardData, DashboardDataError, evidence_signature,
                                                get_data, pareto_frontier)
from ARNAV_Task.tests import research_copy


class DashboardDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = DashboardData()

    def test_actual_kpis_and_validation(self):
        k = self.data.kpis()
        self.assertEqual((k['runs'], k['policies'], k['sizes'], k['curves']), (36, 4, 3, 3))
        self.assertEqual(k['completed'], 5559312)
        self.assertEqual((k['wins'], k['losses'], k['primary_pairs']), (4, 5, 9))
        self.assertEqual((k['rejected'], k['unfinished']), (0, 0))
        self.assertTrue(self.data.validation['numerical']['passed'])
        self.assertEqual(self.data.provenance['status'], 'unresolved')

    def test_scheduler_size_and_curve_filters(self):
        for kwargs, count in (({'policies':['lr_mmt']},9),({'sizes':[1000]},12),({'curves':[CURVES[1]]},12),
                              ({'policies':['lr_mmt'], 'sizes':[4000], 'curves':[CURVES[2]]},1)):
            self.assertEqual(len(self.data.runs(**kwargs)),count)
        self.assertTrue(self.data.runs(policies=[]).empty)
        with self.assertRaises(ValueError):self.data.runs(policies=['same_job'])
        self.assertEqual(set(self.data.runs().policy),set(POLICIES))

    def test_baseline_metrics_reuse_phase1_results(self):
        frame=self.data.relative('energy_kwh','lr_mmt',size=4000,curve=CURVES[0],policies=['lr_mmt_memory'])
        original=self.data.artifacts.comparisons(primary_only=True)
        expected=next(r for r in original if r['workload_groups']==4000 and r['power_curve']==CURVES[0])
        self.assertAlmostEqual(frame.iloc[0].energy_reduction_pct,expected['energy_reduction_pct'])
        self.assertLess(frame.iloc[0].energy_reduction_pct,0)
        self.assertEqual(frame.iloc[0].baseline_energy_kwh,expected['baseline_energy_kwh'])
        with self.assertRaises(DashboardDataError):self.data.relative('energy_kwh','payback',size=4000,curve=CURVES[0])

    def test_metric_ranking_and_non_energy_deltas(self):
        frame=self.data.relative('p95_wait_s','first_fit',size=4000,curve=CURVES[0])
        reference=self.data.artifacts.index[(4000,CURVES[0],'first_fit')]['p95_wait_s']
        for row in frame.itertuples():
            self.assertEqual(row.metric_delta,row.p95_wait_s-reference)
        self.assertEqual(frame['rank'].min(),1)

    def test_missing_optional_observation_is_not_zero(self):
        data=DashboardData()
        data.artifacts.index[(250,CURVES[0],'lr_mmt_memory')]['p95_wait_s']=None
        result=data.relative('p95_wait_s','lr_mmt',size=250,curve=CURVES[0],policies=['lr_mmt_memory'])
        self.assertTrue(pd.isna(result.iloc[0].metric_delta))
        self.assertTrue(pd.isna(result.iloc[0]['rank']))

    def test_resource_skew_support(self):
        self.assertTrue(self.data.skew(size=250,curve=CURVES[0],policies=['first_fit']).empty)
        self.assertTrue(self.data.skew(size=250,curve=CURVES[0],categories=['cpu_heavy']).empty)
        self.assertNotIn('energy_kwh',self.data.skew(size=1000,curve=CURVES[0]))
        with self.assertRaises(ValueError):self.data.skew(size=1000,curve=CURVES[0],categories=['invented'])
        composition=self.data.composition(250)
        self.assertEqual(composition.loc[composition.task_type=='cpu_heavy','instances'].iloc[0],0)

    def test_recordings_are_supported_primary_cases_with_sources(self):
        frame=self.data.timelines(4000,CURVES[0])
        self.assertEqual(frame.groupby('policy').size().tolist(),[145,145])
        self.assertTrue(frame.source_recording.str.startswith('RUSHI_Task/reports/runs/').all())
        with self.assertRaises(DashboardDataError):self.data.timelines(250,CURVES[0],['first_fit'])

    def test_missing_and_malformed_evidence_never_falls_back(self):
        with research_copy() as root:
            p=root/'RAW_Alibaba/reports/summaries.json'
            p.unlink()
            with self.assertRaisesRegex(DashboardDataError,'summaries.json'):DashboardData(root)
            p.write_text('{malformed')
            with self.assertRaisesRegex(DashboardDataError,'JSON'):DashboardData(root)

    def test_numerically_inconsistent_csv_is_rejected(self):
        with research_copy() as root:
            p=root/'BASELINE_Comparison/reports/proposal_pairs.csv'
            p.write_text(p.read_text().replace('-0.3886662661091833','99'))
            with self.assertRaisesRegex(DashboardDataError,'primary reduction'):DashboardData(root)

    def test_paths_work_outside_repository_cwd(self):
        old=os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                self.assertEqual(len(DashboardData().runs()),36)
            finally:os.chdir(old)

    def test_cache_invalidation_and_refresh(self):
        first=get_data(refresh=True)
        self.assertIs(first,get_data())
        self.assertIsNot(first,get_data(refresh=True))
        with research_copy() as root:
            before=evidence_signature(root)
            p=root/'RAW_Alibaba/reports/comparison.csv'
            p.write_text(p.read_text()+'\n')
            self.assertNotEqual(before,evidence_signature(root))

    def test_asset_allowlist_and_missing_assets(self):
        self.assertIn('<svg',self.data.asset('energy_gap_breakdown.svg'))
        with self.assertRaises(DashboardDataError):self.data.asset('../same_job/REPORT.md')
        with research_copy() as root:
            with self.assertRaisesRegex(DashboardDataError,'unavailable'):DashboardData(root).asset('REPORT.md')

    def test_downloads_preserve_current_provenance(self):
        report,reconciliation=self.data.downloads()
        self.assertIn('"verified": false',report)
        self.assertIn('unresolved',reconciliation)


class ParetoTests(unittest.TestCase):
    def frame(self):
        return pd.DataFrame({'workload_groups':[250]*5,'power_curve':[CURVES[0]]*5,
                             'energy_kwh':[1,2,3,2,None],'mean_wait_s':[4,2,3,2,1]})

    def test_minimization_dominance_ties_and_missing(self):
        rows=pareto_frontier(self.frame())
        self.assertEqual(rows.pareto_efficient.iloc[:4].tolist(),[True,True,False,True])
        self.assertTrue(pd.isna(rows.pareto_efficient.iloc[4]))

    def test_mixed_conditions_rejected(self):
        for field,value in [('workload_groups',1000),('power_curve',CURVES[1])]:
            frame=self.frame();frame.loc[0,field]=value
            with self.assertRaisesRegex(DashboardDataError,'one workload'):pareto_frontier(frame)

    def test_empty_selection(self):
        self.assertTrue(pareto_frontier(self.frame().iloc[:0]).empty)
