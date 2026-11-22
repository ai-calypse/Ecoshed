"""Tiny fabricated fixtures test parsers only; project experiments use raw rows."""
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

from RAW_Alibaba.extract import extract, FILES
from RAW_Alibaba.prepare import CONFIG, prepare, parse_attempt, select_hosts
from RAW_Alibaba.verify_data import verify_data
from RAW_Alibaba.data import iter_instances


def make_archive(path, contents):
    with tarfile.open(path, "w:gz") as tar:
        for name, content in contents.items():
            data = content.encode()
            entry = tarfile.TarInfo("fixture/" + name)
            entry.size = len(data)
            tar.addfile(entry, io.BytesIO(data))


class RawTests(unittest.TestCase):
    def fixture(self, root):
        contents = {name: "" for name in FILES}
        contents["server_event.csv"] = "0,1,add,,4,1,1\n0,2,add,,4,1.5,1\n"
        contents["batch_task.csv"] = (
            "0,20,10,100,2,Terminated,100,0.1\n"
            "5,18,20,200,1,Terminated,50,0.2\n"
            "0,20,30,300,2,Terminated,100,0.1\n")
        contents["batch_instance.csv"] = (
            "1,4,10,100,1,Terminated,1,1,,,,\n"
            "2,11,10,100,2,Terminated,1,1,,,,\n"
            "7,12,20,200,1,Terminated,1,1,,,,\n"
            "1,5,30,300,1,Terminated,1,1,,,,\n")
        archive = root / "fixture.tar.gz"
        make_archive(archive, contents)
        extract(archive, root / "raw")
        config = json.loads(CONFIG.read_text())
        config.update(window_end_s=20, host_count=2, workload_group_counts=[1, 2], arrival_bin_s=5)
        config_path = root / "fixture_config.json"
        config_path.write_text(json.dumps(config))
        return prepare(root / "raw", root / "prepared", config_path)

    def test_individual_raw_durations_and_original_multiplicity_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = self.fixture(root)
            self.assertEqual(manifest["completeness_audit"]["complete_groups"], 2)
            self.assertEqual(manifest["completeness_audit"]["fewer_observations_than_declared"], 1)
            tasks = list(iter_instances(2, root / "prepared"))
            self.assertEqual(len(tasks), 3)
            self.assertEqual(sorted(t.duration_s for t in tasks if t.task_group_id == "j10_t100"), [3, 9])
            self.assertEqual({t.cpu_request_cores for t in tasks if t.task_group_id == "j10_t100"}, {1})
            self.assertFalse(manifest["uses_yaksh_prepared_inputs"])
            self.assertTrue(verify_data(root / "raw", root / "prepared")["passed"])

    def test_modified_output_rejected_by_independent_verifier(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            with (root / "prepared/instances.csv").open("a") as f:
                f.write("changed\n")
            with self.assertRaisesRegex(ValueError, "Prepared output changed"):
                verify_data(root / "raw", root / "prepared")

    def test_retry_and_future_or_invalid_bounds_rejected(self):
        tasks = {("10", "100"): {"source_create_s": 0, "source_end_s": 20}}
        valid = ["1", "4", "10", "100", "1", "Terminated", "1", "1", "", "", "", ""]
        self.assertIsNone(parse_attempt(valid, tasks, {"1"})[1])
        retry = valid.copy();retry[6] = "2"
        self.assertEqual(parse_attempt(retry, tasks, {"1"})[1], "not_first_attempt")
        outside = valid.copy();outside[1] = "21"
        self.assertEqual(parse_attempt(outside, tasks, {"1"})[1], "invalid_or_outside_parent_interval")

    def test_host_selection_deterministic_and_capacity_classes_retained(self):
        source = {str(i): {"host_id": str(i), "cpu_capacity": 4 if i < 5 else 8,
                           "memory_capacity": 1, "source_row": i} for i in range(1, 10)}
        a = select_hosts(source, 3, 2026)
        b = select_hosts(dict(reversed(list(source.items()))), 3, 2026)
        self.assertEqual(a, b)
        self.assertEqual({h["cpu_capacity"] for h in a}, {4, 8})

    def test_archive_links_and_unexpected_members_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "link.tar.gz"
            with tarfile.open(archive, "w:gz") as tar:
                link = tarfile.TarInfo("fixture/batch_task.csv")
                link.type = tarfile.SYMTYPE
                link.linkname = "../../outside"
                tar.addfile(link)
            with self.assertRaisesRegex(ValueError, "Unexpected"):
                extract(archive, root / "raw")

    def test_fresh_runner_does_not_import_yaksh_loader(self):
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run([sys.executable, "-s", "-c",
            "import RAW_Alibaba.run,sys; assert not any(x.startswith('YAKSH_Task') for x in sys.modules)"],
            cwd=root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
