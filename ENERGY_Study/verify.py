"""Independently reconcile the frozen full study and published paired analytics."""
import argparse
import csv
import json
import math
from pathlib import Path
from dataclasses import asdict, replace

from ecosched import SimulationConfig
from .run import CONFIG, HERE, POLICIES, digest, plan, summarize_pairs


def verify(directory):
    directory = Path(directory)
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    frozen = json.loads((directory / "frozen_protocol.json").read_text(encoding="utf-8"))
    if frozen["config_sha256"] != digest(CONFIG) or frozen["protocol"] != raw:
        raise ValueError("Configuration differs from frozen protocol")
    for path, expected in frozen["source_sha256"].items():
        if digest(HERE.parent / path) != expected:
            raise ValueError(f"Source changed: {path}")
    rows = json.loads((directory / "summaries.json").read_text(encoding="utf-8"))
    fields = ("phase", "scenario", "seed", "mix", "lifetime", "curve")
    expected = {}
    for case in plan(raw):
        names = POLICIES + ("legacy_lr_mmt", "legacy_lr_mmt_memory") if case["phase"] == "development" else POLICIES
        for name in names:
            expected[tuple(case[k] for k in fields) + (name,)] = case
    found = {tuple(r[k] for k in fields) + (r["policy"],): r for r in rows}
    if len(found) != len(rows) or set(found) != set(expected):
        raise ValueError("Study matrix is incomplete, duplicated or contains extra runs")
    for key, row in found.items():
        case = expected[key]
        settings = SimulationConfig(**raw["base_simulation"])
        settings = replace(settings, **case["overrides"])
        mechanism = case["phase"] == "mechanism"
        if mechanism:
            settings = replace(settings, arrival_window_s=1000, control_interval_s=2000,
                               wake_latency_s=0, idle_timeout_s=0)
        if row["config"] != asdict(settings):
            raise ValueError("Resolved simulator settings differ from planned case")
        n = 4 if mechanism else raw["instance_count"]
        if row["completed_instances"] != n or row["completed_task_groups"] != n:
            raise ValueError("Completion counts differ from offered workload")
        if row["rejected_instances"] or row["unfinished_instances"] or not row["validation_passed"]:
            raise ValueError("An episode failed validation")
        if row["data_source"] != "synthetic":
            raise ValueError("Unexpected data source")
        components = sum(row[k] for k in ("sleep_energy_j", "waking_energy_j", "active_energy_j",
                                         "wake_transition_extra_energy_j", "migration_extra_energy_j"))
        if not math.isclose(components, row["energy_j"], abs_tol=1e-6, rel_tol=1e-10):
            raise ValueError("Energy breakdown does not reconcile")
        if not 0 <= row["mean_fragmentation_index"] <= 1:
            raise ValueError("Invalid fragmentation index")
    pairs, intervals = summarize_pairs(rows, raw)
    for filename, computed in (("paired_comparisons.csv", pairs), ("confidence_intervals.csv", intervals)):
        with (directory / filename).open(newline="", encoding="utf-8") as f:
            published = list(csv.DictReader(f))
        if published != [{k: str(v) if v is not None else "" for k, v in row.items()} for row in computed]:
            raise ValueError(f"Published analysis differs from recomputation: {filename}")
    result = {"passed": True, "verified_runs": len(rows), "verified_pairs": len(pairs),
              "verified_pointwise_intervals": len(intervals), "config_and_sources_match": True,
              "source_data": "synthetic", "production_claim_established": False}
    (directory / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    from RAW_Alibaba.run import verify_main
    verify_main()
