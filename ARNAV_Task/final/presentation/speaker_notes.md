# EcoSched speaker notes

Provisional: adapt 12–15 minutes plus a 2–3 minute live demonstration; no course limit found.

Presenter allocations below are provisional and require team agreement.

## Slide 1: EcoSched

Provisional presenter: Arnav Desai

Introduce the team and the central question. We evaluate a specific CPU/memory placement change under shared conditions; we do not claim a universally better scheduler. The final package combines frozen scheduling evidence with a real, separately verified Kafka workload-arrival demonstration. The speaking allocation and suggested timing in these notes are provisional; no course presentation limit was found in the repository.

## Slide 2: Balanced resources do not automatically mean lower energy

Provisional presenter: Brave Desai

Start with the competing mechanisms. Packing can reduce the number of powered servers, while balancing requests can improve feasibility and initial waiting. A machine can be CPU-light yet memory-constrained. Neither balanced occupancy nor a lower migration count is itself an energy objective. Our experiment was designed to retain a negative result if the proposed balance term spreads work too far.

## Slide 3: Change placement; hold the controller fixed

Provisional presenter: Rohan Rane

Explain the controlled ablation before showing results. CPU-oriented placement still enforces memory feasibility; only its scoring term omits explicit balance. Both primary variants share one LR/MMT implementation and its settings. The additional baselines do not consolidate, so their comparison is broader than placement alone. No same-job, payback or later controller extension enters the active conclusions.

## Slide 4: One evidence pipeline, from raw rows to research outputs

Provisional presenter: Brave Desai

Follow the architecture from the independent raw pipeline into validated workload instances, the event engine and four policies. Power is a surrogate SPECpower mapping. Baseline analysis selects the active outcomes and D5 explains mechanisms; D6 makes them inspectable and reproducible. The report reuses original vector assets. This slide uses editable shapes derived from the same A01 diagram data.

## Slide 5: Preserve each task group’s individual instances

Provisional presenter: Yaksh Gandhi

Yaksh delivered the earlier reproducible handoff. The active study independently prepares raw Alibaba observations with seed 2026. The three samples contain 16,534, 68,457 and 378,285 instances. Every group keeps its declared multiplicity. Missing optional utilization is not filled with zero, and observed future durations are not sent to policies or Kafka. Filtering complete observations introduces selection bias.

## Slide 6: A common feasibility rule; one extra scoring term

Provisional presenter: Rohan Rane

Both resources must physically fit for every policy, and FIFO admission remains shared. LR uses past/current aggregate reservations; MMT selects the smallest eligible memory request under a common copy-time model. Safe shadow reservations, all-or-nothing evacuations, cooldown and a per-tick budget prevent contradictory plans. This is an online batch-instance adaptation, not an exact CloudSim/PABFD reproduction. The score is a placement heuristic; the engine accounts for actual modeled transitions.

## Slide 7: SPECpower supplies a surrogate, not Alibaba electricity

Provisional presenter: Brave Desai

Describe the actual SPECpower points and linear interpolation. Active idle and sleeping are different states. The same selected curve is applied to each sampled host without scaling for CPU core count or RAM, so this is a hardware sensitivity model. kWh equals joules divided by 3.6 million. Wh per completed instance uses completed individual instances, never task groups. These curves are not statistical replications.

## Slide 8: 36 outcomes; 9 primary paired comparisons

Provisional presenter: Rohan Rane

The full grid has 36 active outcomes rather than the historical six-policy grid. The nine primary pairs match workload size and power curve exactly. All active runs complete identical offered work without rejected or unfinished instances. Pressure is requested-resource time above a threshold, not measured application SLA failure. We never average P95 quantiles across runs or categories.

## Slide 9: Memory-aware placement saves energy in 4/9 cases

Provisional presenter: Rushi Jhala

Pause on the negative bars. The proposed rule saves energy in four of nine conditions, but all largest-workload cases are worse by 10.96–14.56%. The small medium Huawei gain is not statistically significant evidence because this is a deterministic grid without independent replications. We preserve each curve separately. This editable chart reproduces the Phase 6 R03 values and sign convention.

## Slide 10: A larger powered footprint buys modest performance gains

Provisional presenter: Rushi Jhala

Use this one matched condition to explain the trade-off. The energy penalty accompanies more mean active hosts, slightly lower mean initial waiting and lower reservation pressure. All values come from the same two original run summaries. Pressure remains a modeled proxy. Peak hosts, migration pause and P95 outcomes are in the report, not hidden. Pareto comparisons are descriptive only within one size/curve and objective pair.

## Slide 11: Extra busy-host on-time explains the largest-case penalty

Provisional presenter: Rushi Jhala

D5 decomposes each curve’s net candidate-minus-baseline gap. About 88% in the earlier summary is a pooled descriptive ratio of component sums to gap sums; it is not one physical energy experiment. The separate shares are shown here. The proposed rule wakes fewer servers, but spreads work across more already-on hosts. Extra time with work dominates; idle-empty time contributes little, while fewer wakes offset some cost. This is supported mechanism analysis, not universal production causality.

## Slide 12: Kafka transports arrivals; it does not run the scheduler

Provisional presenter: Arnav Desai

Follow validated input, ordered producer, one Kafka partition, validating consumer, SQLite WAL and Streamlit monitoring. The external controller survives browser reruns and navigation. Persist before manual offset commit. Exact duplicates do not inflate unique instances, while conflicts fail verification. The guarantee is at least once with idempotent persistence; no distributed exactly-once or high availability is claimed.

## Slide 13: Classroom demo: inspect results, then replay real arrivals

Provisional presenter: Arnav Desai

The screenshot is recorded Phase 5 evidence, not an active session in this deck. Switch to localhost:8501, show the offline overview/primary comparison, then open Live Workload Replay. Select 250 groups at 600× and start once. Count distinct instances separately from deliveries. Show offered CPU/memory requests, logical time and actual Kafka lag, never live energy or hosts. Let event-level verification finish. If unavailable, clearly label the historical-session/screenshot fallback; do not fake a live demonstration.

## Slide 14: Verified numbers; unresolved historical metadata

Provisional presenter: Arnav Desai

Distinguish compressed archive identity, extracted-member identity, prepared-output equivalence, source fingerprints and numerical consistency. Recovering exact CSVs does not recreate three historical metadata versions. We have not rerun the complete scheduler matrix in D6, so we do not claim fresh end-to-end simulation reproduction. Phase 6 also records 167 byte-identical compared publication files. Later documentation edits are tracked separately from those historical receipts.

## Slide 15: The defensible result is an energy/performance trade-off

Provisional presenter: Arnav Desai

Conclude with the actual scientific result: balance-aware placement can improve some performance outcomes but can work against consolidation. Negative findings are useful because the ablation and D5 explain why. Future work should freeze settings and test independent windows, calibrate power/migration assumptions and define application-level acceptability. The team’s code ownership is documented separately from imported commit authorship. Invite questions, then use appendices for exact values and provenance.

## Slide 16: Appendix · all primary energy comparisons

Provisional presenter: Rushi Jhala

Each row is a matched workload/curve pair. The memory-aware column is a candidate, CPU LR-MMT is baseline, and positive reduction means savings. All values are from the active raw-derived study; historical scheduler reports used different prepared data and must not be substituted.

## Slide 17: Appendix · fixed controls and resource-skew scope

Provisional presenter: Rohan Rane

These fixed settings come from RAW_Alibaba/config.json and ROHAN_Task/config/default.json. Migration uses an assumed normalized-memory conversion and per-transfer bandwidth. Resource categories are fixed by prepared request fractions relative to median host capacity. Full tables preserve absent observations and individual P95 quantiles. No whole-run energy is attributed to skew categories.

## Slide 18: Appendix · verified Kafka fast-mode sessions

Provisional presenter: Arnav Desai

These are the original Phase 4 fast-mode measurements. Session duration includes controller completion/verification and is not isolated verifier time. Timed browser replay has a different purpose and must not be merged into this throughput chart. Duplicate redelivery doubled deliveries without changing unique counts; consumer restart and broker restoration were verified. One laptop and one broker do not establish distributed scalability.

## Slide 19: Appendix · unresolved metadata references

Provisional presenter: Arnav Desai

Do not repair this slide by replacing old expected hashes. They are evidence of the historical lineage gap. Full hashes, source references and search scope are in the report appendix and reconciliation document. The active archive matches its own recorded compressed checksum; the released legacy compressed archive is different even though raw payloads corroborate.

## Slide 20: Appendix · references and individual contribution evidence

Provisional presenter: All team members

Academic references were checked against the author manuscript or publisher record. Tetris uses the conference DOI printed in the paper. Dataset, SPECpower and software references are included in the report bibliography. Implementation ownership follows teammate handoffs and code paths; Rohan’s module was imported in a Brave-authored commit. Arnav’s D6 work remains uncommitted, and no commit attribution is invented.
