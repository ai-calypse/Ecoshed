# Fixed algorithm ablation on unchanged raw Alibaba samples

These are in-sample development comparisons, not held-out evidence or proof of universal savings. The 64-host pool, requests, task-create releases, multiplicity, individual observed durations, simulation settings, and input hashes are unchanged. Each SPEC curve runs separately in a fresh simulator.

## Aggregate results

| Policy | Energy wins vs original CPU / 9 | Wins within performance limits / 9 |
|---|---:|---:|
| energy_first_cpu | 0 | 0 |
| energy_first_memory | 4 | 4 |
| compact_memory | 1 | 1 |
| payback_cpu | 9 | 8 |
| payback_memory | 6 | 6 |
| payback_compact_memory | 3 | 0 |

Performance limits fixed before runs: mean and p95 waiting may each rise by at most max(1 second, 5% of baseline); overload-proxy host-time fraction may rise by at most 0.01. This proxy is requested CPU/memory pressure, not a measured application SLA.

## All energy outcomes

Positive percentages save energy relative to the original CPU policy.

| Curve | Groups | Original memory | Compact memory | Payback CPU | Payback memory | Payback + compact memory |
|---|---:|---:|---:|---:|---:|---:|
| hpe_dl360_gen9 | 250 | +0.4692% | -0.6142% | +0.4115% | +0.7973% | -0.1299% |
| huawei_rh2288h_v3 | 250 | +0.4928% | -0.5967% | +0.3929% | +0.8026% | -0.1354% |
| quanta_d51b_2u | 250 | +0.4832% | -0.6096% | +0.4282% | +0.8142% | -0.1110% |
| hpe_dl360_gen9 | 1000 | -0.1477% | -0.3927% | +0.4407% | +0.0803% | -0.1234% |
| huawei_rh2288h_v3 | 1000 | -0.0983% | -0.4752% | +0.5265% | +0.1953% | -0.0910% |
| quanta_d51b_2u | 1000 | +0.0020% | -0.4796% | +0.5326% | +0.3614% | -0.0777% |
| hpe_dl360_gen9 | 4000 | -5.8239% | -0.1205% | +0.3671% * | -6.7197% | +0.2618% * |
| huawei_rh2288h_v3 | 4000 | -5.9397% | +0.0047% | +0.4227% | -7.1546% | +0.3126% * |
| quanta_d51b_2u | 4000 | -6.2362% | -0.0459% | +0.4891% | -7.4537% | +0.3687% * |

* Exceeds at least one fixed performance limit; see comparison.csv for actual metrics.

## Fair CPU/memory comparison with the same payback controller

| Memory policy | Energy wins vs payback CPU / 9 | Wins within performance limits / 9 |
|---|---:|---:|
| payback_memory | 3 | 3 |
| payback_compact_memory | 0 | 0 |

## Changes and limitations

1. Compact packing keeps incremental modeled watts as the primary objective; power ties favor a small product of remaining CPU and memory capacity, rather than equal CPU/memory utilization.
2. A migration payback gate compares staying versus moving over the unchanged 300-second control interval. It accounts for source/destination power, duplicate reservations during copying, wakeup, the 60-second source idle timeout, and sleep. Projected steady benefit must exceed 1.2 times transient cost. Tasks younger than 60 seconds are not moved. Source-group moves are accepted or rejected together, preserving transactional evacuation; rejected proposals leave no migration locks.
3. The gate uses current requests and elapsed age only. It assumes current tasks stay for the projection horizon; future completions and arrivals are unknown. It may reject pressure-relief moves that do not pay back. This is a heuristic, not a guarantee or an established novelty claim.

All 54 runs completed and conserved offered work; 18 unmodified baseline runs exactly reproduce the previous results on energy, waiting, migrations, host counts, pressure and stop time. Every candidate and adverse outcome is retained. No per-case winning policy is selected.

The source archive's legacy published compressed checksum does not match; gzip/member integrity checks and raw-member corroboration passed, as documented in RAW_Alibaba. This is batch-only requested-resource simulation with task-create release, not the entire production cluster or measured hardware energy. A claim of consistent improvement still needs untouched Alibaba time windows/samples with the algorithm and settings fixed before evaluation.

Reproduce from the repository root:

```powershell
python -m unittest POLICY_Improvement.test_policies -v
python -m POLICY_Improvement.run --curve hpe_dl360_gen9
python -m POLICY_Improvement.run --curve huawei_rh2288h_v3
python -m POLICY_Improvement.run --curve quanta_d51b_2u
python -m POLICY_Improvement.report
```
