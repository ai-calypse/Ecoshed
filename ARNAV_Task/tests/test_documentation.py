"""Final package tests use actual frozen evidence, never benchmark simulations."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

import fitz
from docx import Document
from pptx import Presentation

from ARNAV_Task.documentation.evidence import Evidence, FINAL, ROOT, TEAM, safe_output
from ARNAV_Task.documentation.build_report import build as build_report, resolve
from ARNAV_Task.documentation.build_presentation import build as build_presentation
from ARNAV_Task.documentation.validate_final import document_check, write_manifest, validate_manifest
from ARNAV_Task.documentation.tables import report_table
from ARNAV_Task.analysis.provenance import sha256


class FinalDocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.e=Evidence()

    def test_claim_matrix(self):
        c=self.e.claims;self.assertEqual((c['runs'],c['pairs'],c['wins']),(36,9,4))
        self.assertEqual([c[f'instances_{s}'] for s in (250,1000,4000)],[16534,68457,378285])

    def test_energy_signs_preserve_negative_results(self):
        pairs=self.e.a.comparisons(primary_only=True)
        self.assertTrue(all(r['energy_reduction_pct']<0 for r in pairs if r['workload_groups']==4000))

    def test_d5_share_uses_per_curve_denominator(self):
        for r in self.e.a.d5_tables['pair_energy_gap']:
            if r['workload_groups']==4000:
                key={'hpe_dl360_gen9':'hpe','huawei_rh2288h_v3':'huawei','quanta_d51b_2u':'quanta'}[r['power_curve']]+'_on_share'
                self.assertEqual(self.e.claims[key],100*r['on_running_work_kwh']/r['energy_change_kwh'])
        self.assertNotEqual(self.e.claims['hpe_on_share'],self.e.claims['d5_pooled_share'])

    def test_active_policies_only(self):self.assertEqual({r['policy'] for r in self.e.a.rows},{'first_fit','best_fit','lr_mmt','lr_mmt_memory'})

    def test_report_source_and_abstract(self):
        pages=resolve(self.e,json.loads((FINAL/'report/source/report.json').read_text()))
        self.assertEqual(len(pages),28);self.assertTrue(200<=len(pages[1]['blocks'][1]['text'].split())<=250)

    def test_report_generation_readable_editable(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=build_report(tmp);self.assertEqual(result['page_count'],28)
            with fitz.open(Path(tmp)/result['pdf']) as pdf:self.assertEqual(len(pdf),28)
            self.assertTrue(Document(str(Path(tmp)/result['docx'])).paragraphs)

    def test_report_vectors_and_no_student_ids(self):
        with fitz.open(FINAL/'report/EcoSched_Final_Report.pdf') as d:
            self.assertLess(sum(len(p.get_images()) for p in d),5)
            text=' '.join(p.get_text() for p in d)
        self.assertNotIn('117382972',text)
        self.assertTrue(all(member in text for member in TEAM))

    def test_complete_experiment_tables(self):
        _,rows=report_table(self.e,'energy_all');self.assertEqual(len(rows),36)
        _,performance=report_table(self.e,'performance_all');self.assertEqual(len(performance),36)
        _,skew=report_table(self.e,'skew_all');self.assertEqual(len(skew),48)

    def test_verified_references(self):
        text=(FINAL/'report/references.bib').read_text()
        self.assertIn('10.1002/cpe.1867',text);self.assertIn('10.1145/2619239.2626334',text)
        self.assertIn('10.3390/app12199654',text);self.assertIn('Srikanth Kandula',text)

    def test_slide_source_main_appendix_and_notes(self):
        source=json.loads((FINAL/'presentation/source/slides.json').read_text())
        self.assertEqual(len(source['slides']),20);self.assertEqual(source['main_slides'],15)
        self.assertEqual(sum(s.get('appendix',False) for s in source['slides']),5)
        self.assertTrue(all(len(s['notes'])>120 for s in source['slides']))

    def test_editable_deck_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=build_presentation(tmp);d=Presentation(str(Path(tmp)/'EcoSched_Final_Presentation.pptx'))
            self.assertEqual(len(d.slides),20);self.assertIsNone(r['pdf_rendering'])
            self.assertEqual(sum(shape.has_chart for s in d.slides for shape in s.shapes),2)

    def test_final_cross_document_validation(self):
        r=document_check(self.e);self.assertTrue(r['passed'],r['errors'])

    def test_claim_ledger_corruption_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for folder in ('report','presentation','demo'):shutil.copytree(FINAL/folder,Path(tmp)/folder,ignore=shutil.ignore_patterns('previews'))
            path=Path(tmp)/'report/claims.json';d=json.loads(path.read_text());d['wins']['value']=9;path.write_text(json.dumps(d))
            self.assertFalse(document_check(self.e,Path(tmp))['passed'])

    def test_missing_research_data_fails_explicitly(self):
        from unittest.mock import patch
        with patch('ARNAV_Task.documentation.evidence.ResearchArtifacts',side_effect=ValueError('Missing authoritative artifact')):
            with self.assertRaisesRegex(ValueError,'authoritative'):Evidence()

    def test_protected_output_paths(self):
        with self.assertRaises(ValueError):safe_output(ROOT/'RAW_Alibaba/reports')
        with self.assertRaises(ValueError):build_report(ROOT/'ROHAN_Task')

    def test_source_preservation(self):
        paths=[ROOT/'RAW_Alibaba/reports/summaries.json',ROOT/'ARNAV_Task/reports/publication/figure_manifest.json']
        before=[sha256(p) for p in paths]
        with tempfile.TemporaryDirectory() as tmp:build_presentation(tmp)
        self.assertEqual(before,[sha256(p) for p in paths])

    def test_byte_identical_report_and_pptx(self):
        with tempfile.TemporaryDirectory() as tmp:
            one=Path(tmp)/'one';two=Path(tmp)/'two'
            build_report(one);build_report(two)
            for name in ('EcoSched_Final_Report.pdf','EcoSched_Final_Report.docx','EcoSched_Final_Report.md'):
                self.assertEqual(sha256(one/name),sha256(two/name),name)
            build_presentation(one)
            import time
            time.sleep(1.1)  # Catch timestamps in embedded chart workbooks, too.
            build_presentation(two)
            self.assertEqual(sha256(one/'EcoSched_Final_Presentation.pptx'),sha256(two/'EcoSched_Final_Presentation.pptx'))

    def test_manifest_detects_output_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)
            for folder in ('report','presentation','demo'):shutil.copytree(FINAL/folder,target/folder,ignore=shutil.ignore_patterns('previews'))
            write_manifest(self.e,target);self.assertEqual(validate_manifest(target),[])
            (target/'demo/demo_checklist.md').write_text('tampered')
            self.assertTrue(validate_manifest(target))

    def test_recorded_demo_fallback_is_explicit(self):
        text=(FINAL/'demo/demo_runbook.md').read_text()
        self.assertIn('recorded',text.lower());self.assertIn('72.698',text);self.assertIn('never fake',text.lower())

    def test_office_archives_have_no_broken_zip_members(self):
        for path in (FINAL/'report/EcoSched_Final_Report.docx',FINAL/'presentation/EcoSched_Final_Presentation.pptx'):
            with zipfile.ZipFile(path) as z:self.assertIsNone(z.testzip())
