"""Load only independently prepared raw-archive rows; never fall back to a handoff."""
import csv
from dataclasses import dataclass
import json
from pathlib import Path

from ecosched.models import HostSpec
from .extract import digest

HERE = Path(__file__).resolve().parent
PACKAGE = HERE / "prepared"


@dataclass(frozen=True)
class TraceInstance:
    instance_id: str
    task_group_id: str
    job_id: str
    arrival_time_s: int
    cpu_request_cores: float
    memory_request_normalized: float
    duration_s: float


def verified_manifest(package=PACKAGE):
    package = Path(package)
    manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    if manifest["data_source"] != "fresh_user_archive_alibaba_v2017" or manifest["uses_yaksh_prepared_inputs"] or manifest["uses_synthetic_workloads"]:
        raise ValueError("Fresh raw-archive inputs are required")
    if digest(HERE / "prepare.py") != manifest["preparation_source_sha256"]:
        raise ValueError("Preparation code differs from recorded build")
    if digest(HERE / "config.json") != manifest["config_sha256"]:
        raise ValueError("Raw experiment config differs from recorded build")
    for name, entry in manifest["outputs"].items():
        if digest(package / name) != entry["sha256"]:
            raise ValueError(f"Prepared raw input changed: {name}")
    return manifest


def load_hosts(package=PACKAGE):
    with (Path(package) / "hosts.csv").open(newline="", encoding="utf-8") as f:
        return [HostSpec(r["host_id"], float(r["cpu_capacity"]), float(r["memory_capacity"])) for r in csv.DictReader(f)]


def iter_instances(size, package=PACKAGE):
    package = Path(package)
    with (package / f"workload_{size}.csv").open(newline="", encoding="utf-8") as f:
        groups = {r["task_group_id"] for r in csv.DictReader(f)}
    with (package / "instances.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["task_group_id"] in groups:
                yield TraceInstance(row["instance_id"], row["task_group_id"], row["job_id"], int(row["arrival_time_s"]),
                                    float(row["cpu_request_cores"]), float(row["memory_request_normalized"]), float(row["duration_s"]))
