"""Phase 8 tests check packaging boundaries, not implementation-mirroring output."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ARNAV_Task.analysis.artifacts import ROOT
from ARNAV_Task.scripts.release_candidate import candidate_paths, scan, validate, check_manifest
from ARNAV_Task.scripts.restore_inputs import check_archive, restore
from ARNAV_Task.workload.source import WorkloadError


class ReleaseCandidateTests(unittest.TestCase):
    def test_candidate_excludes_private_runtime_and_agent_settings(self):
        paths=candidate_paths()
        self.assertTrue(paths)
        self.assertFalse(any('/.runtime/' in p or p.startswith('.agents/') for p in paths))
        self.assertIn('README.md',paths)
        self.assertIn('.github/workflows/validate-final-package.yml',paths)

    def test_candidate_security_scan(self):
        result=scan(candidate_paths());self.assertTrue(result['passed'],result['errors'])

    def test_current_manifest_detects_candidate_source_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'manifest.json'
            path.write_text(json.dumps({'source_and_output_sha256':{'ARNAV_Task/analysis/artifacts.py':'0'*64}}))
            errors=check_manifest(path)
            self.assertTrue(any('changed or missing' in e for e in errors))
            self.assertTrue(any('inventory' in e for e in errors))

    def test_unknown_archive_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'archive';path.write_text('unit fixture, not research evidence')
            with self.assertRaisesRegex(WorkloadError,'Unrecognized'):check_archive(path)

    def test_missing_archive_rejected(self):
        with self.assertRaisesRegex(WorkloadError,'Missing archive'):check_archive(ROOT/'ARNAV_Task/.runtime/not-present.tar.gz')

    def test_protected_restoration_output(self):
        with self.assertRaisesRegex(WorkloadError,'ignored'):restore('absent',ROOT/'RAW_Alibaba')

    def test_frozen_report_projection_changes_links_only(self):
        original=(ROOT/'ARNAV_Task/final/report/EcoSched_Final_Report.md').read_text()
        portable=(ROOT/'ARNAV_Task/final/report/EcoSched_Final_Report_Portable.md').read_text()
        self.assertEqual(original.replace('(ARNAV_Task/figures/','(../../figures/').replace('(ARNAV_Task/reports/','(../../reports/'),portable)

    def test_current_gate_keeps_historical_lineage_unresolved(self):
        r=validate();self.assertTrue(r['passed'],r['errors'])
        self.assertEqual(r['numerical']['active_outcomes'],36)
        self.assertEqual(r['historical_provenance']['unresolved_discrepancy_count'],3)
        self.assertFalse(r['historical_provenance']['strict_prerequisites_passed'])

    def test_optional_dependency_sets_and_workflow(self):
        import yaml
        workflow=yaml.safe_load((ROOT/'.github/workflows/validate-final-package.yml').read_text())
        self.assertIn('offline',workflow['jobs']);self.assertIn('optional-broker',workflow['jobs'])
        for name in ('runtime','publication','documents','dev'):
            self.assertTrue((ROOT/f'ARNAV_Task/requirements-{name}.txt').is_file())
