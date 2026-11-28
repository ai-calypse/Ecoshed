# EcoSched publication captions

## A01_system — Complete EcoSched research architecture

The offline research path uses fixed Alibaba-derived inputs, common simulation controls and separate SPECpower curves. D6 reuses frozen results and D5 evidence; it does not rerun experiments.

Evidence: system architecture. Sources: `ARNAV_Task/README.md`, `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ARNAV_Task/reports/artifact_validation.json`, `ARNAV_Task/reports/phase3_verification.json`, `RAW_Alibaba/README.md`, `RAW_Alibaba/prepared/manifest.json`, `ROHAN_Task/README.md`, `RUSHI_Task/README.md`

## A02_kafka — Kafka arrival transport and monitoring

At-least-once transport with idempotent SQLite persistence. The external controller outlives Streamlit reruns. Manual Kafka offsets are committed after persistence; no exactly-once or high-availability claim is made.

Evidence: system architecture. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ARNAV_Task/docker-compose.yml`, `ARNAV_Task/kafka/consumer.py`, `ARNAV_Task/kafka/controller.py`, `ARNAV_Task/kafka/state.py`, `ARNAV_Task/reports/artifact_validation.json`, `ARNAV_Task/reports/phase3_verification.json`, `RAW_Alibaba/prepared/manifest.json`

## A03_dashboard_modes — Offline research and live transport remain separate

Offline pages show previous scheduler simulation results. The live page monitors real arrival transport only: offered requests, throughput, lag and integrity. It provides no live energy, allocation, active-host or SLA metrics.

Evidence: system architecture. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/app.py`, `ARNAV_Task/dashboard/constants.py`, `ARNAV_Task/dashboard/data_service.py`, `ARNAV_Task/dashboard/replay_service.py`, `ARNAV_Task/reports/artifact_validation.json`, `ARNAV_Task/reports/phase3_verification.json`, `RAW_Alibaba/prepared/manifest.json`

## A04_validation — Layered reproducibility and validation

Raw payload and prepared-output identity are verified in Phase 3. Numerical consistency is independently checked. Three historical manifest/summary/audit references remain unresolved; these layers do not establish full end-to-end lineage.

Evidence: system architecture. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ARNAV_Task/reports/artifact_validation.json`, `ARNAV_Task/reports/phase3_verification.json`, `ARNAV_Task/reports/provenance_reconciliation.md`, `RAW_Alibaba/prepared/manifest.json`

## R01_energy — Modeled energy across the active experiment matrix

Modeled energy across the active experiment matrix. All four policies use identical inputs and controls within each workload/curve condition. Each mark is one offline deterministic run; curves are separate sensitivity cases. Missing values are omitted. 

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `BASELINE_Comparison/reports/summaries.json`, `RAW_Alibaba/reports/summaries.json`

## R02_efficiency_sensitivity — Workload-size and power-curve sensitivity

Workload-size and power-curve sensitivity. All four policies use identical inputs and controls within each workload/curve condition. Each mark is one offline deterministic run; curves are separate sensitivity cases. Missing values are omitted. 

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `BASELINE_Comparison/reports/summaries.json`, `RAW_Alibaba/reports/summaries.json`

## R03_primary_savings — Nine-condition primary energy comparison

Energy reduction = 100 × (CPU LR-MMT − CPU/memory LR-MMT) / CPU LR-MMT. Positive values mean savings; negative values mean higher energy. The heatmap is centered at zero. No distinct power curves are pooled.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `BASELINE_Comparison/reports/proposal_pairs.csv`

## R04_specpower — SPECpower surrogate power curves

Published SPECpower points used by the existing piecewise-linear model. The same selected whole-server curve is mapped to each sampled host using requested CPU / host capacity, without core-count or memory scaling. This is a surrogate sensitivity model, not Alibaba hardware calibration.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ecosched/power_curves.json`

## R05_d5_energy_decomposition — D5 decomposition of the largest-workload penalty

Signed D5 energy-gap components; positive means additional consumption, the opposite sign to energy reduction. Components explain the net penalty without assigning energy to individual resource-skew categories.

Evidence: D5 mechanism analysis. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `RUSHI_Task/reports/pair_energy_gap.csv`

## R06_active_hosts — Active-host footprint

Active-host footprint. All four policies use identical inputs and controls within each workload/curve condition. Each mark is one offline deterministic run; curves are separate sensitivity cases. Missing values are omitted. 

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `BASELINE_Comparison/reports/summaries.json`, `RAW_Alibaba/reports/summaries.json`

## R07_waiting — Waiting-time outcomes

Waiting-time outcomes. All four policies use identical inputs and controls within each workload/curve condition. Each mark is one offline deterministic run; curves are separate sensitivity cases. Missing values are omitted. P95 values remain individual-run quantiles and are never averaged. 

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `BASELINE_Comparison/reports/summaries.json`, `RAW_Alibaba/reports/summaries.json`

## R08_migrations — Migration activity and pause

Migration activity and pause. All four policies use identical inputs and controls within each workload/curve condition. Each mark is one offline deterministic run; curves are separate sensitivity cases. Missing values are omitted. 

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `BASELINE_Comparison/reports/summaries.json`, `RAW_Alibaba/reports/summaries.json`

## R09_pressure_fragmentation — Reservation pressure and fragmentation

Reservation pressure and fragmentation. All four policies use identical inputs and controls within each workload/curve condition. Each mark is one offline deterministic run; curves are separate sensitivity cases. Missing values are omitted. Reservation pressure is a modeled overload/SLA proxy, not observed SLA violations.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `BASELINE_Comparison/reports/summaries.json`, `RAW_Alibaba/reports/summaries.json`

## R10_stranded_capacity — Stranded resource capacity

Stranded resource capacity. All four policies use identical inputs and controls within each workload/curve condition. Each mark is one offline deterministic run; curves are separate sensitivity cases. Missing values are omitted. 

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `BASELINE_Comparison/reports/summaries.json`, `RAW_Alibaba/reports/summaries.json`

## R11_pareto_tradeoffs — Condition-specific descriptive Pareto comparisons

Each panel minimizes modeled energy and its displayed performance objective, within one identical workload/curve. Dashed lines connect non-dominated observed policies only. They do not imply a continuous feasible frontier, global optimality, statistical significance or scheduler superiority. Reservation pressure is a modeled SLA proxy.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ARNAV_Task/dashboard/data_service.py`, `BASELINE_Comparison/reports/summaries.json`

## R12_resource_composition — Resource-skew composition

Instance counts and percentages use the existing D5 resource-skew classification. The 250-group sample has no CPU-heavy instances; this population zero does not imply zero waiting or migration outcomes for that absent category.

Evidence: D5 mechanism analysis. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `RUSHI_Task/reports/workload_mix.csv`

## R13_resource_outcomes — Supported resource-skew outcomes

Only the two primary policies have D5 category outcomes. The selected curve is shown without pooling other curves; full outcomes are exported in T12. Absent categories are labeled No observations. P95 values are category-specific quantiles, never averaged; no category energy is assigned.

Evidence: D5 mechanism analysis. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `RUSHI_Task/reports/outcomes_by_task_type.csv`

## R14_offline_host_timelines — Offline sampled host-state timelines

Previously recorded D5 simulation samples, not live Kafka measurements. Busy-host means condition on hosts running work; sampled step lines are descriptive recordings and cannot reconstruct continuous event-level occupancy or energy.

Evidence: D5 mechanism analysis. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `RUSHI_Task/reports/runs/hpe_dl360_gen9/workload_1000/lr_mmt.json`, `RUSHI_Task/reports/runs/hpe_dl360_gen9/workload_1000/lr_mmt_memory.json`, `RUSHI_Task/reports/runs/hpe_dl360_gen9/workload_250/lr_mmt.json`, `RUSHI_Task/reports/runs/hpe_dl360_gen9/workload_250/lr_mmt_memory.json`, `RUSHI_Task/reports/runs/hpe_dl360_gen9/workload_4000/lr_mmt.json`, `RUSHI_Task/reports/runs/hpe_dl360_gen9/workload_4000/lr_mmt_memory.json`, `RUSHI_Task/reports/runs/huawei_rh2288h_v3/workload_1000/lr_mmt.json`, `RUSHI_Task/reports/runs/huawei_rh2288h_v3/workload_1000/lr_mmt_memory.json`, `RUSHI_Task/reports/runs/huawei_rh2288h_v3/workload_250/lr_mmt.json`, `RUSHI_Task/reports/runs/huawei_rh2288h_v3/workload_250/lr_mmt_memory.json`, `RUSHI_Task/reports/runs/huawei_rh2288h_v3/workload_4000/lr_mmt.json`, `RUSHI_Task/reports/runs/huawei_rh2288h_v3/workload_4000/lr_mmt_memory.json`, `RUSHI_Task/reports/runs/quanta_d51b_2u/workload_1000/lr_mmt.json`, `RUSHI_Task/reports/runs/quanta_d51b_2u/workload_1000/lr_mmt_memory.json`, `RUSHI_Task/reports/runs/quanta_d51b_2u/workload_250/lr_mmt.json`, `RUSHI_Task/reports/runs/quanta_d51b_2u/workload_250/lr_mmt_memory.json`, `RUSHI_Task/reports/runs/quanta_d51b_2u/workload_4000/lr_mmt.json`, `RUSHI_Task/reports/runs/quanta_d51b_2u/workload_4000/lr_mmt_memory.json`

## R15_d5_placement — D5 explanation of memory-balance placement

Left: D5's fixed illustrative score arithmetic, not an experiment rerun or fitted causal model. Right: actual disagreement outcomes from recorded primary-policy placement decisions at the largest workload. The balance term can outweigh the power preference for busy hosts.

Evidence: D5 mechanism analysis. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `RUSHI_Task/reports/placement_decisions.csv`, `RUSHI_Task/reports/placement_score_arithmetic.csv`

## S01_fast_replay — Measured fast-mode Kafka replay

Complete authentic workloads replayed as fast as possible in the Phase 4 environment. Throughput uses distinct persisted instances / recorded session wall time. Wall time includes the controller's completion/verification lifecycle; it is not an isolated verifier benchmark. These single-session observations do not establish distributed scalability or scheduler performance.

Evidence: Kafka transport verification. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ARNAV_Task/reports/phase4_verification.json`

## S02_integrity_recovery — Duplicate delivery and restart integrity

At-least-once Kafka delivery with idempotent SQLite persistence: exact redelivery increases delivery counts while unique instances remain unchanged. The adjacent table reports full event-level verification, not count-only checks. Restart evidence is from the separately recorded interruption test.

Evidence: Kafka transport verification. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ARNAV_Task/reports/phase4_verification.json`

## S03_browser_timed_replay — Recorded browser-driven timed replay

Actual sampled browser observations from Phase 5; markers denote observations, connecting lines are guides. Producer acknowledgement counters are flushed in batches and can temporarily trail consumer observations. Logical source time is distinct from elapsed wall time. This timed replay is not combined with fast-mode throughput measurements.

Evidence: Dashboard demonstration evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ARNAV_Task/reports/phase5_verification.json`

## S04_recorded_transport_history — Measured throughput, lag and offered arrival demand

Frozen read-only SQLite observations for the fully verified Phase 5 browser replay. Throughput counts distinct persisted instances in one-second wall-clock buckets; omitted buckets are unobserved, not interpolated. Lag uses actual consumer and broker offsets at observation time. Demand sums requests from arriving instances over logical 900-second intervals; it is not allocated resources or utilization.

Evidence: Kafka transport verification. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ARNAV_Task/reports/phase5_verification.json`

## T01_dataset — Dataset characteristics

Active raw-derived Alibaba v2017 package. Individual observed durations support offline simulation; arrival replay events do not expose future durations.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ARNAV_Task/reports/phase3_verification.json`, `RAW_Alibaba/config.json`, `RAW_Alibaba/prepared/manifest.json`

## T02_workloads — Workload groups and individual instances

Groups preserve original instance multiplicity. Skew counts are population counts, not category-specific performance outcomes.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `RAW_Alibaba/prepared/manifest.json`

## T03_experiment_matrix — Active experiment matrix

Exactly 36 unique outcomes: four approved policies × three workloads × three separately evaluated SPECpower curves.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `BASELINE_Comparison/reports/summaries.json`

## T04_simulator_configuration — Fixed simulator and sampling configuration

Fixed simulation assumptions. Memory-unit conversion and independent per-transfer bandwidth are modeling assumptions, not Alibaba measurements.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `RAW_Alibaba/config.json`, `ROHAN_Task/config/default.json`

## T05_power_models — SPECpower model configuration

Separate measured SPECpower curves drive a CPU-request-based surrogate, with no RAM/core-count scaling. Raw watt-point arrays are retained.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ecosched/power_curves.json`

## T06_policies — Active scheduling policy definitions

The primary controlled ablation changes placement only. Additional baselines are included without restoring historical policies.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `BASELINE_Comparison/reports/REPORT.md`, `ROHAN_Task/README.md`, `ROHAN_Task/config/default.json`

## T07_energy — Complete modeled energy results

Modeled kWh for each active outcome. Each row is a separate deterministic simulation, not measured production energy.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `BASELINE_Comparison/reports/summaries.json`

## T08_efficiency — Energy per completed individual instance

Wh per completed instance = 1000 × modeled kWh / completed individual instances; task groups are not the denominator.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `BASELINE_Comparison/reports/summaries.json`

## T09_primary_comparisons — Primary energy and performance comparisons

Energy reduction = 100 × (baseline − candidate) / baseline; CPU LR-MMT is baseline. Positive means savings. Conditions match exactly.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `BASELINE_Comparison/reports/proposal_pairs.csv`

## T10_performance — Hosts, migrations and waiting outcomes

P95 values are individual-run quantiles; no averaging across runs. Pause is accumulated instance-seconds, not elapsed experiment overhead.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `BASELINE_Comparison/reports/summaries.json`

## T11_pressure_fragmentation — Reservation pressure, fragmentation and stranded capacity

Reservation pressure is a modeled overload/SLA proxy, not application SLA violations. Stranded capacity has time-integrated units.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `BASELINE_Comparison/reports/summaries.json`

## T12_resource_skew — Supported resource-skew outcomes

Only primary policies have category outcomes: 48 observed rows plus six explicit absent-category rows. Missing outcomes remain empty, never artificial zeros. CPU-heavy means (CPU / median host CPU) / (memory / median host memory) > 2; memory-heavy means this ratio < 0.5; otherwise balanced.

Evidence: D5 mechanism analysis. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `RUSHI_Task/reports/outcomes_by_task_type.csv`

## T13_kafka_configuration — Tested Kafka infrastructure

One ARM64 broker/controller in KRaft mode, one partition and replication factor one; localhost-only external listener. Not a high-availability deployment.

Evidence: Kafka transport verification. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ARNAV_Task/docker-compose.yml`, `ARNAV_Task/reports/phase4_verification.json`

## T14_kafka_replays — Complete replay and event-level verification results

Fast and timed runs are explicitly separate. Session durations are controller lifecycle measurements, not isolated verifier time or scheduler benchmark time.

Evidence: Kafka transport verification. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ARNAV_Task/reports/phase4_verification.json`, `ARNAV_Task/reports/phase5_verification.json`

## T15_recovery — Duplicate delivery and interruption recovery

Exact duplicates increase accepted deliveries without increasing unique-instance counts. Consumer restart resumes from durable offsets after SQLite persistence.

Evidence: Kafka transport verification. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ARNAV_Task/reports/phase4_verification.json`

## T16_recorded_validation — Recorded validation and test coverage

Historical receipts are labeled by phase and not added together. Phase 6 totals, when present, use the frozen executed-test receipt; ordinary discovery skips broker tests which are counted only in the explicit integration run.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ARNAV_Task/reports/artifact_validation.json`, `ARNAV_Task/reports/phase3_verification.json`, `ARNAV_Task/reports/phase4_verification.json`, `ARNAV_Task/reports/phase5_verification.json`

## T17_provenance — Layered reproducibility and provenance status

Prepared-file byte identity, raw-member identity and numerical consistency do not repair three missing historical metadata versions. Full lineage remains unresolved.

Evidence: active research evidence. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ARNAV_Task/reports/artifact_validation.json`, `ARNAV_Task/reports/phase3_verification.json`, `ARNAV_Task/reports/provenance_reconciliation.md`

## T18_contributions — Individual contributions and Git evidence

Current ownership is checked against path-specific Git history, not the original proposal ownership table. Git authors and directory owners are distinguished. D6 is uncommitted.

Evidence: active research evidence. Sources: `ARNAV_Task/README.md`, `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `ROHAN_Task/README.md`, `RUSHI_Task/README.md`, `YAKSH_Task/README.md`, `docs/EcoSched_Proposal.pdf`

## T19_d5_energy_accounting — D5 pair energy gap

Existing D5 analysis, restricted to the active study. Energy change in D5 means candidate minus baseline; positive indicates a penalty, unlike energy reduction.

Evidence: D5 mechanism analysis. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `RUSHI_Task/reports/pair_energy_gap.csv`

## T20_d5_placement — D5 placement decisions

Existing D5 analysis, restricted to the active study. Energy change in D5 means candidate minus baseline; positive indicates a penalty, unlike energy reduction.

Evidence: D5 mechanism analysis. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `RUSHI_Task/reports/placement_decisions.csv`

## T21_d5_controller — D5 controller diagnostics

Existing D5 analysis, restricted to the active study. Energy change in D5 means candidate minus baseline; positive indicates a penalty, unlike energy reduction.

Evidence: D5 mechanism analysis. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `RUSHI_Task/reports/controller_diagnostics.csv`

## T22_d5_score_arithmetic — D5 placement score arithmetic

Existing D5 analysis, restricted to the active study. Energy change in D5 means candidate minus baseline; positive indicates a penalty, unlike energy reduction.

Evidence: D5 mechanism analysis. Sources: `ARNAV_Task/analysis/artifacts.py`, `ARNAV_Task/analysis/metrics.py`, `ARNAV_Task/config/artifacts.json`, `ARNAV_Task/config/publication.json`, `ARNAV_Task/dashboard/constants.py`, `RUSHI_Task/reports/placement_score_arithmetic.csv`

