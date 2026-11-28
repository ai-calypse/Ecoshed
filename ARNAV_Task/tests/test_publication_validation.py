import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from ARNAV_Task.analysis.artifacts import ROOT, ResearchArtifacts, ArtifactError
from ARNAV_Task.analysis.provenance import sha256
from ARNAV_Task.publication.validation import reconcile, validate_exports
from ARNAV_Task.publication.build import build, finding_text


class PublicationValidationTests(unittest.TestCase):
    def test_numerical_reconciliation(self):
        r=reconcile(ResearchArtifacts());self.assertTrue(r['passed'],r['errors'])
        self.assertEqual(r['active_outcomes'],36);self.assertEqual(r['primary_energy_savings_cases'],4)

    def test_bad_efficiency_detected(self):
        a=ResearchArtifacts();original=a.filter_runs()
        original[0]['wh_per_completed_instance']*=2
        with patch.object(a,'filter_runs',return_value=original):self.assertFalse(reconcile(a)['passed'])

    def test_duplicate_matrix_detected(self):
        a=ResearchArtifacts();rows=a.filter_runs();rows[0]=rows[1]
        with patch.object(a,'filter_runs',return_value=rows):self.assertFalse(reconcile(a)['passed'])

    def test_unsafe_output_rejected(self):
        with self.assertRaises(ArtifactError):build(destination=ROOT/'RAW_Alibaba/reports',sections=['tables'])

    def test_missing_manifests_fail(self):
        with tempfile.TemporaryDirectory() as tmp:self.assertFalse(validate_exports(ROOT,Path(tmp),ResearchArtifacts())['passed'])

    def test_offline_tables_and_architecture_without_runtime_inputs(self):
        # The build is forbidden from constructing workload sources or Kafka clients.
        with tempfile.TemporaryDirectory() as tmp, patch('ARNAV_Task.workload.source.WorkloadSource',side_effect=AssertionError('Raw input dependency')),patch('kafka.KafkaConsumer',side_effect=AssertionError('Broker dependency')):
            result=build(destination=tmp,sections=['tables','architecture'])
            self.assertTrue(result['passed'],result['errors'])
            manifest=json.loads((Path(tmp)/'reports/publication/figure_manifest.json').read_text())
            self.assertEqual(len(manifest['artifacts']),4)
            for r in manifest['artifacts']:
                self.assertTrue(r['source_sha256']);self.assertTrue(all(len(x['sha256'])==64 for x in r['outputs']))

    def test_source_preservation(self):
        paths=[ROOT/'ARNAV_Task/reports/experiment_summary.csv',ROOT/'BASELINE_Comparison/reports/summaries.json']
        before=[sha256(p) for p in paths]
        with tempfile.TemporaryDirectory() as tmp:build(destination=tmp,sections=['tables'])
        self.assertEqual(before,[sha256(p) for p in paths])

    def test_full_build_without_optional_history_or_live_input_access(self):
        from ARNAV_Task.publication import build as module
        # Force the optional history absent; keep all required result receipts real.
        original=Path.is_file
        history=ROOT/'ARNAV_Task/reports/publication/streaming_observations.json'
        def available(path):return False if path==history else original(path)
        with tempfile.TemporaryDirectory() as tmp,patch.object(Path,'is_file',available),\
             patch('ARNAV_Task.workload.source.WorkloadSource',side_effect=AssertionError('Raw input accessed')),\
             patch('kafka.KafkaProducer',side_effect=AssertionError('Broker accessed')),\
             patch('kafka.KafkaConsumer',side_effect=AssertionError('Broker accessed')):
            result=module.build(destination=tmp)
            self.assertTrue(result['passed'],result['errors'])
            manifest=json.loads((Path(tmp)/'reports/publication/figure_manifest.json').read_text())
            self.assertEqual(len(manifest['artifacts']),22)
            self.assertNotIn('S04_recorded_transport_history',{r['identifier'] for r in manifest['artifacts']})

    def test_corrupted_output_fails_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            build(destination=tmp,sections=['tables']);p=Path(tmp)/'reports/publication/tables/T07_energy.csv'
            p.write_text(p.read_text().replace('energy_kwh','wrong_unit'))
            self.assertFalse(validate_exports(ROOT,Path(tmp),ResearchArtifacts())['passed'])

    def test_findings_preserve_lineage_and_negative_results(self):
        read=lambda i:json.loads((ROOT/f'ARNAV_Task/reports/phase{i}_verification.json').read_text())
        text=finding_text(ResearchArtifacts(),read(3),read(4),read(5))
        self.assertIn('4/9',text);self.assertIn('10.96–14.56%',text);self.assertIn('unresolved',text)
        self.assertIn('not the final report',text)
