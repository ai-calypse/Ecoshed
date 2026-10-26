"""Regression checks for safe validation against the committed handoff files."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


def fingerprints(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}


class ValidationTests(unittest.TestCase):
    def test_quick_check_does_not_modify_any_package_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'package';shutil.copytree(ROOT,root,ignore=shutil.ignore_patterns('__pycache__'))
            before=fingerprints(root)
            result=subprocess.run([sys.executable,str(root/'scripts/validate_data.py')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertEqual(fingerprints(root),before)

    def test_explicit_output_is_separate_from_full_source_evidence(self):
        before=fingerprints(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'quick-check.json'
            result=subprocess.run([sys.executable,str(ROOT/'scripts/validate_data.py'),'--output',str(output)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            record=json.loads(output.read_text())
            self.assertTrue(record['passed']);self.assertFalse(record['full_source_verification'])
        self.assertEqual(fingerprints(ROOT),before)

    def test_validator_recomputes_sampling_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'package';shutil.copytree(ROOT,root,ignore=shutil.ignore_patterns('__pycache__'))
            manifest=root/'manifest.json';value=json.loads(manifest.read_text())
            value['workloads'][0]['instance_time_bin_total_variation']=0.99
            manifest.write_text(json.dumps(value))
            result=subprocess.run([sys.executable,str(root/'scripts/validate_data.py')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('independently recomputed instance_time_bin_total_variation',result.stderr)


if __name__=='__main__':unittest.main()
