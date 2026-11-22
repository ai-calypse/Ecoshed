# Rohan's D3 implementation and executed comparisons

Rohan's scheduling task is implemented and integrated: LR-MMT, the CPU/memory-aware
placement variant, first-fit and CPU best-fit baselines, overload relief,
underload evacuation, MMT migration selection and regression tests. The policies
reuse Yaksh's prepared inputs and Brave's existing simulator and power curves.

**36 of 36 runs passed validation.** Each workload was replayed under four policies
and three curves, completing **10,078,092 instance replays** in total. All runs had
zero rejected instances, zero unfinished instances and all task groups completed.

## Primary HPE results

Modeled energy, kWh, using SPEC result 20151215-00708:

| Task groups | Instances per run | First-fit | Best-fit | LR-MMT | LR-MMT + memory |
|---:|---:|---:|---:|---:|---:|
| 250 | 40,381 | 9.382510 | 9.409366 | 9.567916 | 9.588541 |
| 1,000 | 160,813 | 25.835535 | 25.982859 | 26.568034 | 28.498380 |
| 4,000 | 638,647 | 83.269500 | 83.268462 | 83.592332 | 87.618801 |

For the primary curve, the memory-aware variant used **0.216%, 7.266% and 4.817%
more energy** than CPU-oriented LR-MMT at the three sizes. These runs do not
support a claim that this placement heuristic reduces modeled energy.

The corresponding migration and waiting outcomes show the performance tradeoff:

| Groups | LR-MMT migrations | Memory-aware migrations | LR-MMT mean wait, s | Memory-aware mean wait, s | LR-MMT overload fraction | Memory-aware overload fraction |
|---:|---:|---:|---:|---:|---:|---:|
| 250 | 2,061 | 1,953 | 8.055 | 7.796 | 0.02937 | 0.02681 |
| 1,000 | 8,974 | 6,736 | 8.249 | 6.616 | 0.12420 | 0.09801 |
| 4,000 | 9,941 | 6,107 | 227.327 | 212.082 | 0.63096 | 0.53137 |

Overload fraction is the shared engine's time-weighted CPU-or-memory reservation
pressure proxy above 0.9, divided by 64 hosts times simulated duration. It is not
an observed SLA-failure rate. Waiting includes queuing and host wake delay;
migration pause is separate. The full comparison also records maximum wait,
Wh/instance, active hosts and migration pause-instance-seconds.

## Power-curve sensitivity

The percentage below is `100 * (LR-MMT kWh - memory-aware kWh) / LR-MMT kWh`.
Positive means savings; negative means more energy.

| Groups | Curve | LR-MMT kWh | Memory-aware kWh | Energy reduction vs LR-MMT |
|---:|---|---:|---:|---:|
| 250 | HPE DL360 Gen9 | 9.567916 | 9.588541 | -0.2156% |
| 250 | Huawei RH2288H V3 | 9.367953 | 9.364693 | +0.0348% |
| 250 | QuantaGrid D51B-2U | 9.732144 | 9.752576 | -0.2099% |
| 1,000 | HPE DL360 Gen9 | 26.568034 | 28.498380 | -7.2657% |
| 1,000 | Huawei RH2288H V3 | 26.250395 | 27.606150 | -5.1647% |
| 1,000 | QuantaGrid D51B-2U | 27.304988 | 29.359701 | -7.5250% |
| 4,000 | HPE DL360 Gen9 | 83.592332 | 87.618801 | -4.8168% |
| 4,000 | Huawei RH2288H V3 | 80.666962 | 83.755507 | -3.8288% |
| 4,000 | QuantaGrid D51B-2U | 85.221298 | 89.658220 | -5.2064% |

Memory-aware placement reduced migrations and mean waiting in all nine primary
pair comparisons, while reducing energy in only the small Huawei case. It also
kept more hosts powered. For HPE at 4,000 groups, mean active hosts increased from
51.56 to 58.71, consistent with the higher energy despite fewer migrations. This
is descriptive evidence from a fixed model, not a causal or statistical proof.

The non-migrating baselines used less energy than the consolidation variants in
these runs, with higher pressure/waiting in several comparisons. This demonstrates
why migration counts, waits and pressure must accompany energy figures.

## Assumptions and scope

All policies share the same 64 Alibaba hosts, unchanged 250/1,000/4,000-group
inputs, original instance counts, FIFO queue, request-based constant demand,
physical resource constraints, sleep/wake model and 43,200-second arrival window.
Each run accounts for the full window and drains outstanding work. In this matrix
all work completed before the window ended, so every stopping time was 43,200 s
and every reported drain time was zero. Unit tests separately cover completion
beyond the arrival horizon.

Migration assumes **64 GiB per normalized memory unit** and **125 MB/s per
concurrent transfer**. This is an explicit experimental conversion, not a field
measured in the Alibaba data. It does not change normalized host capacities.
Brave's stop-and-copy engine retains both reservations during transfer and pauses
execution. Policy conclusions depend on these assumptions.

The shared detector uses 10 recent control samples, tricube local linear CPU
regression, a 1.2 safety factor and a common 0.9 memory guard. MMT uses smallest
memory first at fixed bandwidth. Both variants use the same controller, cooldown,
migration budget and evacuation rules; only their placement score differs. This
is the documented batch-instance adaptation in [the handoff](README.md), not an
exact reproduction of the original CloudSim/PlanetLab experiment. The memory
score is the initial project heuristic and has not been selected by tuning on
these benchmark results. Resource-skew attribution, statistical analysis and
broader migration/parameter sensitivity remain subsequent analysis work.

## Verification evidence

- **14 policy tests, 18 Brave simulator tests and 15 Yaksh data tests passed:**
  47 unit/regression tests in total.
- **104 read-only prepared-data checks passed.** No new full raw-source validation
  or raw-data download is claimed.
- The [matrix validator](reports/validation.json) checked all 36 unique
  combinations, current input/implementation hashes, common simulation and LR/MMT
  settings, instance conservation, energy reconciliation and migration reasons.
- Each run reconciled outcome IDs, timing, sampled capacities, migration logs and
  fully drained reservations. Engine capacity enforcement applies at every
  reservation; sample checks provide an additional validation layer.
- An [independent integration audit](reports/integration_audit.json) checked both
  detailed 250-group smoke outputs: every completed instance's elapsed runtime
  equals its Yaksh group duration plus its logged migration pauses.
- All **47 files** in Yaksh's package remain byte-identical to the supplied ZIP.
  Brave's simulator source hashes match its earlier verified integration report.
- Policy modules compile successfully; a GitHub workflow runs policy/simulator
  tests and a real two-policy smoke comparison on future pushes and pull requests.

Raw numeric results: [comparison.csv](reports/comparison.csv).
Full per-run metrics and provenance: [summaries.json](reports/summaries.json).
Reproduction instructions and algorithm details: [README.md](README.md).
