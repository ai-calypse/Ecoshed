"""Independent row-level validation against extracted raw records, not cleaned data."""
from collections import Counter
import csv
import json
from pathlib import Path

from .extract import FILES, digest

HERE = Path(__file__).resolve().parent


def verify_data(raw_directory=HERE / "raw", package=HERE / "prepared"):
    raw_directory, package = Path(raw_directory), Path(package)
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    for name in FILES:
        if digest(raw_directory / name) != manifest["archive"]["source_files"][name]["sha256"]:
            raise ValueError(f"Raw source changed: {name}")
    for name, entry in manifest["outputs"].items():
        if digest(package / name) != entry["sha256"]:
            raise ValueError(f"Prepared output changed: {name}")
    tasks = {}
    memberships = {}
    for size in manifest["config"]["workload_group_counts"]:
        with (package / f"workload_{size}.csv").open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if len(rows) != size or len({r["task_group_id"] for r in rows}) != size:
            raise ValueError("Workload size or uniqueness failed")
        memberships[size] = {r["task_group_id"] for r in rows}
        for row in rows:
            if row["task_group_id"] in tasks and tasks[row["task_group_id"]] != row:
                raise ValueError("Same group differs between workload samples")
            tasks[row["task_group_id"]] = row
    task_rows = {int(r["source_task_row"]): r for r in tasks.values()}
    verified_tasks = set()
    with (raw_directory / "batch_task.csv").open(newline="", encoding="utf-8") as f:
        for number, row in enumerate(csv.reader(f), 1):
            expected = task_rows.get(number)
            if expected is None:
                continue
            group = f"j{int(row[2])}_t{int(row[3])}"
            if (group != expected["task_group_id"] or row[5] != "Terminated"
                    or int(row[4]) != int(expected["instance_num"])
                    or int(row[0]) != int(expected["source_create_s"])
                    or int(row[1]) != int(expected["source_end_s"])
                    or float(row[6]) / manifest["config"]["cpu_request_divisor"] != float(expected["cpu_request_cores"])
                    or float(row[7]) != float(expected["memory_request_normalized"])):
                raise ValueError("Workload group differs from its exact raw task row")
            verified_tasks.add(group)
    if verified_tasks != set(tasks):
        raise ValueError("Some groups lack matching raw task rows")
    with (package / "hosts.csv").open(newline="", encoding="utf-8") as f:
        sampled_hosts = list(csv.DictReader(f))
    expected_hosts = {int(h["source_row"]): h for h in sampled_hosts}
    checked_hosts = set()
    known_hosts = set()
    with (raw_directory / "server_event.csv").open(newline="", encoding="utf-8") as f:
        for number, row in enumerate(csv.reader(f), 1):
            if row[2] == "add" and float(row[4]) > 0 and float(row[5]) > 0:
                known_hosts.add(str(int(row[1])))
            if number not in expected_hosts:
                continue
            h = expected_hosts[number]
            if (str(int(row[1])) != h["host_id"] or row[2] != "add"
                    or float(row[4]) != float(h["cpu_capacity"])
                    or float(row[5]) != float(h["memory_capacity"])):
                raise ValueError("Sampled host differs from raw capacity record")
            checked_hosts.add(h["host_id"])
    if len(checked_hosts) != manifest["config"]["host_count"]:
        raise ValueError("Host-pool count failed")
    with (package / "instances.csv").open(newline="", encoding="utf-8") as f:
        instances = list(csv.DictReader(f))
    reference_rows = {int(r["source_instance_row"]): r for r in instances}
    if len(reference_rows) != len(instances) or len({r["instance_id"] for r in instances}) != len(instances):
        raise ValueError("Duplicate selected raw instance rows or replay IDs")
    if instances != sorted(instances, key=lambda r: (int(r["arrival_time_s"]), r["task_group_id"], int(r["source_instance_row"]))):
        raise ValueError("Prepared arrivals are not sorted")
    selected_counts, all_valid_counts = Counter(), Counter()
    checked = 0
    with (raw_directory / "batch_instance.csv").open(newline="", encoding="utf-8") as f:
        for number, row in enumerate(csv.reader(f), 1):
            group = None
            valid = False
            if len(row) == 12:
                try:
                    group = f"j{int(row[2])}_t{int(row[3])}"
                    task = tasks.get(group)
                    valid = bool(task and row[5] == "Terminated" and int(row[6]) == 1
                                 and str(int(row[4])) in known_hosts
                                 and int(task["source_create_s"]) <= int(row[0]) < int(row[1]) <= int(task["source_end_s"]))
                except ValueError:
                    valid = False
            if valid:
                all_valid_counts[group] += 1
            reference = reference_rows.get(number)
            if reference is None:
                continue
            if not valid or group != reference["task_group_id"]:
                raise ValueError("Selected raw attempt has invalid parent/status/interval")
            task = tasks[group]
            if (int(reference["source_start_s"]) != int(row[0]) or int(reference["source_end_s"]) != int(row[1])
                    or float(reference["duration_s"]) != int(row[1]) - int(row[0])
                    or float(reference["cpu_request_cores"]) != float(task["cpu_request_cores"])
                    or float(reference["memory_request_normalized"]) != float(task["memory_request_normalized"])
                    or int(reference["arrival_time_s"]) != int(task["arrival_time_s"])):
                raise ValueError("Instance requests, release or actual duration changed")
            selected_counts[group] += 1
            checked += 1
    if checked != len(instances):
        raise ValueError("Not all selected instance records were found in the raw source")
    for group, task in tasks.items():
        if selected_counts[group] != int(task["instance_num"]) or all_valid_counts[group] != int(task["instance_num"]):
            raise ValueError("A group does not preserve complete original multiplicity")
    result = {"passed": True, "independent_raw_row_verification": True,
              "manifest_sha256": digest(package / "manifest.json"),
              "checked_groups": len(tasks), "checked_instances": checked, "checked_hosts": len(checked_hosts),
              "uses_yaksh_cleaned_inputs": False, "synthetic_workloads": False,
              "published_legacy_archive_hash_matches": manifest["archive"]["matches_published_legacy_archive"],
              "checks": ["raw/output hashes", "exact original task-row equality", "raw host capacities",
                         "unique observed raw attempt rows", "individual observed duration equality",
                         "no mean-runtime imputation", "complete original multiplicity", "sorted releases"]}
    (package.parent / "data_validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    return result


if __name__ == "__main__":
    verify_data()
