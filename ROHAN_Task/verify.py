"""Collect and verify a complete 3-size x 3-curve x 4-policy result matrix."""
import argparse
from dataclasses import asdict, replace
import itertools
import json
from pathlib import Path

from ecosched.__main__ import fingerprint, load_experiment, write_csv
from .run import ROOT, DEFAULT_CONFIG, comparison_rows


def verify_matrix(source, output):
    raw = json.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    expected = set(itertools.product(raw["sizes"], raw["curves"], raw["policies"]))
    found = {}
    for path in Path(source).rglob("summary.json"):
        result = json.loads(path.read_text(encoding="utf-8"))
        key = result["workload_groups"], result["power_curve"], result["policy"]
        if key in found:
            raise ValueError(f"Duplicate result {key}")
        found[key] = result
    if set(found) != expected:
        raise ValueError(f"Matrix mismatch; missing={expected-set(found)}, extra={set(found)-expected}")
    expected_counts = {250: 40381, 1000: 160813, 4000: 638647}
    for key, result in found.items():
        if not result["validation"]["passed"]:
            raise ValueError(f"Run validation failed {key}")
        if result["completed_instances"] != expected_counts[key[0]] or result["unfinished_instances"] or result["rejected_instances"]:
            raise ValueError(f"Outcome conservation failed {key}")
        _, _, original, inputs = load_experiment(ROOT / f"YAKSH_Task/config/experiment_{key[0]}.json")
        if result["inputs"] != inputs:
            raise ValueError(f"Input/engine provenance mismatch {key}")
        if result["config"] != asdict(replace(original, **raw["simulation_overrides"])):
            raise ValueError(f"Common simulator settings changed {key}")
        if key[2].startswith("lr_mmt") and result["policy_config"] != raw["policy"]:
            raise ValueError(f"Common policy settings changed {key}")
        if result["runner_config_sha256"] != fingerprint(DEFAULT_CONFIG):
            raise ValueError(f"Runner config changed {key}")
        for name, digest in result["rohan_sources_sha256"].items():
            if fingerprint(Path(__file__).parent / name) != digest:
                raise ValueError(f"Policy implementation changed {key}: {name}")
        if abs(sum(result["host_energy_j"].values()) - result["energy_j"]) > 1e-5:
            raise ValueError(f"Energy reconciliation failed {key}")
        if key[2].startswith("lr_mmt"):
            kinds = result["policy_diagnostics"]
            if kinds.get("overload_migrations", 0) + kinds.get("consolidation_migrations", 0) != result["migrations"]:
                raise ValueError(f"Migration reasons failed to reconcile {key}")
    results = [found[k] for k in sorted(found)]
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "comparison.csv", comparison_rows(results))
    (out / "summaries.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    validation = {"passed": True, "runs": len(results), "matrix": raw,
                  "checks": ["complete unique matrix", "instance/group conservation",
                             "input and Brave source hashes", "Rohan source hashes",
                             "identical resolved simulation and LR/MMT settings",
                             "per-host/total energy reconciliation", "migration reason reconciliation"],
                  "total_completed_instance_replays": sum(r["completed_instances"] for r in results)}
    (out / "validation.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in validation.items() if k != "matrix"}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).with_name("results"))
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("reports"))
    args = parser.parse_args()
    verify_matrix(args.source, args.output)
