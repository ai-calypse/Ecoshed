AMS 560  /  MID-TERM CHECKPOINT  /  26 OCTOBER 2026

EcoSched

CPU and memory-aware placement for energy-efficient cluster scheduling

Team: Arnav Desai, Brave Desai, Rohan Rane, Rushi Jhala and Yaksh Gandhi

## 1. Project objective and description

EcoSched investigates whether considering both CPU and memory demand during placement can reduce modeled cluster energy without unacceptable waiting, overload or migration costs. Our primary comparison is **CPU-oriented LR-MMT versus LR-MMT + CPU/Memory-Aware Placement**. Local Regression (LR) overload detection and Minimum Migration Time (MMT) selection remain fixed; only placement changes. First Fit and Best Fit provide additional baselines.

We built a trace-driven simulator using independently processed Alibaba cluster-trace-v2017 raw data. The fixed 64-host pool is tested with 250, 1,000 and 4,000 task groups (16,534, 68,457 and 378,285 instances). HPE DL360 Gen9, Huawei RH2288H V3 and QuantaGrid D51B-2U SPECpower curves are applied separately. Reported energy is a simulation estimate, not Alibaba's measured electricity consumption.

## 2. Timeline and expected deliverables

| Period / target | Work and expected output |
|---|---|
| Completed by checkpoint | Raw-data preparation, simulator, initial scheduling policies and the 36-case proposal/baseline comparison. |
| Oct 27 - Nov 8 | D5: analyze resource skew, fragmentation and energy/performance tradeoffs; test placement parameters. |
| Nov 9 - Nov 25 | D4-D5: evaluate frozen settings on untouched Alibaba samples and complete sensitivity checks; freeze core engineering and experiments by Nov 25. |
| Nov 26 - Dec 12 | D6: finish Kafka replay/dashboard demo, final report and presentation; reserve time for verification and rehearsal. |

## 3. Completion status of each deliverable

| Deliverable | Status and completed work |
|---|---|
| D1. Workload package | **Complete for the current benchmark.** Raw-table preparation, deterministic host/workload samples, individual observed runtimes, original instance counts and input hashes. |
| D2. Simulator and power | **Core implementation complete.** Event replay, CPU/memory capacity checks, FIFO queueing, sleep/wakeup, migration pauses, SPECpower integration and unit checks. |
| D3. Scheduling policies | **Initial implementation complete.** Both proposed comparison policies plus First Fit and Best Fit; shared LR/MMT controller and validated capacity constraints. |
| D4. Experiment matrix | **Initial matrix complete: 36/36 cases.** Four policies x three workload sizes x three separate power curves; all offered work completed. |
| D5. Research analysis | **Partially complete.** Energy/performance tables, graphs and sanity checks available. Detailed skew analysis, placement sensitivity and unseen-sample evaluation remain. |
| D6. Final package | **Partially complete.** Code, configuration, reproducibility instructions and plots available. Kafka demo, final report and presentation remain. |

EcoSched | Findings and completion plan

MID-TERM CHECKPOINT  /  PAGE 2

## 3. Completion status: preliminary findings

The proposed memory-aware placement saves energy in **4 of 9** paired workload/curve cases; CPU-oriented LR-MMT uses less energy in the other five. The proposed variant wins all three small workloads and the medium Huawei case. On the largest workload, its energy use increases as follows:

| Server curve | CPU LR-MMT | Proposed placement | Energy increase |
|---|---|---|---|
| HPE DL360 Gen9 | 34.270 kWh | 39.136 kWh | +14.20% |
| Huawei RH2288H V3 | 34.017 kWh | 37.745 kWh | +10.96% |
| QuantaGrid D51B-2U | 35.333 kWh | 40.478 kWh | +14.56% |

Memory-aware placement lowers mean waiting and requested-resource pressure on the largest workloads, but keeps more hosts powered. Current results therefore show an energy/performance tradeoff and do not establish consistent energy savings. All 36 active cases preserve identical offered work and report zero rejected or unfinished instances. Later scheduler extensions are outside this checkpoint's scope.

## 4. Plan to complete unfinished deliverables

**D4 - Extended validation:** Select additional untouched Alibaba windows or samples using a recorded sampling rule. Freeze policy settings before evaluation and rerun the same four-policy matrix separately for each power curve. Preserve unfavorable outcomes and validate completion and energy accounting.

**D5 - Analysis and refinement:** Break down outcomes by balanced, CPU-heavy and memory-heavy demand; measure fragmentation, active-host time and migration cost. Investigate why the current memory-balance score spreads work across extra hosts. Test placement-weight and packing refinements on development samples while keeping LR detection and MMT selection unchanged, then assess the frozen rule on untouched samples. Report energy together with waiting, migrations and overload proxies.

**D6 - Delivery:** Complete one Kafka replay/dashboard demonstration of the trace and scheduling outputs. Integrate the verified tables and graphs into the final report, document assumptions and reproduction commands, and prepare and rehearse the final presentation. The demo will visualize the experiment; simulator outputs remain the evaluation evidence.

## 5. Difficulties and risks to completing on time

**Data access and provenance:** Acquiring the raw archive and resolving earlier input ambiguity took additional effort. The active pipeline now reads the uploaded raw archive independently. Its compressed checksum differs from the published legacy archive; gzip/member integrity checks and raw-file corroboration passed. The discrepancy remains documented rather than treated as a publisher checksum match.

**Model and evidence limits:** The trace is large and has incomplete observations. We retain only complete eligible groups, which introduces selection bias. Samples overlap; the nine comparisons are not independent statistical replications. Power, migration and sleep assumptions require sensitivity checks; background online load and production dependencies are not replayed.

**Algorithm and schedule risk:** The proposed placement does not yet deliver consistent energy improvement. Further tuning may not reverse this result. We will prioritize a defensible explanation and fair evaluation, keep scope limited to placement, and freeze core work by Nov 25. The Kafka demo and final integration are the main remaining delivery risks; Nov 26-Dec 12 is reserved for completion, reruns and rehearsal.

Evidence: docs/EcoSched_Proposal.pdf; BASELINE_Comparison/reports/REPORT.md and validation.json; RAW_Alibaba/prepared/manifest.json and data_validation.json. Status reflects the current implementation; future dates are planned targets.
