"""Deterministic D6 exports from committed research results; no simulations."""
import argparse
import csv
from pathlib import Path

from .artifacts import ArtifactError, ResearchArtifacts, ROOT, PRIMARY, CURVES, SIZES, output_path
from .metrics import METRICS, definitions
from .provenance import reconciliation_markdown, sha256
from .validate_artifacts import make_report, write_json


def write_csv(path, rows):
    if not rows:
        raise ArtifactError(f"Cannot export empty research table: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build(root=ROOT, output=None, config=None, *, check_history=True):
    a = ResearchArtifacts(root, config)
    report = make_report(a, check_history=check_history)
    if not report["numerical"]["passed"]:
        raise ArtifactError(f"Numerical artifact validation failed: {report['numerical']['errors']}")
    output = output_path(a.root, output or a.root / "ARNAV_Task/reports")
    # Include implementation fingerprints as well as input artifacts in the
    # preservation guard. Nothing in a teammate package is an output destination.
    protected = sorted(a.source_paths | {r["path"] for r in report["provenance"]["source_code_fingerprints"]["files"]})
    before = {p: sha256(a.root / p) for p in protected if (a.root / p).is_file()}
    output.mkdir(parents=True, exist_ok=True)
    status = report["provenance"]["status"]
    common = {"numerical_consistency": "verified", "provenance_status": status,
              "metric_definitions_source": "research_summary.json#metric_definitions"}
    experiments = []
    for row in a.filter_runs():
        experiments.append({
            "workload_groups": row["workload_groups"], "power_curve": row["power_curve"],
            "power_curve_label": row["power_curve_label"], "policy": row["policy"], "policy_label": row["policy_label"],
            **{name: row.get(name) for name in METRICS},
            "source_summary": row["source_summary"], "source_raw_summary": row["source_raw_summary"],
            "source_individual_summary": row["source_individual_summary"],
            "recorded_manifest_sha256": row["manifest_sha256"], **common,
        })
    primary = [{**r, **common} for r in a.comparisons(primary_only=True)]
    comparisons = [{**r, **common} for r in a.comparisons()]
    write_csv(output / "experiment_summary.csv", experiments)
    write_csv(output / "primary_comparisons.csv", primary)
    write_csv(output / "policy_comparisons.csv", comparisons)
    # D5 remains clearly attributed. Its original energy_change_pct columns use
    # increase semantics; the public D6 comparisons above always use reduction.
    d5 = {name: {"source": f"{a.sources['d5_reports']}/{name}.csv", "rows": rows,
                 "energy_sign": "energy_change_pct is energy INCREASE; use primary_comparisons for reduction"}
          for name, rows in a.d5_tables.items()}
    summary = {
        "schema_version": 1,
        "study": "Existing independently prepared Alibaba v2017 study; D6 offline packaging only",
        "scope": report["active_scope"],
        "schedulers": a.config["policies"], "power_curves": a.config["power_curves"],
        "coverage": {"active_outcomes": len(experiments), "primary_comparisons": len(primary),
                     "ordered_policy_comparisons_including_self": len(comparisons),
                     "per_curve_outcomes": report["numerical"]["per_curve_outcomes"]},
        "workloads": a.manifest["workloads"],
        "methodology": {"raw_config_reference": a.sources["raw_config"],
                        "simulation_settings": a.raw_config["simulation"],
                        "sampling_seed": a.raw_config["seed"],
                        "runtime_model": a.raw_config["runtime_model"],
                        "arrival_model": a.raw_config["arrival_model"],
                        "policy_config_reference": a.sources["policy_config"],
                        "recorded_input_manifest": a.sources["manifest"],
                        "power_model_source": a.sources["power_curves"],
                        "historical_extra_policies_in_raw_config_are_excluded": True},
        "metric_definitions": definitions(),
        "provenance": report["provenance"], "numerical_validation": report["numerical"],
        "source_artifacts_sha256": report["artifact_sha256"],
        "experiments": experiments, "primary_comparisons": primary,
        "policy_comparisons": comparisons,
        "d5": {"tables": d5, "resource_skew_outcomes": a.resource_skew(),
               "sampled_recording_sources": [f"{a.sources['d5_reports']}/runs/{curve}/workload_{size}/{policy}.json"
                                             for size in SIZES for curve in CURVES for policy in PRIMARY],
               "resource_skew_energy_available": False,
               "sampled_series_are_offline": True},
        "findings": {"primary_energy_saving_cases": sum(r["energy_reduction_pct"] > 0 for r in primary),
                     "primary_additional_energy_cases": sum(r["energy_reduction_pct"] < 0 for r in primary),
                     "primary_energy_ties": sum(r["energy_reduction_pct"] == 0 for r in primary),
                     "completed_instance_replays": report["numerical"]["completed_instance_replays"]},
        "limitations": a.manifest["limitations"] + [
            "Deterministic overlapping samples and power-curve cases are not independent statistical replications.",
            "Requested-resource pressure is a modeled SLA proxy, not measured SLA violations.",
            "SPECpower is a whole-server surrogate; migration and sleep/wake parameters are modeling assumptions.",
            "P95 waiting times are not averaged. Energy is not allocated to resource-skew categories.",
            "Original stale provenance references remain unresolved; numerical consistency does not verify end-to-end reproduction.",
        ],
        "new_simulations": 0, "raw_archive_processing_in_this_phase": False,
    }
    write_json(output / "research_summary.json", summary)
    write_json(output / "artifact_validation.json", report)
    (output / "provenance_reconciliation.md").write_text(reconciliation_markdown(report["provenance"]),
                                                       encoding="utf-8", newline="\n")
    after = {p: sha256(a.root / p) for p in before}
    if before != after:
        raise ArtifactError("Original research inputs or source files changed during export generation")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output", type=Path, help="D6 report directory, or a directory outside the source checkout")
    args = parser.parse_args(argv)
    try:
        result = build(args.source_root, args.output, args.config)
    except (ArtifactError, KeyError, TypeError, ValueError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(f"Exported {result['coverage']['active_outcomes']} runs, "
          f"{result['coverage']['primary_comparisons']} primary comparisons and "
          f"{result['coverage']['ordered_policy_comparisons_including_self']} ordered policy comparisons. "
          f"Provenance: {result['provenance']['status']}; new simulations: 0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
