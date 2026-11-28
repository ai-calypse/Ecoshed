import csv
import json
from pathlib import Path
import tempfile
import unittest
from ARNAV_Task.analysis.artifacts import ResearchArtifacts, ROOT, POLICIES
from ARNAV_Task.publication.tables import academic_tables, write_table, latex_escape


class PublicationTableTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=ResearchArtifacts()
        read=lambda name:json.loads((ROOT/f'ARNAV_Task/reports/{name}.json').read_text())
        cls.tables={t.identifier:t for t in academic_tables(cls.a,read('phase3_verification'),read('phase4_verification'),read('phase5_verification'),read('artifact_validation'))}

    def test_requested_table_coverage(self):self.assertEqual(len(self.tables),22)

    def test_complete_energy_matrix(self):
        rows=self.tables['T07_energy'].rows;self.assertEqual(len(rows),36)
        self.assertEqual({r['policy'] for r in rows},set(POLICIES))

    def test_primary_comparisons_and_sign(self):
        rows=self.tables['T09_primary_comparisons'].rows;self.assertEqual(len(rows),9)
        self.assertEqual(sum(r['energy_reduction_pct']>0 for r in rows),4)

    def test_efficiency_denominator(self):
        for r in self.tables['T08_efficiency'].rows:self.assertAlmostEqual(r['wh_per_completed_instance'],1000*r['energy_kwh']/r['completed_instances'])

    def test_missing_skew_categories_explicit(self):
        rows=self.tables['T12_resource_skew'].rows
        self.assertEqual(len(rows),54)
        missing=[r for r in rows if r['observation_status']=='No observations'];self.assertEqual(len(missing),6)
        self.assertTrue(all(r['mean_wait_s'] is None and r['migrated_pct'] is None for r in missing))
        self.assertEqual({r['policy'] for r in rows},{'lr_mmt','lr_mmt_memory'})

    def test_fast_and_timed_modes_separate(self):
        rows=self.tables['T14_kafka_replays'].rows
        self.assertEqual(len(rows),4);self.assertEqual(sum(r['mode']=='Phase 4 fast' for r in rows),3)
        self.assertEqual(rows[-1]['mode'],'Phase 5 browser timed')

    def test_duplicate_counts_preserved(self):
        r=self.tables['T15_recovery'].rows[0]
        self.assertEqual(r['consumed_deliveries'],2*r['distinct_instances']);self.assertEqual(r['duplicate_deliveries'],r['distinct_instances'])

    def test_csv_roundtrip_preserves_precision(self):
        spec=self.tables['T08_efficiency']
        with tempfile.TemporaryDirectory() as tmp:
            paths=write_table(spec,Path(tmp))
            with paths[0].open() as f:rows=list(csv.DictReader(f))
            for actual,expected in zip(rows,spec.rows):self.assertEqual(float(actual['energy_kwh']),expected['energy_kwh'])
            self.assertIn('Wh/instance',paths[1].read_text());self.assertIn('longtable',paths[2].read_text())

    def test_latex_escaping(self):self.assertEqual(latex_escape('a_b & 10%'),r'a\_b \& 10\%')

    def test_deterministic_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths=write_table(self.tables['T09_primary_comparisons'],Path(tmp));before=[p.read_bytes() for p in paths]
            self.assertEqual(before,[p.read_bytes() for p in write_table(self.tables['T09_primary_comparisons'],Path(tmp))])

    def test_all_tables_have_source_and_caption(self):
        for t in self.tables.values():self.assertTrue(t.sources and t.caption and t.rows)

    def test_contributions_separate_owner_and_git_author(self):
        rows=self.tables['T18_contributions'].rows;self.assertEqual(len(rows),5)
        self.assertTrue(all('git_authors' in r for r in rows));self.assertEqual(rows[-1]['git_authors'],'Not committed')
