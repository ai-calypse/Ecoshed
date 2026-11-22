"""Build the first-run comparison graphs from the validated CSV (no dependencies)."""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
source = HERE.parent / "reports" / "comparison.csv"
with source.open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
keys = ("energy_kwh", "mean_wait_s", "mean_active_hosts", "migrations",
        "overload_host_time_fraction", "energy_reduction_vs_lr_mmt_pct")
data = [{"workload_groups": int(r["workload_groups"]), "policy": r["policy"],
         "power_curve": r["power_curve"], **{key: float(r[key]) for key in keys}} for r in rows]
assert len(data) == 36
assert len({(r["workload_groups"], r["power_curve"], r["policy"]) for r in data}) == 36
template = (HERE / "first-run-results.template.html").read_text(encoding="utf-8")
assert template.count("RESULTS_DATA") == 1
output = HERE / "first-run-results.html"
output.write_text(template.replace("RESULTS_DATA", json.dumps(data, separators=(",", ":"))), encoding="utf-8")
(HERE / "source.json").write_text(json.dumps({"source": "ROHAN_Task/reports/comparison.csv",
    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "runs": len(data),
    "dataset": "first completed 36-run matrix"}, indent=2) + "\n", encoding="utf-8")
print(output)
