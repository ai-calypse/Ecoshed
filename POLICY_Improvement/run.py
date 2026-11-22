"""Fixed six-policy ablation on the unchanged verified raw Alibaba samples."""
import argparse
import json
from pathlib import Path
import time
from ecosched import SimulationConfig, load_curve
from ENERGY_Study.instrumentation import InstrumentedSimulator
from RAW_Alibaba.data import verified_manifest, load_hosts, iter_instances, PACKAGE, HERE as RAW
from RAW_Alibaba.extract import digest
from RAW_Alibaba.run import source_hashes as original_hashes, validate_run, make_policy
from .policies import ImprovedPolicy

HERE = Path(__file__).resolve().parent


def source_hashes():
    return {**original_hashes(), **{p.relative_to(HERE.parent).as_posix(): digest(p)
            for p in sorted(HERE.glob("*.py"))}, "POLICY_Improvement/config.json": digest(HERE / "config.json")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--curve", required=True)
    args = parser.parse_args()
    protocol = json.loads((HERE / "config.json").read_text())
    manifest = verified_manifest()
    config = manifest["config"]
    assert args.curve in config["power_curves"]
    manifest_sha = digest(PACKAGE / "manifest.json")
    audit = json.loads((RAW / "data_validation.json").read_text())
    assert audit["passed"] and audit["manifest_sha256"] == manifest_sha
    frozen = source_hashes()
    baseline = json.loads((RAW / "reports/summaries.json").read_text())
    assert all(r["manifest_sha256"] == manifest_sha for r in baseline)
    settings = SimulationConfig(**config["simulation"])
    pool = load_hosts()
    for size in config["workload_group_counts"]:
        tasks = list(iter_instances(size))
        for name in protocol["policies"]:
            start = time.monotonic()
            curve = load_curve(args.curve)
            if name.startswith("energy_first"):
                policy = make_policy(name, settings, curve)
            else:
                policy = ImprovedPolicy(settings, curve, compact="compact" in name,
                    gate="payback" in name, memory=name != "payback_cpu",
                    safety_factor=protocol["payback_safety_factor"],
                    minimum_residence_s=protocol["minimum_residence_s"])
            engine = InstrumentedSimulator(pool, settings, curve, policy)
            result = engine.run(iter(tasks))
            result.update(workload_groups=size, validation=validate_run(engine, result, tasks, size),
                manifest_sha256=manifest_sha, source_sha256=frozen, synthetic_workload=False,
                uses_yaksh_prepared_inputs=False, data_source="fresh_user_archive_alibaba_v2017",
                evaluation_role=protocol["evaluation_role"],
                archive_sha256=manifest["archive"]["archive_sha256"],
                published_legacy_archive_hash_matches=manifest["archive"]["matches_published_legacy_archive"])
            directory = HERE / "reports" / "runs" / args.curve / str(size) / name
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
            if hasattr(policy, "gate_log"):
                (directory / "gate.json").write_text(json.dumps(policy.gate_log, indent=2)+"\n")
            print(f"{args.curve} / {size} / {name}: {result['energy_kwh']:.6f} kWh, "
                  f"{result['migrations']} migrations ({time.monotonic()-start:.1f}s)", flush=True)
    assert source_hashes() == frozen and digest(PACKAGE / "manifest.json") == manifest_sha


if __name__ == "__main__":
    main()
