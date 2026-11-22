# Energy-first placement: mechanism and robustness study

**HISTORICAL SYNTHETIC DIAGNOSTIC — not Alibaba project evidence.** See
[ALIBABA_REPORT.md](ALIBABA_REPORT.md) for the active trace-derived experiment.
Exact old source/config bytes are preserved under `archive/synthetic_v1/`.

This is a new **synthetic-only** study. It does not read Yaksh's cleaned data, does not replace the original 36-run results, and does not claim raw Alibaba replay.

**510 runs, 225 paired comparisons and 24 pointwise intervals independently verified.** The study completed 80,664 individual synthetic instance replays.

## What changed

The new CPU-oriented and memory-aware variants use incremental steady-state power as the first placement objective. The memory-aware variant uses normalized CPU/memory imbalance only to break power ties (rounded at one nanowatt to remove floating-point noise). The CPU variant breaks those ties by CPU occupancy. Both inherit the same LR/MMT controller, migration guard, cooldown, admission and physical resource constraints. The original weighted-balance policy is preserved and appears as a development-only reference alongside the original CPU-oriented policy.

Instrumentation adds exact event-interval energy components, powered-idle time, stranded CPU/memory threshold measures, request-specific blocked-capacity probes, fragmentation, p95 wait and p95 turnaround. Tests verify that instrumentation preserves every metric from Brave's original engine.

## Designed mechanism case

Four requests arrive together on hosts of capacity `(100 CPU, 1 memory)`: `a=(72,.20)`, `b=(72,.80)`, `c=(14,.01)`, `d=(15,.30)`. Total CPU is 173 and total memory 1.31, so at least two hosts are necessary. A feasible packing is `{a,d}=(87,.50)` and `{b,c}=(86,.81)`. The memory-aware power tie-break recovers that two-host solution; the CPU tie-break uses three. Both resource fractions remain below 0.9.

This is an intentionally constructed unit mechanism, not a random workload sample. The controller is disabled **for both policies only in this case**, with zero wake latency and immediate sleep to isolate placement. It establishes existence of a saving opportunity, not broad production performance or LR-controller performance.

| Curve | CPU-oriented kWh | Memory-aware kWh | Reduction | Preset budgets pass |
|---|---:|---:|---:|---|
| hpe_dl360_gen9 | 0.146486 | 0.134722 | +8.031% | True |
| huawei_rh2288h_v3 | 0.141194 | 0.128806 | +8.774% | True |
| quanta_d51b_2u | 0.147278 | 0.133444 | +9.393% | True |

## Held-out generated workloads

Five requested resource mixes, two lifetime bands and eight held-out seeds give 80 paired base comparisons. Every episode has 160 independent instances on 16 synthetic hosts. The same workload bytes, runtime and simulator settings are used for each pair. The synthetic catalog and probabilities are explicit in `workloads.py`; the scarce-CPU mix is illustrative and is not a reconstruction of the original Alibaba distribution.

Energy decreased in **25/80** base held-out pairs. **6/80** met all preset practical energy, waiting, migration and pressure budgets. These criteria are stronger than simply observing any positive energy difference.

| Mix | Lifetimes | Episodes | Mean reduction | 95% pointwise bootstrap interval | All budgets pass |
|---|---|---:|---:|---:|---:|
| cpu_heavy | short | 8 | -0.069% | [-0.168, +0.000]% | 0/8 |
| cpu_heavy | long | 8 | +0.005% | [-0.147, +0.152]% | 0/8 |
| memory_heavy | short | 8 | +0.000% | [+0.000, +0.000]% | 0/8 |
| memory_heavy | long | 8 | +0.008% | [-0.112, +0.136]% | 0/8 |
| mixed | short | 8 | +1.466% | [+0.212, +3.444]% | 3/8 |
| mixed | long | 8 | -0.367% | [-1.346, +0.783]% | 1/8 |
| balanced | short | 8 | -0.438% | [-1.228, +0.026]% | 0/8 |
| balanced | long | 8 | +0.118% | [-0.854, +1.128]% | 1/8 |
| scarce_cpu_heavy | short | 8 | -0.143% | [-0.430, +0.000]% | 0/8 |
| scarce_cpu_heavy | long | 8 | -0.566% | [-1.544, +0.532]% | 1/8 |

Positive reductions mean less modeled energy; negative values mean more energy. The mixed/short result is encouraging within this generator, but its confidence interval does not establish that the practical 1% saving threshold is exceeded at the population level. Other base-case intervals include zero. The original general energy-saving claim remains unestablished.

## Complete power and assumption sensitivity

Each row uses the same eight mixed/long held-out seeds. Power-curve changes reuse the same workloads; other cases vary exactly one setting from the HPE baseline. These rows are correlated sensitivity checks, not additional independent production observations.

| Curve / setting | Mean reduction | 95% pointwise bootstrap interval | All budgets pass |
|---|---:|---:|---:|
| huawei_rh2288h_v3 | +0.849% | [+0.083, +1.572]% | 3/8 |
| quanta_d51b_2u | +0.226% | [-0.430, +0.833]% | 0/8 |
| memory_unit_bytes=34359738368 | +0.034% | [-0.403, +0.521]% | 0/8 |
| memory_unit_bytes=137438953472 | -0.798% | [-2.085, +0.459]% | 1/8 |
| migration_bandwidth_bytes_s=62500000 | -0.798% | [-2.085, +0.459]% | 1/8 |
| migration_bandwidth_bytes_s=250000000 | +0.034% | [-0.403, +0.521]% | 0/8 |
| control_interval_s=30 | +0.785% | [-0.078, +1.625]% | 2/8 |
| control_interval_s=300 | +1.190% | [+0.399, +1.903]% | 2/8 |
| idle_timeout_s=0 | -0.106% | [-1.038, +0.958]% | 2/8 |
| idle_timeout_s=300 | -0.381% | [-1.413, +0.767]% | 1/8 |
| sleep_watts=0 | -0.362% | [-1.322, +0.805]% | 1/8 |
| sleep_watts=15 | -0.379% | [-1.449, +0.760]% | 1/8 |
| wake_latency_s=0 | -0.041% | [-2.010, +1.887]% | 3/8 |
| wake_latency_s=30 | -0.017% | [-1.439, +1.119]% | 2/8 |

The HPE mixed/long base case uses 60-second control, 64 GiB per normalized memory unit, 125 MB/s migration bandwidth, a 60-second idle timeout, 5-W sleep and 10-second wake latency. The full matrix is retained, including adverse outcomes. A favorable 300-second sensitivity result is not a reason to retune the policy on these held-out cases; any selected revision would require a new untouched evaluation set.

## Protocol and interpretation

Development seeds are 11–13; held-out seeds are 101–108. No policy parameter search or selection was performed. Source/config hashes and the entire plan were locally snapshotted before execution in `reports/frozen_protocol.json`; this is not an external preregistration. Each pointwise 95% interval resamples paired episode reductions 2,000 times with bootstrap seed 560. Tasks are not treated as independent samples. The eight generated episodes support inference only within the specified synthetic generator. The 24 intervals are exploratory and have no family-wise or false-discovery correction.

Preset per-episode acceptance: at least 1% energy reduction; no rejected/unfinished work; mean and p95 wait increase no greater than 5% or a 1-second floor; migration increase no greater than 10% or a one-migration floor; pressure-proxy increase no greater than 0.01 absolute. The pressure proxy is not observed SLA failures. Meeting these synthetic budgets does not establish acceptable behavior for an actual production service.

The residual fragmentation index compares pooled free normalized host-units with co-located balanced residual fit, considering powered hosts only. Stranded threshold metrics use >=90% utilization in one resource and <=50% in the other. Probe metrics integrate free CPU on hosts that could fit a catalog request's CPU but not its memory. All diagnostics use reservations, including wake/migration reservations, rather than measured usage. They describe different aspects of fragmentation and need not improve together.

## What this supports

There is a verified mechanism by which CPU/memory-aware tie-breaking can reduce host count and modeled energy without sacrificing the preset budgets. Held-out evidence shows that benefits depend on workload shape, task duration, power curve and controller assumptions. It does not support unconditional savings, measured electricity savings or an Alibaba production claim. Direct raw-trace replay with independently prepared windows and calibrated migration assumptions remains a separate required step.

## Reproduce

```sh
python -m unittest discover -s ENERGY_Study/tests -v
python -m ENERGY_Study.run
python -m ENERGY_Study.verify
python ENERGY_Study/analysis/build_report.py
```

Review all numeric outcomes in [paired_comparisons.csv](reports/paired_comparisons.csv), [confidence_intervals.csv](reports/confidence_intervals.csv), [runs.csv](reports/runs.csv) and [verification.json](reports/verification.json).
