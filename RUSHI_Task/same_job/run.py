"""Run the same-job rule on Rohan's two LR-MMT policies, on the team's 9 cases
(DESIGN.md in this folder).

Four policies, each wrapped in a read-only observer (JobMixObserver) that counts how
many different jobs share each busy server at every controller tick:
    lr_mmt, lr_mmt_memory      Rohan's originals, re-run with the observer. Each run must
                               reproduce the team's committed result
                               (RAW_Alibaba/reports/summaries.json) in every field.
    lr_mmt_same_job            LR-MMT + the same-job rule
    lr_mmt_memory_same_job     memory-aware LR-MMT + the same-job rule

The team's prepared inputs only (RAW_Alibaba/prepared, checked by hash): the same 9 cases
as BASELINE_Comparison (3 sizes x 3 power curves), the same tasks, 64 hosts and
simulator settings as RAW_Alibaba.run. One fresh simulator per run, InstrumentedSimulator,
validate_run on every run. One compact JSON per run; finished runs are skipped, so an
interrupted run resumes where it stopped.

    python -m RUSHI_Task.same_job.run                         # all 36 runs
    python -m RUSHI_Task.same_job.run --policies lr_mmt_same_job
"""
import argparse
from collections import defaultdict
import csv
from itertools import product
import json
from pathlib import Path
import sys
import time

from ecosched import SimulationConfig, load_curve
from ENERGY_Study.instrumentation import InstrumentedSimulator
from RAW_Alibaba.data import iter_instances, load_hosts, verified_manifest
from RAW_Alibaba.extract import digest
from RAW_Alibaba.run import make_policy as make_original, source_hashes, validate_run
from RUSHI_Task.observer import outcomes_by_skew, time_series
from .policy import POLICIES, make_policy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PACKAGE = ROOT / "RAW_Alibaba" / "prepared"
OUTPUT = HERE / "reports" / "runs"
COMMITTED = ROOT / "RAW_Alibaba" / "reports" / "summaries.json"
SIZES = (250, 1000, 4000)
CURVES = ("hpe_dl360_gen9", "huawei_rh2288h_v3", "quanta_d51b_2u")
ORIGINALS = ("lr_mmt", "lr_mmt_memory")
NAMES = ORIGINALS + tuple(POLICIES)


class JobMixObserver:
    """Forwards every call unchanged; counts different jobs per busy server at each tick."""

    def __init__(self, policy):
        self.policy = policy
        self.name = policy.name
        self.host_ticks = self.distinct_jobs = self.single_job_hosts = 0

    def select_host(self, request, hosts, now):
        return self.policy.select_host(request, hosts, now)

    def on_tick(self, now, hosts, running):
        jobs = defaultdict(set)
        for task in running:
            jobs[task.host_id].add(task.request.task_group_id)
        for host_jobs in jobs.values():
            self.host_ticks += 1
            self.distinct_jobs += len(host_jobs)
            self.single_job_hosts += len(host_jobs) == 1
        return self.policy.on_tick(now, hosts, running)

    def report(self):
        ticks = self.host_ticks or 1
        return {"busy_server_ticks": self.host_ticks, "mean_jobs_per_busy_server": self.distinct_jobs / ticks,
                "single_job_server_share": self.single_job_hosts / ticks}


def jobs():
    """3 sizes x 3 curves x 4 policies = 36 runs."""
    return [(size, curve, name) for size, curve, name in product(SIZES, CURVES, NAMES)]


def code_hashes():
    hashes = source_hashes()   # simulator, Rohan's policies, power curves, replay code
    for path in (HERE / "policy.py", HERE / "run.py"):
        hashes[path.relative_to(ROOT).as_posix()] = digest(path)
    return hashes


def skews(size):
    """Task type of each group (balanced / memory-heavy / CPU-heavy), from RAW_Alibaba/prepare.py."""
    with (PACKAGE / f"workload_{size}.csv").open(newline="", encoding="utf-8") as f:
        return {r["task_group_id"]: r["resource_skew"] for r in csv.DictReader(f)}


def output_path(size, curve, name):
    return OUTPUT / curve / f"workload_{size}" / f"{name}.json"


def committed_results():
    return {(r["workload_groups"], r["power_curve"], r["policy"]): r
            for r in json.loads(COMMITTED.read_text(encoding="utf-8"))}


def run_one(size, curve_name, name, tasks, settings, committed):
    curve = load_curve(curve_name)
    policy = make_original(name, settings, curve) if name in ORIGINALS else make_policy(name, settings, curve)
    observer = JobMixObserver(policy)
    engine = InstrumentedSimulator(load_hosts(), settings, curve, observer)
    result = engine.run(iter(tasks))
    record = {"sample": "team", "workload_groups": size, "power_curve": curve_name, "policy": name,
              "summary": result, "validation": validate_run(engine, result, tasks, size),
              "job_mix": observer.report(),
              "outcomes_by_task_type": outcomes_by_skew(engine.records, engine.migration_log, skews(size)),
              "time_series": time_series(engine.samples),
              "controller_diagnostics": dict(policy.diagnostics),
              "input_manifest_sha256": digest(PACKAGE / "manifest.json"),
              "source_sha256": code_hashes(), "python_version": sys.version.split()[0]}
    if name in ORIGINALS:  # the observer must not change anything
        reference = committed[(size, curve_name, name)]
        record["differing_fields"] = sorted(k for k in result if result[k] != reference.get(k))
        record["reproduces_committed_result"] = not record["differing_fields"]
        if record["differing_fields"]:
            raise RuntimeError(f"Re-run differs from the team's committed result: {size} {curve_name} {name} "
                               f"{record['differing_fields']}")
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--policies", nargs="*", choices=NAMES)
    args = parser.parse_args(argv)
    manifest = verified_manifest(PACKAGE)   # the team's prepared inputs, checked by hash
    settings = SimulationConfig(**manifest["config"]["simulation"])
    committed = committed_results()
    hashes = code_hashes()
    plan = [j for j in jobs() if not args.policies or j[2] in args.policies]
    loaded, done = {}, 0
    for size, curve, name in plan:
        path = output_path(size, curve, name)
        if path.exists() and json.loads(path.read_text(encoding="utf-8"))["source_sha256"] == hashes:
            done += 1
            continue
        if size not in loaded:
            loaded.clear()  # keep one task list in memory at a time
            loaded[size] = list(iter_instances(size))
        start = time.monotonic()
        record = run_one(size, curve, name, loaded[size], settings, committed)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        done += 1
        print(f"[{done}/{len(plan)}] {size} {curve} {name}: {record['summary']['energy_kwh']:.4f} kWh, "
              f"{record['job_mix']['mean_jobs_per_busy_server']:.2f} jobs per busy server "
              f"({time.monotonic() - start:.0f}s)", flush=True)
    if code_hashes() != hashes:
        raise ValueError("Source changed during the experiment")
    print(f"All {len(plan)} runs present.", flush=True)


if __name__ == "__main__":
    main()
