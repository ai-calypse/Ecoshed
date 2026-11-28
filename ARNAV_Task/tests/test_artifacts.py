"""Artifact coverage, corruption detection, deterministic exports and preservation."""
import csv
import itertools
import json
from pathlib import Path
import tempfile
import unittest

from ARNAV_Task.analysis.artifacts import (ArtifactError, ResearchArtifacts, ROOT, POLICIES,
                                            SIZES, CURVES, read_json, output_path)
from ARNAV_Task.analysis.build import build
from ARNAV_Task.analysis.metrics import METRICS
from ARNAV_Task.analysis.validate_artifacts import make_report, validate, main
from ARNAV_Task.tests import change_json, research_copy, source_hashes


class ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.artifacts = ResearchArtifacts()

    def test_complete_matrix_and_original_metric_values(self):
        a = self.artifacts
        self.assertEqual(set(a.index), set(itertools.product(SIZES, CURVES, POLICIES)))
        raw = {tuple(r[k] for k in ("workload_groups", "power_curve", "policy")): r
               for r in read_json(ROOT / a.sources["raw_summaries"])}
        for row in a.filter_runs():
            key = row["workload_groups"], row["power_curve"], row["policy"]
            for name in METRICS:
                self.assertEqual(row.get(name), raw[key].get(name))
            self.assertTrue(row["policy_label"])
            self.assertTrue((ROOT / row["source_individual_summary"]).is_file())

    def test_filters_and_independent_return_values(self):
        rows = self.artifacts.filter_runs(policies=["lr_mmt"], sizes=[1000], curves=[CURVES[0]])
        self.assertEqual(len(rows), 1)
        rows[0]["config"]["sleep_watts"] = 999
        self.assertNotEqual(self.artifacts.filter_runs(policies=["lr_mmt"])[0]["config"]["sleep_watts"], 999)
        self.assertEqual(self.artifacts.filter_runs(policies=[]), [])
        with self.assertRaisesRegex(ArtifactError, "Unsupported policy"):
            self.artifacts.filter_runs(policies=["lr_mmt_same_job"])

    def test_historical_policies_never_appear_as_active_results(self):
        a = self.artifacts
        self.assertTrue(a.excluded_policies)
        self.assertEqual({r["policy"] for r in a.filter_runs()}, set(POLICIES))
        self.assertTrue(all(r["policy"] in POLICIES and r["baseline"] in POLICIES for r in a.comparisons()))

    def test_no_prepared_or_raw_csvs_required(self):
        with research_copy() as root:
            self.assertFalse((root / "RAW_Alibaba/prepared/hosts.csv").exists())
            self.assertTrue(validate(ResearchArtifacts(root))["passed"])

    def test_duplicate_active_run_rejected(self):
        with research_copy() as root:
            change_json(root, "BASELINE_Comparison/reports/summaries.json", lambda rows: rows.append(rows[0]))
            with self.assertRaisesRegex(ArtifactError, "duplicate"):
                ResearchArtifacts(root)

    def test_missing_active_run_rejected(self):
        with research_copy() as root:
            change_json(root, "BASELINE_Comparison/reports/summaries.json", lambda rows: rows.pop())
            with self.assertRaisesRegex(ArtifactError, "missing="):
                ResearchArtifacts(root)

    def test_duplicate_raw_run_rejected(self):
        with research_copy() as root:
            change_json(root, "RAW_Alibaba/reports/summaries.json", lambda rows: rows.append(rows[0]))
            with self.assertRaisesRegex(ArtifactError, "duplicate"):
                ResearchArtifacts(root)

    def test_original_collection_and_data_validation_metadata_checked(self):
        a = ResearchArtifacts()
        a.data_validation["passed"] = False
        self.assertFalse(validate(a)["passed"])
        a = ResearchArtifacts()
        a.raw_validation["runs"] -= 1
        self.assertFalse(validate(a)["passed"])

    def test_invalid_json_schema_has_a_useful_error(self):
        with research_copy() as root:
            (root / "RAW_Alibaba/prepared/manifest.json").write_text("[]")
            with self.assertRaisesRegex(ArtifactError, "Expected dict.*manifest.json"):
                ResearchArtifacts(root)

    def test_mismatch_against_original_raw_is_rejected(self):
        with research_copy() as root:
            change_json(root, "BASELINE_Comparison/reports/summaries.json",
                        lambda rows: rows[0].update(energy_kwh=0))
            with self.assertRaisesRegex(ArtifactError, "differs from original"):
                ResearchArtifacts(root)

    def test_individual_mismatch_and_missing_file_are_rejected(self):
        path = next(iter(self.artifacts.individual_paths.values()))
        with research_copy() as root:
            change_json(root, path, lambda row: row.update(migrations=999))
            with self.assertRaisesRegex(ArtifactError, "Individual raw summary differs"):
                ResearchArtifacts(root)
        with research_copy() as root:
            (root / path).unlink()
            with self.assertRaisesRegex(ArtifactError, "individual raw summaries.*missing="):
                ResearchArtifacts(root)

    def test_missing_artifact_reports_path(self):
        with research_copy() as root:
            (root / "BASELINE_Comparison/reports/proposal_pairs.csv").unlink()
            with self.assertRaisesRegex(ArtifactError, "proposal_pairs.csv"):
                ResearchArtifacts(root)

    def test_nonfinite_json_and_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "invalid.json"
            for text in ('{"energy": NaN}', '{"energy": 1, "energy": 2}'):
                p.write_text(text)
                with self.assertRaises(ArtifactError):
                    read_json(p)

    def test_scope_and_path_escape_cannot_be_enabled_by_config(self):
        with research_copy() as root:
            change_json(root, "ARNAV_Task/config/artifacts.json",
                        lambda cfg: cfg["policies"].update(same_job="Outside scope"))
            with self.assertRaisesRegex(ArtifactError, "active scope"):
                ResearchArtifacts(root)
        with research_copy() as root:
            change_json(root, "ARNAV_Task/config/artifacts.json",
                        lambda cfg: cfg["sources"].update(raw_summaries="../../outside.json"))
            with self.assertRaisesRegex(ArtifactError, "escapes repository"):
                ResearchArtifacts(root)

    def test_resource_skew_support_and_absence(self):
        a = self.artifacts
        self.assertEqual(len(a.resource_skew()), 48)
        self.assertEqual(a.resource_skew(policies=["first_fit"]), [])
        self.assertEqual(a.resource_skew(sizes=[250], categories=["cpu_heavy"]), [])
        self.assertTrue(all("energy_kwh" not in r for r in a.resource_skew()))
        self.assertEqual(len(a.resource_skew(policies=["lr_mmt"], sizes=[1000], curves=[CURVES[0]])), 3)

    def test_pairwise_comparison_coverage_and_baseline_filter(self):
        self.assertEqual(len(self.artifacts.comparisons()), 144)
        self.assertEqual(len(self.artifacts.comparisons(primary_only=True)), 9)
        self.assertEqual(len(self.artifacts.comparisons(baseline="first_fit")), 36)
        with self.assertRaisesRegex(ArtifactError, "baseline"):
            self.artifacts.comparisons(baseline="payback_cpu")

    def test_pairwise_csv_corruption_is_detected(self):
        with research_copy() as root:
            path = root / "BASELINE_Comparison/reports/all_pairwise_comparisons.csv"
            with path.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            rows[0]["energy_saving_pct"] = "99"
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
            result = validate(ResearchArtifacts(root))
            self.assertFalse(result["passed"])
            self.assertIn("policy pair reduction", str(result["errors"]))

    def test_primary_sign_corruption_is_detected(self):
        with research_copy() as root:
            path = root / "BASELINE_Comparison/reports/proposal_pairs.csv"
            with path.open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            rows[0]["proposed_energy_increase_pct"] = str(-float(rows[0]["proposed_energy_increase_pct"]))
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)
            self.assertFalse(validate(ResearchArtifacts(root))["passed"])

    def test_d5_missing_and_corrupt_outcomes_are_detected(self):
        with research_copy() as root:
            (root / "RUSHI_Task/reports/runs/hpe_dl360_gen9/workload_250/lr_mmt.json").unlink()
            with self.assertRaisesRegex(ArtifactError, "D5 recordings.*missing="):
                ResearchArtifacts(root)
        a = ResearchArtifacts()
        a.d5_tables["outcomes_by_task_type"][0]["p95_wait_s"] += 100
        self.assertFalse(validate(a)["passed"])

    def test_counts_and_energy_accounting_reject_consistently_copied_corruption(self):
        for field, bad in (("energy_j", 1), ("wh_per_completed_instance", 999),
                           ("rejected_instances", 1), ("completed_instances", 1),
                           ("overload_host_time_fraction", 2), ("peak_active_hosts", True)):
            with self.subTest(field=field):
                a = ResearchArtifacts()
                a.rows[0][field] = bad
                self.assertFalse(validate(a)["passed"])

    def test_deterministic_export_and_original_preservation(self):
        before = source_hashes()
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            a = build(output=left)
            build(output=right)
            files = sorted(Path(left).iterdir())
            self.assertEqual(len(files), 6)
            for path in files:
                self.assertEqual(path.read_bytes(), (Path(right) / path.name).read_bytes(), path.name)
            self.assertEqual(a["coverage"]["active_outcomes"], 36)
            self.assertEqual(a["findings"]["primary_energy_saving_cases"],
                             sum(r["energy_reduction_pct"] > 0 for r in a["primary_comparisons"]))
            self.assertEqual(set(a["scope"]["policies"]), set(POLICIES))
            self.assertFalse(a["d5"]["resource_skew_energy_available"])
        self.assertEqual(before, source_hashes())

    def test_output_guard_preserves_teammate_files(self):
        with self.assertRaisesRegex(ArtifactError, "Refusing output"):
            output_path(ROOT, ROOT / "RAW_Alibaba/reports/summaries.json")
        self.assertEqual(output_path(ROOT, ROOT / "ARNAV_Task/reports/test.json"),
                         ROOT / "ARNAV_Task/reports/test.json")

    def test_cli_failure_writes_useful_report_without_traceback(self):
        with research_copy() as root:
            (root / "RAW_Alibaba/reports/summaries.json").unlink()
            self.assertEqual(main(["--source-root", str(root)]), 1)
            report = read_json(root / "ARNAV_Task/reports/artifact_validation.json")
            self.assertFalse(report["numerical"]["passed"])
            self.assertIn("summaries.json", str(report["numerical"]["errors"]))


if __name__ == "__main__":
    unittest.main()
