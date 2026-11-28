"""Cached read-only views over Phase 1; no alternate processing or synthetic fallback."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pandas as pd
import streamlit as st

from ARNAV_Task.analysis.artifacts import ResearchArtifacts, ArtifactError, ROOT, POLICIES, PRIMARY, SIZES, CURVES
from ARNAV_Task.analysis.metrics import METRICS, difference
from ARNAV_Task.analysis.provenance import reconciliation_markdown
from ARNAV_Task.analysis.validate_artifacts import make_report
from .constants import SKEW_LABELS

ASSETS = ("REPORT.md", "energy_gap_breakdown.svg", "servers_over_time.svg",
          "who_picks_the_emptier_server.svg", "wait_by_task_type.svg")


class DashboardDataError(ValueError):
    """Research evidence cannot safely be displayed."""


class DashboardData:
    def __init__(self, root=ROOT):
        try:
            self.artifacts = ResearchArtifacts(root)
            self.validation = make_report(self.artifacts)
            if not self.validation["numerical"]["passed"]:
                raise ArtifactError(str(self.validation["numerical"]["errors"]))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise DashboardDataError(f"Research artifacts could not be validated: {exc}") from exc
        self.root = self.artifacts.root
        self.policy_labels = self.artifacts.config["policies"]
        self.curve_labels = self.artifacts.config["power_curves"]

    @property
    def provenance(self):
        return self.validation["provenance"]

    def runs(self, *, policies=None, sizes=None, curves=None):
        rows = self.artifacts.filter_runs(policies=policies, sizes=sizes, curves=curves)
        # An empty selection retains its schema; missing numeric observations stay NaN.
        columns = list(self.artifacts.filter_runs()[0])
        return pd.DataFrame(rows, columns=columns)

    def comparisons(self, baseline="lr_mmt", *, sizes=None, curves=None, policies=None, primary=False):
        rows = self.artifacts.comparisons(baseline=None if primary else baseline, primary_only=primary)
        allowed = self.runs(policies=policies, sizes=sizes, curves=curves)
        keys = set(zip(allowed.workload_groups, allowed.power_curve, allowed.policy))
        return pd.DataFrame([r for r in rows if (r["workload_groups"], r["power_curve"], r["policy"]) in keys],
                            columns=list(rows[0]))

    def relative(self, metric, baseline, *, size, curve, policies=None):
        """Use Phase 1 comparisons/differences and preserve the reference even if hidden."""
        if metric not in METRICS:
            raise DashboardDataError(f"Unsupported comparison metric: {metric}")
        if baseline not in POLICIES:
            raise DashboardDataError(f"Unsupported baseline: {baseline}")
        frame = self.runs(policies=policies, sizes=[size], curves=[curve])
        reference = self.artifacts.index[(size, curve, baseline)]
        frame["baseline"] = baseline
        frame["baseline_energy_kwh"] = reference.get("energy_kwh")
        frame["baseline_value"] = reference.get(metric)
        original = self.artifacts.filter_runs(policies=policies, sizes=[size], curves=[curve])
        frame["metric_delta"] = [difference(row, reference, metric) for row in original]
        energy = self.comparisons(baseline, sizes=[size], curves=[curve])
        reductions = energy.set_index("policy")["energy_reduction_pct"].to_dict()
        frame["energy_reduction_pct"] = frame.policy.map(reductions)
        frame["rank"] = frame[metric].rank(method="min", ascending=metric != "completed_instances", na_option="keep")
        return frame

    def d5(self, name, *, size=None, curve=None, policies=None):
        if name not in self.artifacts.d5_tables:
            raise DashboardDataError(f"Unknown D5 table: {name}")
        rows = deepcopy(self.artifacts.d5_tables[name])
        frame = pd.DataFrame(rows)
        if size is not None and "workload_groups" in frame:
            if size not in SIZES:
                raise DashboardDataError(f"Unsupported workload size: {size}")
            frame = frame[frame.workload_groups == size]
        if curve is not None and "power_curve" in frame:
            if curve not in CURVES:
                raise DashboardDataError(f"Unsupported power curve: {curve}")
            frame = frame[frame.power_curve == curve]
        if policies is not None and "policy" in frame:
            if not set(policies) <= set(POLICIES):
                raise DashboardDataError("Unsupported scheduler in D5 selection")
            frame = frame[frame.policy.isin(policies)]
        if "policy" in frame:
            frame["policy_label"] = frame.policy.map(self.policy_labels)
        frame["source_table"] = f"{self.artifacts.sources['d5_reports']}/{name}.csv"
        return frame.reset_index(drop=True)

    def skew(self, *, size, curve, policies=PRIMARY, categories=None):
        columns = list(self.artifacts.d5_tables["outcomes_by_task_type"][0])
        rows = self.artifacts.resource_skew(policies=policies, sizes=[size], curves=[curve], categories=categories)
        frame = pd.DataFrame(rows, columns=columns)
        frame["policy_label"] = frame.policy.map(self.policy_labels)
        frame["category_label"] = frame.task_type.map(SKEW_LABELS)
        frame["source_table"] = f"{self.artifacts.sources['d5_reports']}/outcomes_by_task_type.csv"
        return frame

    def composition(self, size):
        row = self.d5("workload_mix", size=size)
        if len(row) != 1:
            raise DashboardDataError("Missing workload composition")
        return pd.DataFrame([{"task_type": key, "category_label": label,
                              "instances": row.iloc[0][f"{key}_instances"],
                              "share_pct": row.iloc[0][f"{key}_pct"],
                              "source_table": row.iloc[0].source_table}
                             for key, label in SKEW_LABELS.items()])

    def timelines(self, size, curve, policies=PRIMARY):
        if size not in SIZES or curve not in CURVES or not set(policies) <= set(PRIMARY):
            raise DashboardDataError("Offline host recordings support only the primary LR-MMT pair and configured cases")
        frames = []
        for policy in policies:
            rec = self.artifacts.d5_recordings[(size, curve, policy)]
            frame = pd.DataFrame(rec["time_series"])
            frame["policy"], frame["policy_label"] = policy, self.policy_labels[policy]
            frame["source_recording"] = f"RUSHI_Task/reports/runs/{curve}/workload_{size}/{policy}.json"
            frames.append(frame)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def asset(self, name):
        if name not in ASSETS:
            raise DashboardDataError("Only approved D5 report/figures are available")
        try:
            return (self.artifacts.path("d5_reports") / name).read_text(encoding="utf-8")
        except OSError as exc:
            raise DashboardDataError(f"D5 asset unavailable: {name}") from exc

    def kpis(self):
        runs, pairs = self.runs(), self.comparisons(primary=True)
        return {"runs": len(runs), "policies": runs.policy.nunique(), "sizes": runs.workload_groups.nunique(),
                "curves": runs.power_curve.nunique(), "completed": int(runs.completed_instances.sum()),
                "rejected": int(runs.rejected_instances.sum()), "unfinished": int(runs.unfinished_instances.sum()),
                "primary_pairs": len(pairs), "wins": int((pairs.energy_reduction_pct > 0).sum()),
                "losses": int((pairs.energy_reduction_pct < 0).sum()),
                "ties": int((pairs.energy_reduction_pct == 0).sum())}

    def downloads(self):
        return (json.dumps(self.validation, indent=2, sort_keys=True, allow_nan=False),
                reconciliation_markdown(self.provenance))


def evidence_signature(root):
    """Invalidate cached validation when artifacts or recorded implementations change.

    Hash small evidence files; only stat potentially large raw/prepared inputs.
    No source data is prepared or modified. Explicit refresh also clears the cache.
    """
    root = Path(root).resolve()
    paths = {root / "ARNAV_Task/config/artifacts.json"}
    for name in ("RAW_Alibaba", "BASELINE_Comparison/reports", "RUSHI_Task/reports"):
        folder = root / name
        if folder.exists():
            paths.update(p for p in folder.rglob("*") if p.is_file() and p.suffix in (".json", ".md", ".svg", ".py")
                         and "__pycache__" not in p.parts and "archive" not in p.parts)
            if name != "RAW_Alibaba":
                paths.update(folder.rglob("*.csv"))
    for name in ("ecosched", "ROHAN_Task", "RUSHI_Task"):
        paths.update((root / name).glob("*.py"))
    paths.update((root / "RAW_Alibaba/reports").rglob("*.csv"))
    paths.update(root / p for p in ("ecosched/power_curves.json", "ROHAN_Task/config/default.json",
                                   "BASELINE_Comparison/build.py", "ENERGY_Study/instrumentation.py", "ENERGY_Study/policies.py"))
    paths.update(p for p in (root / ".git/refs").rglob("*") if p.is_file())
    paths.add(root / ".git/packed-refs")
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(path.read_bytes() if path.is_file() else b"MISSING")
    for path in sorted((root / "RAW_Alibaba/prepared").glob("*.csv")):
        digest.update(f"{path.name}:{path.stat().st_size}:{path.stat().st_mtime_ns}".encode())
    for path in (root / "RAW_Alibaba/raw", root / "alibaba-trace-2017.tar.gz"):
        digest.update(f"{path.name}:{path.stat().st_mtime_ns if path.exists() else 'missing'}".encode())
    return digest.hexdigest()


@st.cache_resource(show_spinner=False, max_entries=4)
def _cached_data(root, signature):
    return DashboardData(root)


def get_data(root=ROOT, *, refresh=False):
    if refresh:
        _cached_data.clear()
    try:
        return _cached_data(str(Path(root).resolve()), evidence_signature(root))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise DashboardDataError(str(exc)) from exc


def pareto_frontier(frame, x="energy_kwh", y="mean_wait_s"):
    """Descriptive non-dominated set; minimize both objectives in one size/curve."""
    if frame.empty:
        return frame.assign(pareto_efficient=pd.Series(dtype="boolean"))
    if frame.workload_groups.nunique() != 1 or frame.power_curve.nunique() != 1:
        raise DashboardDataError("Pareto comparisons require one workload size and one power curve")
    result = frame.copy()
    valid = result[[x, y]].notna().all(axis=1)
    result["pareto_efficient"] = pd.Series(pd.NA, index=result.index, dtype="boolean")
    points = result.loc[valid, [x, y]]
    for i, row in points.iterrows():
        dominated = ((points[x] <= row[x]) & (points[y] <= row[y])
                     & ((points[x] < row[x]) | (points[y] < row[y]))).any()
        result.loc[i, "pareto_efficient"] = not dominated
    return result
