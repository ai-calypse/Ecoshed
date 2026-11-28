"""Read-only adapter for the frozen Alibaba research artifacts, without CSV inputs."""
from copy import deepcopy
import csv
import itertools
import json
from pathlib import Path

from .metrics import energy_reduction, difference

ROOT = Path(__file__).resolve().parents[2]
POLICIES = ("first_fit", "best_fit", "lr_mmt", "lr_mmt_memory")
SIZES = (250, 1000, 4000)
CURVES = ("hpe_dl360_gen9", "huawei_rh2288h_v3", "quanta_d51b_2u")
PRIMARY = ("lr_mmt", "lr_mmt_memory")
SKEWS = ("balanced", "memory_heavy", "cpu_heavy")
D5_TABLES = (
    "outcomes_by_task_type", "workload_mix", "pair_energy_gap", "run_energy_breakdown",
    "tradeoffs", "controller_diagnostics", "servers_running_work", "placement_decisions",
    "placement_load_bands", "placement_score_arithmetic", "curve_band_watts",
)


class ArtifactError(ValueError):
    """An artifact is missing, malformed or inconsistent with its research source."""


def output_path(root, path):
    """Allow D6 reports/runtime or destinations outside the source checkout."""
    root, path = Path(root).resolve(), Path(path).resolve()
    if path.is_relative_to(root) and not any(path.is_relative_to(root / "ARNAV_Task" / name)
                                             for name in ("reports", ".runtime")):
        raise ArtifactError(f"Refusing output outside ARNAV_Task/reports or .runtime in source checkout: {path}")
    return path


def read_json(path):
    try:
        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    raise ValueError(f"duplicate JSON key {key!r}")
                result[key] = value
            return result
        def invalid(value):
            raise ValueError(f"nonfinite JSON number {value}")
        return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs,
                          parse_constant=invalid)
    except (OSError, ValueError) as exc:
        raise ArtifactError(f"Cannot read JSON artifact {path}: {exc}") from exc


def read_csv(path):
    text_fields = {"policy", "baseline", "power_curve", "task_type", "data_source",
                   "paired_cpu_baseline", "band", "cheapest_band"}
    try:
        with Path(path).open(newline="", encoding="utf-8") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ValueError("missing or duplicate CSV headers")
            rows = []
            for line, row in enumerate(reader, 2):
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"wrong column count at line {line}")
                normalized = {}
                for key, value in row.items():
                    if key in text_fields:
                        normalized[key] = value
                    elif value == "":
                        normalized[key] = None
                    elif key == "proposed_energy_win":
                        if value not in ("True", "False"):
                            raise ValueError(f"invalid boolean at line {line}: {key}")
                        normalized[key] = value == "True"
                    else:
                        try:
                            normalized[key] = int(value)
                        except ValueError:
                            normalized[key] = float(value)
                rows.append(normalized)
            return rows
    except (OSError, ValueError) as exc:
        raise ArtifactError(f"Cannot read CSV artifact {path}: {exc}") from exc


def run_key(row):
    try:
        return row["workload_groups"], row["power_curve"], row["policy"]
    except (KeyError, TypeError) as exc:
        raise ArtifactError(f"Run is missing workload_groups, power_curve or policy: {row!r}") from exc


def index_rows(rows, label, fields=("workload_groups", "power_curve", "policy")):
    result = {}
    if not isinstance(rows, (list, tuple)):
        raise ArtifactError(f"{label}: expected a list of rows")
    for row in rows:
        try:
            key = tuple(row[field] for field in fields)
            if key in result:
                raise ArtifactError(f"{label}: duplicate combination {key}")
            result[key] = row
        except (KeyError, TypeError) as exc:
            raise ArtifactError(f"{label}: invalid key columns {fields} in {row!r}") from exc
    return result


def require_keys(index, expected, label):
    if set(index) != set(expected):
        missing = sorted(set(expected) - set(index), key=str)
        extra = sorted(set(index) - set(expected), key=str)
        raise ArtifactError(f"{label}: incomplete experiment coverage; missing={missing}, unexpected={extra}")


class ResearchArtifacts:
    """Numerically cross-checked sources. Lineage status is assessed separately.

    No RAW_Alibaba loader is imported: the original loader requires ignored prepared
    CSVs, whereas offline packaging must use the committed result evidence alone.
    """

    def __init__(self, root=ROOT, config=None):
        self.root = Path(root).resolve()
        config = Path(config) if config else self.root / "ARNAV_Task/config/artifacts.json"
        if not config.is_absolute():
            config = self.root / config
        self.config_path = config.resolve()
        self.config = read_json(self.config_path)
        if (not isinstance(self.config, dict)
                or tuple(self.config.get("policies", {})) != POLICIES
                or tuple(self.config.get("workload_sizes", [])) != SIZES
                or tuple(self.config.get("power_curves", {})) != CURVES):
            raise ArtifactError("D6 config must preserve the four-policy, three-size, three-curve active scope")
        self.sources = self.config.get("sources")
        required_sources = {"raw_summaries", "raw_runs", "raw_comparison", "active_summaries", "primary_pairs",
                            "policy_pairs", "manifest", "raw_config", "policy_config", "power_curves", "data_validation",
                            "raw_validation", "baseline_validation", "archive_audit", "archive_corroboration", "d5_reports"}
        if not isinstance(self.sources, dict) or not required_sources <= self.sources.keys():
            raise ArtifactError(f"D6 config is missing required artifact source paths: {sorted(required_sources)}")
        self.source_paths = set()
        self._track(self.config_path)
        self.manifest = self.json("manifest")
        self.raw_config = self.json("raw_config")
        self.policy_config = self.json("policy_config")
        self.curve_data = self.json("power_curves")
        self.data_validation = self.json("data_validation")
        self.raw_validation = self.json("raw_validation")
        self.baseline_validation = self.json("baseline_validation")
        self.archive_audit = self.json("archive_audit")
        self.archive_corroboration = self.json("archive_corroboration")
        raw = self.json("raw_summaries")
        baseline = self.json("active_summaries")
        # Check duplicate identities even outside the selected subset, but never expose
        # historical policies as active outcomes or final-package comparisons.
        self.raw_keys = set(index_rows(raw, self.sources["raw_summaries"]))
        self.raw_manifest_references = tuple({"field": f"[{i}].manifest_sha256",
                                              "expected_sha256": row["manifest_sha256"]}
                                             for i, row in enumerate(raw))
        index_rows(baseline, self.sources["active_summaries"])
        self.excluded_policies = sorted({r["policy"] for r in raw + baseline} - set(POLICIES))
        self.raw_rows = tuple(r for r in raw if r["policy"] in POLICIES)
        self.rows = tuple(r for r in baseline if r["policy"] in POLICIES)
        self.index = index_rows(self.rows, "active summaries")
        raw_index = index_rows(self.raw_rows, "selected raw summaries")
        expected = set(itertools.product(SIZES, CURVES, POLICIES))
        require_keys(self.index, expected, "active summaries")
        require_keys(raw_index, expected, "selected raw summaries")
        for key, row in self.index.items():
            if row != raw_index[key]:
                raise ArtifactError(f"Active summary differs from original raw summary: {key}")
        self.individual_paths = {}
        individual = []
        for path in sorted(self.path("raw_runs").rglob("summary.json")):
            row = read_json(path)
            if not isinstance(row, dict):
                raise ArtifactError(f"Expected an object in individual raw summary: {path}")
            if row.get("policy") in POLICIES:
                self._track(path)
                key = run_key(row)
                if key in self.individual_paths:
                    raise ArtifactError(f"Duplicate individual raw summary: {key}")
                self.individual_paths[key] = path.relative_to(self.root).as_posix()
                individual.append(row)
        individual_index = index_rows(individual, "individual raw summaries")
        require_keys(individual_index, expected, "individual raw summaries")
        for key, row in self.index.items():
            if row != individual_index[key]:
                raise ArtifactError(f"Individual raw summary differs from aggregate: {key}")
        self.rows = tuple(self.index[key] for key in self.ordered_keys())
        self.raw_comparison = [r for r in self.csv("raw_comparison") if r["policy"] in POLICIES]
        self.primary_pairs = self.csv("primary_pairs")
        self.policy_pairs = [r for r in self.csv("policy_pairs")
                             if r["policy"] in POLICIES and r["baseline"] in POLICIES]
        d5 = self.path("d5_reports")
        self.d5_validation = self.json_path(d5 / "validation.json")
        self.d5_tables = {name: self.csv_path(d5 / f"{name}.csv") for name in D5_TABLES}
        self.d5_recordings = {}
        for path in sorted((d5 / "runs").rglob("*.json")):
            row = self.json_path(path)
            if row.get("policy") not in PRIMARY:
                continue
            key = run_key(row)
            if key in self.d5_recordings:
                raise ArtifactError(f"Duplicate D5 recording: {key}")
            self.d5_recordings[key] = row
        require_keys(self.d5_recordings, set(itertools.product(SIZES, CURVES, PRIMARY)), "D5 recordings")

    def _track(self, path):
        try:
            self.source_paths.add(path.resolve().relative_to(self.root).as_posix())
        except ValueError as exc:
            raise ArtifactError(f"Artifact path must remain inside source root: {path}") from exc

    def path(self, name):
        if not isinstance(self.sources[name], str):
            raise ArtifactError(f"Expected a relative file/directory path for {name}")
        path = (self.root / self.sources[name]).resolve()
        if not path.is_relative_to(self.root):
            raise ArtifactError(f"Artifact path escapes repository: {name}")
        return path

    def json_path(self, path, expected_type=dict):
        self._track(path)
        result = read_json(path)
        if not isinstance(result, expected_type):
            raise ArtifactError(f"Expected {expected_type.__name__} in JSON artifact {path}")
        return result

    def csv_path(self, path):
        self._track(path)
        return read_csv(path)

    def json(self, name):
        return self.json_path(self.path(name), list if name in ("raw_summaries", "active_summaries") else dict)

    def csv(self, name):
        return self.csv_path(self.path(name))

    def ordered_keys(self):
        return [(size, curve, policy) for size in SIZES for curve in CURVES for policy in POLICIES]

    def filter_runs(self, *, policies=None, sizes=None, curves=None):
        """Return independent copies, with labels and source links; no data imputation."""
        filters = []
        for values, allowed, label in ((policies, POLICIES, "policy"), (sizes, SIZES, "workload size"),
                                       (curves, CURVES, "power curve")):
            values = set(allowed if values is None else values)
            if not values <= set(allowed):
                raise ArtifactError(f"Unsupported {label} filter: {sorted(values - set(allowed), key=str)}")
            filters.append(values)
        result = []
        for row in self.rows:
            size, curve, policy = run_key(row)
            if size in filters[1] and curve in filters[2] and policy in filters[0]:
                item = deepcopy(row)
                item.update(policy_label=self.config["policies"][policy],
                            power_curve_label=self.config["power_curves"][curve],
                            source_summary=self.sources["active_summaries"],
                            source_raw_summary=self.sources["raw_summaries"],
                            source_individual_summary=self.individual_paths[run_key(row)])
                result.append(item)
        return result

    def resource_skew(self, *, policies=None, sizes=None, curves=None, categories=None):
        """Only D5-supported observations; no energy or fabricated absent categories."""
        allowed_keys = {run_key(r) for r in self.filter_runs(policies=policies, sizes=sizes, curves=curves)}
        categories = set(SKEWS if categories is None else categories)
        if not categories <= set(SKEWS):
            raise ArtifactError(f"Unsupported resource-skew categories: {sorted(categories - set(SKEWS))}")
        return [deepcopy(r) for r in self.d5_tables["outcomes_by_task_type"]
                if run_key(r) in allowed_keys and r["task_type"] in categories]

    def comparisons(self, *, baseline=None, primary_only=False):
        if baseline is not None and baseline not in POLICIES:
            raise ArtifactError(f"Unsupported baseline: {baseline}")
        result = []
        for size in SIZES:
            for curve in CURVES:
                pairs = [(PRIMARY[1], PRIMARY[0])] if primary_only else itertools.product(POLICIES, repeat=2)
                for policy, reference in pairs:
                    if baseline is not None and reference != baseline:
                        continue
                    a, b = self.index[(size, curve, policy)], self.index[(size, curve, reference)]
                    result.append({
                        "workload_groups": size, "power_curve": curve, "policy": policy,
                        "policy_label": self.config["policies"][policy], "baseline": reference,
                        "baseline_label": self.config["policies"][reference],
                        "energy_kwh": a["energy_kwh"], "baseline_energy_kwh": b["energy_kwh"],
                        "energy_reduction_pct": energy_reduction(a, b),
                        "mean_wait_delta_s": difference(a, b, "mean_wait_s"),
                        "p95_wait_delta_s": difference(a, b, "p95_wait_s"),
                        "migrations": a.get("migrations"),
                        "pressure_delta_percentage_points": (
                            100 * difference(a, b, "overload_host_time_fraction")
                            if a.get("overload_host_time_fraction") is not None
                            and b.get("overload_host_time_fraction") is not None else None),
                        "source_candidate": self.individual_paths[run_key(a)],
                        "source_baseline": self.individual_paths[run_key(b)],
                        "source_comparison": self.sources["primary_pairs" if primary_only else "policy_pairs"],
                    })
        return result

    def provenance(self, *, check_history=True):
        """Explicitly expose unresolved lineage without preventing offline inspection."""
        from .provenance import assess
        return assess(self, check_history=check_history)
