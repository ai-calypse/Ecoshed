# Active proposal comparison

Run `python -m BASELINE_Comparison.build` from the repository root.

The primary pair is **CPU-oriented LR-MMT versus LR-MMT + CPU/memory-aware
placement**. First Fit and Best Fit are additional baselines. Later scheduler
extensions are excluded from the active report, plots and result exports.

This read-only analysis checks the original raw-Alibaba 54-run grid, current
source hashes, input manifest, simulation settings and complete work, then
selects the 36 outcomes belonging to these four policies. It does not rerun the
simulation or change data, policies or prior raw results.

Read [the report](reports/REPORT.md) and [the graph](reports/proposal_energy_change.svg).
The nine primary comparisons are in `reports/proposal_pairs.csv`; all four-policy
pairwise comparisons are in `reports/all_pairwise_comparisons.csv`.

The proposed implementation saves energy in 4/9 cases and loses in 5/9; it uses
10.96–14.56% more energy on the largest samples. CPU-oriented LR-MMT therefore
performs better on energy overall in this grid. Memory-aware placement also
reduces pressure and mean waiting on the largest sample: the conclusion concerns
energy, not superiority on every metric.

The previous extended comparison is preserved in `historical_payback/reports`
for provenance and excluded from all active exports. The original raw source
results remain unchanged in `RAW_Alibaba/reports`.
