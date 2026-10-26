# EcoSched D1: data preparation and sampling report

Prepared for the **Yaksh / Data & sampling** assignment in the EcoSched AMS 560 proposal. This is a data handoff, not a simulator or scheduler result.

## Completion evidence

| Proposal requirement | Delivered evidence |
|---|---|
| Acquire and verify Alibaba v2017 | Published archive checksum matches; all six extracted files checked against archive content |
| Clean schema and invalid values | All six CSVs audited; filtered task population, named output fields, exclusion accounting |
| Preserve instance_num | Unmodified source multiplicity in all cleaned/sample records; independent validation |
| Deterministic representative host sample | 64 hosts; capacity/utilization strata, seed 560, comparison table |
| Time-stratified workloads at several sizes | 250 / 1,000 / 4,000 groups; skew quotas, 15-minute bins, multiplicity bands |
| D1 documented subset, manifest, cleaned inputs | CSV package, manifest, configurations, scripts and simulator handoff |

## Verified source

The archive SHA-256 is `02c1fbc412fccc03b748c05ec18fc30fd93c0bc383eea47ac21146c4aa2235df`. Full-source validation also confirms each extracted CSV is byte-identical to the corresponding file inside that verified archive.

| Raw file | Rows | Size (MiB) |
|---|---:|---:|
| batch_instance.csv | 16,094,656 | 818.77 |
| batch_task.csv | 80,553 | 4.42 |
| container_event.csv | 11,102 | 0.83 |
| container_usage.csv | 1,480,906 | 263.21 |
| server_event.csv | 1,352 | 0.05 |
| server_usage.csv | 187,963 | 18.15 |

The source has **16,094,656 instance-trial records**. Of these, **3,992,098** lack job/task join keys and **14,166,324 (88.0%)** lack average actual memory measurements. These are measured source limitations, not values imputed by this pipeline.

The headerless container-event file has an extra trailing blank field; it is recognized and counted. The missing download schema was supplied from the official v2017 repository and saved under `docs/upstream/`. The proposal's `machine_meta` filename is corrected to v2017's `server_event.csv`.

## Primary population and cleaning

The arrival window is **[0, 43200) seconds** (12 hours). Task/instance completion at the endpoint is allowed. Only completed task groups with valid requests and usable first-attempt runtime observations enter the population.

**39,861 clean task groups**, representing **6,342,960 declared instances**, remain. Median duration-observation coverage is **100.0%**. There are **2,454** groups with partial duration coverage; their modeled runtime still uses the available observations and their original multiplicity is preserved.

| Exclusion (first applicable reason) | Task groups |
|---|---:|
| arrival outside window | 26,354 |
| invalid or censored task end | 230 |
| missing or nonfinite required value | 10 |
| no valid completed first attempt | 558 |
| not terminated | 13,540 |

The exclusions plus 39,861 retained groups reconcile to 80,553 original task rows.

The per-group runtime is the mean of positive completed first-attempt durations inside the parent task interval. All replicated instances of a group use that mean. This reduces straggler variation and does not reproduce source instance staggering or DAG dependencies. Selection of completed work introduces survivor/boundary bias.

## Fixed mini-cluster

**64 of 1,313 hosts** are selected using deterministic capacity and observed CPU/memory load strata. The host-stratum total-variation distance is **0.0349** (0 is identical; 1 is disjoint). At least one host from each rounded capacity class is reserved; this deliberately overrepresents the rarest type. See `host_sampling_comparison.csv` for omitted/rounded utilization strata.

Total CPU capacity is **4096 cores**. Total normalized memory capacity is **44.353941 units**. No GB conversion is asserted.

Valid source utilization timestamps range from **39600 to 82500 seconds**. That later observation window is used only for host sampling/characterization. It is not added as background load to the first-12-hours batch experiment. Host characteristics are selected offline and are fixed for all schedulers.

## Workloads and stress diagnostics

| Groups | Declared instances | Mean offered CPU / memory capacity | Peak offered CPU / memory capacity | Role |
|---:|---:|---:|---:|---|
| 250 | 21,723 | 0.007 / 0.014 | 0.157 / 0.362 | light / smoke run |
| 1,000 | 123,401 | 0.054 / 0.115 | 0.972 / 1.942 | burst-constrained comparison |
| 4,000 | 671,994 | 0.367 / 0.778 | 6.890 / 13.490 | heavy burst stress case |

Offered demand assumes every group's instances start immediately at task creation and hold their requested resources for the modeled mean duration. Ratios above 1 require queuing/rejection or overcommit. These diagnostics are neither measured utilization nor simulated SLA violations. Keep queue/admission rules identical across policies and drain all accepted work after the arrival window.

## Representativeness

| Groups | Arrival-bin TV | Resource-skew TV | Instance-weighted resource-skew TV |
|---:|---:|---:|---:|
| 250 | 0.0654 | 0.0018 | 0.0256 |
| 1,000 | 0.0203 | 0.0003 | 0.0359 |
| 4,000 | 0.0044 | 0.0001 | 0.0099 |

Total variation compares normalized sample and clean-population distributions. Resource-mix quotas are applied first, then time/multiplicity quotas, using stable seeded hashes within strata. Samples preserve original arrival times and instance counts; they do not preserve every rare group or exact instance-weighted burst magnitude. Sampling is relative to the cleaned completed-work population, not the unfiltered source.

| Population resource skew | Task groups |
|---|---:|
| cpu_heavy | 1,188 |
| balanced | 33,415 |
| memory_heavy | 5,258 |

The skew definition compares each request's CPU and memory fractions of the median sampled host; ratio >2 is CPU-heavy and <0.5 is memory-heavy.

## Verification and reproducibility

- Independent saved-output checks: **59 passed**; full source/archive verification: **True**.
- Nine focused algorithm tests passed: selection invariance to input order, quota rounding, uniqueness, seed variation, edge sample sizes, invalid sizes, resource-skew units, nonfinite-value handling and rare host-capacity preservation.
- Fresh rebuild comparison: **18 generated data/config/report files byte-identical**, manifest identical: **True**.

No scheduler, energy model or performance experiment has been run in D1. Constant requested demand limits claims about production temporal variability; absolute RAM and migration time need explicit simulator assumptions. See `docs/SIMULATOR_HANDOFF.md` before integrating LR/MMT.

## Next team handoff

1. Brave loads hosts and the lazy instance iterator, using one common queue, sleep and completion model.
2. Rohan and Rushi use identical workload files and physical resource constraints across placement policies.
3. Yaksh keeps the manifest, configs and queue/admission rules with each result set.
4. Treat the 4,000-group replay as stress; run the smaller inputs first. Do not interpret aggregate burst pressure as a placement-policy failure or claim Alibaba actual electricity savings.

## References

- [Alibaba v2017 source and download documentation](https://github.com/alibaba/clusterdata/tree/master/cluster-trace-v2017)
- [Official schema](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2017/schema.csv)
- [Maintainer CPU-unit correction, issue 11](https://github.com/alibaba/clusterdata/issues/11)
- [Published archive SHA-256](https://raw.githubusercontent.com/alibaba/clusterdata/master/cluster-trace-v2017/SHA256SUM)
- Local requirements: EcoSched_Proposal.pdf, sections 4-6.
