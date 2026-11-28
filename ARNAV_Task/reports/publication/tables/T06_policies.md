# Active scheduling policy definitions

The primary controlled ablation changes placement only. Additional baselines are included without restoring historical policies.

| Policy | Label | Definition | Source |
| --- | --- | --- | --- |
| first_fit | First Fit | Powered-host-first first fit; common FIFO admission and CPU/memory feasibility. | ROHAN_Task/README.md |
| best_fit | Best Fit | Fullest feasible CPU host, preferring powered hosts; no consolidation controller. | ROHAN_Task/README.md |
| lr_mmt | CPU-oriented LR-MMT | Common LR overload detector and MMT selector; CPU-oriented incremental-power placement. | ROHAN_Task/README.md |
| lr_mmt_memory | LR-MMT + CPU/Memory-Aware Placement | Same LR/MMT controller; incremental-power score plus CPU/memory imbalance penalty. | ROHAN_Task/README.md |

Sources: `ROHAN_Task/README.md`, `ROHAN_Task/config/default.json`, `BASELINE_Comparison/reports/REPORT.md`.
