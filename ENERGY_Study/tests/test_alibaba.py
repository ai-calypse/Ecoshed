import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ENERGY_Study import alibaba
from ENERGY_Study.run import main, historical_synthetic_main


class AlibabaOnlyTests(unittest.TestCase):
    def test_default_runner_delegates_to_alibaba(self):
        with patch("RAW_Alibaba.run.main", return_value="alibaba") as entry:
            self.assertEqual(main(["--sizes", "250"]), "alibaba")
            entry.assert_called_once_with(["--sizes", "250"])

    def test_synthetic_experiment_entry_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "disabled"):
            historical_synthetic_main([])

    def test_real_trace_inputs_count_and_provenance(self):
        hosts, workload, config, provenance, count = alibaba.inputs_for(250)
        self.assertEqual(count, 40381)
        self.assertEqual(len(hosts), 64)
        self.assertEqual(workload.name, "workload_250.csv")
        self.assertEqual(config.arrival_window_s, 43200)
        self.assertIn("data_manifest_sha256", provenance)

    def test_manifest_rejects_modified_files_and_path_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            package = Path(temporary)
            source = package / "source.csv"
            source.write_bytes(b"trace-row\n")
            manifest = {"official_sources": {"repository": "https://github.com/alibaba/clusterdata"},
                        "outputs": {"source.csv": {"sha256": hashlib.sha256(source.read_bytes()).hexdigest()}}}
            (package / "manifest.json").write_text(json.dumps(manifest))
            alibaba.manifest_check(package, ["source.csv"])
            source.write_bytes(b"generated-row\n")
            with self.assertRaisesRegex(ValueError, "altered"):
                alibaba.manifest_check(package, ["source.csv"])
            with self.assertRaisesRegex(ValueError, "escapes"):
                alibaba.manifest_check(package, ["../outside.csv"])

    def test_output_verifier_rejects_synthetic_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "summary.json").write_text(json.dumps({"workload_groups": 250,
                "power_curve": "hpe_dl360_gen9", "policy": "energy_first_cpu",
                "synthetic_workload": True, "data_source": "synthetic"}))
            with self.assertRaisesRegex(ValueError, "Non-Alibaba"):
                alibaba.verify(root, root, require_full=False)


if __name__ == "__main__":
    unittest.main()
