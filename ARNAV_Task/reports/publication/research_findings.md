# EcoSched: verified findings for publication preparation

## Objective and controlled methodology

Compare CPU-oriented LR-MMT with LR-MMT plus CPU/memory-aware placement while holding workload, 64-host pool, SPECpower model, overload detection and MMT migration selection constant. First Fit and Best Fit are additional baselines; unlike the primary pair, their comparison also changes consolidation behavior. The 36 deterministic outcomes cover four approved policies, three workload sizes and three separately evaluated power curves. No benchmark simulation was rerun for these exports.

## Energy findings and sensitivity

Memory-aware placement saves modeled energy in **4/9 primary comparisons**. Savings cases by workload size: 250 groups: 3/3, 1,000 groups: 1/3, 4,000 groups: 0/3. At 4,000 groups it consumes **10.96–14.56% more energy**, depending on the power curve. It does not consistently improve energy. Figure R03 and table T09 preserve each signed comparison. The separate SPECpower cases are surrogate sensitivity checks, not statistical replications or one pooled physical energy experiment. Wh per completed instance uses individual instances, not task groups.

## Performance and placement mechanism

At the largest workload the mean-wait changes are -1.592 to -1.032 seconds (candidate minus baseline). Improved waiting or resource pressure can accompany higher energy. R06–R11 retain host, migration, pause, waiting, pressure, fragmentation and stranded-capacity trade-offs without averaging P95 quantiles. Reservation pressure is a modeled overload/SLA proxy, not measured application SLA failure.

D5's recorded decision analysis and illustrative placement-score arithmetic explain why the memory-balance penalty can favor spreading work: its illustrative balance advantage is 7.04–8.74 times the incremental-power advantage. At the largest workload, additional powered time while running work dominates the energy gap, partly offset by fewer wake transitions. R05, R14 and R15 reuse D5's decomposition, sampled host traces and placement diagnostics. They are not a new causal experiment or tuning sweep.

## Resource-skew scope and additional baselines

Against First Fit, memory-aware LR-MMT uses less modeled energy in 2/9 matched conditions. Against Best Fit, memory-aware LR-MMT uses less modeled energy in 3/9 matched conditions. Resource-skew outcomes exist only for the two primary policies. The smallest workload has 0 CPU-heavy instances; its CPU-heavy wait/migration outcomes are absent, not zero. Category-specific energy has no established attribution method and is not reported. R13 selects one curve; T12 retains all supported outcomes and explicit missing categories.

## Kafka demonstration

Phase 4 fast-mode transport receipts verify 250 groups / 16,534 instances, 1,000 groups / 68,457 instances, 4,000 groups / 378,285 instances. Figure S01 reports the original session wall times and throughput, not scheduler benchmark performance. The browser-driven 600× replay completed 16,534 unique arrivals in 72.698 seconds (227.43 distinct instances/s) with complete event-level verification. Fast-mode and timed runs are separate. Exact duplicate delivery does not inflate unique counts; interruption recovery is documented in T15. These are single-broker laptop observations, not evidence of distributed scalability, exactly-once transport or live scheduling. Arrival demand is offered requests, not allocated resources or server utilization.

## Integrity, recovery and limitations

Phase 3 independently verified raw-row relationships, all six raw-member fingerprints and all five reconstructed prepared-file hashes; the active compressed archive matches its recorded checksum. The legacy compressed archive has a different checksum, even though raw payloads corroborate. **Three historical metadata discrepancies remain unresolved**: prepared manifest, raw summaries and archive audit. Exact prepared-output recovery and numerical result consistency do not establish full historical lineage or a fresh end-to-end simulation reproduction. See T17 and the provenance reconciliation report.

The study has one deterministic sample per size, a fixed host pool, request-based load and surrogate SPECpower mapping, modeled migration/sleep assumptions, no online background load, no repeated stochastic trials and no statistical significance claim. It does not establish universal scheduler superiority or measured Alibaba production energy savings. Resource-skew sampling and sampled host recordings limit category and temporal inference. Runtime replay histories are optional; a frozen verified extract permits portable historical figures without Kafka or the raw archive. These assets support a subsequent academic report and presentation; this summary is not the final report.

## Authoritative sources

`BASELINE_Comparison/reports/summaries.json`, `proposal_pairs.csv`, corresponding `RAW_Alibaba/reports/runs/**/summary.json`, `RUSHI_Task/reports/*.csv` and recorded run JSONs, and D6 Phase 3–5 verification receipts. Every exported figure/table has source hashes and a caption in the publication manifests.
