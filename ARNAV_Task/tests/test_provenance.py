"""Lineage failures remain visible while consistent offline numbers stay usable."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from ARNAV_Task.analysis.artifacts import ResearchArtifacts, ROOT, read_json
from ARNAV_Task.analysis.provenance import assess, historical_versions, reconciliation_markdown, sha256
from ARNAV_Task.analysis.validate_artifacts import make_report, main
from ARNAV_Task.tests import research_copy, source_hashes


class ProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts = ResearchArtifacts()

    def test_three_discrepancies_are_calculated_from_original_references(self):
        a = self.artifacts
        p = assess(a)
        self.assertEqual(p["unresolved_discrepancy_count"], 3)
        by_id = {r["id"]: r for r in p["discrepancies"]}
        for row in by_id.values():
            self.assertEqual(row["current_sha256"], sha256(ROOT / row["target"]))
            self.assertTrue(row["references"])
            self.assertNotIn(row["current_sha256"], row["expected_sha256"])
            self.assertEqual(row["status"], "unresolved")
        self.assertEqual(by_id["prepared_manifest_reference"]["expected_sha256"],
                         sorted({r["manifest_sha256"] for r in a.rows}))
        raw_refs = [r for r in by_id["prepared_manifest_reference"]["references"]
                    if r["file"] == a.sources["raw_summaries"]]
        self.assertEqual(len(raw_refs), len(read_json(ROOT / a.sources["raw_summaries"])))
        self.assertEqual(by_id["raw_summaries_reference"]["expected_sha256"],
                         [a.baseline_validation["source_summary_sha256"]])
        self.assertEqual(by_id["archive_audit_reference"]["expected_sha256"],
                         [a.manifest["archive_audit_sha256"]])

    def test_git_history_search_is_explicit_and_does_not_recover_unknown_bytes(self):
        for row in assess(self.artifacts)["discrepancies"]:
            self.assertTrue(row["history"]["search_available"])
            self.assertFalse(row["earlier_matching_version_found"])
            self.assertGreaterEqual(row["history"]["versions_checked"], 1)

    def test_history_finds_an_exact_earlier_version_in_isolated_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.run(["git", "-C", directory, *args], check=True, capture_output=True)
            git("init", "-q")
            target = root / "manifest.json"
            target.write_bytes(b"original fixture metadata\n")
            expected = sha256(target)
            git("add", "manifest.json")
            git("-c", "user.name=D6 unit test", "-c", "user.email=d6@example.invalid", "commit", "-qm", "fixture original")
            target.write_bytes(b"changed fixture metadata\n")
            git("add", "manifest.json")
            git("-c", "user.name=D6 unit test", "-c", "user.email=d6@example.invalid", "commit", "-qm", "fixture changed")
            history = historical_versions(root, "manifest.json", [expected])
            self.assertEqual(history["versions_checked"], 2)
            self.assertEqual(len(history["matching_versions"]), 1)
            self.assertEqual(history["matching_versions"][0]["sha256"], expected)
            self.assertNotEqual(sha256(target), expected)

    def test_no_git_checkout_or_git_binary_is_reported(self):
        with research_copy() as root:
            p = assess(ResearchArtifacts(root))
            self.assertTrue(all(not r["history"]["search_available"] for r in p["discrepancies"]))
        with patch("ARNAV_Task.analysis.provenance.subprocess.run", side_effect=FileNotFoundError):
            self.assertFalse(historical_versions(ROOT, "README.md", ["unknown"])["search_available"])

    def test_numerics_and_strict_reproducibility_are_separate(self):
        normal = make_report(self.artifacts)
        strict = make_report(self.artifacts, strict=True)
        self.assertTrue(normal["passed"])
        self.assertTrue(strict["numerical"]["passed"])
        self.assertFalse(strict["passed"])
        self.assertTrue(normal["provenance"]["source_code_fingerprints"]["consistent"])
        self.assertFalse(normal["provenance"]["end_to_end_reproducibility"]["verified"])
        self.assertFalse(normal["provenance"]["prepared_inputs"]["all_present"])

    def test_strict_cli_fails_and_keeps_machine_readable_report(self):
        before = source_hashes()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "strict.json"
            self.assertEqual(main(["--strict", "--output", str(output)]), 1)
            result = read_json(output)
            self.assertTrue(result["numerical"]["passed"])
            self.assertFalse(result["passed"])
            self.assertTrue((output.parent / "provenance_reconciliation.md").exists())
        self.assertEqual(before, source_hashes())

    def test_source_changes_do_not_get_misreported_as_input_lineage_only(self):
        with research_copy() as root:
            source = root / "ecosched/engine.py"
            source.write_bytes(source.read_bytes() + b"\n# isolated mutation fixture\n")
            p = assess(ResearchArtifacts(root), check_history=False)
            self.assertFalse(p["source_code_fingerprints"]["consistent"])
            self.assertTrue(any(r["path"] == "ecosched/engine.py" and not r["hash_matches"]
                                for r in p["source_code_fingerprints"]["files"]))

    def test_prepared_file_presence_does_not_imply_hash_validation(self):
        with research_copy() as root:
            a = ResearchArtifacts(root)
            for name in a.manifest["outputs"]:
                (root / "RAW_Alibaba/prepared" / name).write_text("unit fixture, not workload data\n")
            p = assess(a, check_history=False)
            self.assertTrue(p["prepared_inputs"]["all_present"])
            self.assertFalse(p["prepared_inputs"]["all_hashes_verified"])

    def test_archive_corroboration_never_becomes_a_publisher_checksum_match(self):
        p = assess(self.artifacts, check_history=False)
        archive = p["archive_identity"]
        self.assertFalse(archive["recorded_publisher_compressed_checksum_match"])
        self.assertFalse(archive["recorded_archive"]["present"])
        self.assertTrue(archive["recorded_gzip_and_member_integrity"])
        self.assertIn("not a publisher", archive["interpretation"])
        self.assertFalse(p["end_to_end_reproducibility"]["verified"])

    def test_reconciliation_document_is_deterministic_and_explains_limits(self):
        p = assess(self.artifacts)
        text = reconciliation_markdown(p)
        self.assertEqual(text, reconciliation_markdown(p))
        self.assertIn("No exact matching earlier version", text)
        self.assertIn("not verified", text)
        self.assertIn("Never replace historical hashes", text)
        for row in p["discrepancies"]:
            self.assertIn(row["current_sha256"], text)
            for expected in row["expected_sha256"]:
                self.assertIn(expected, text)


if __name__ == "__main__":
    unittest.main()
