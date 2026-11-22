# Energy-first scheduler: Alibaba-derived experiment results

**Historical prepared-sample comparison.** The active pipeline now independently
processes the uploaded raw archive; see [RAW_Alibaba/REPORT.md](../RAW_Alibaba/REPORT.md).
The results below used Yaksh's prepared samples and are not relabeled as raw replay.

**Every run in this report uses Alibaba-derived trace records. No artificial workloads or synthetic workload substitutions are included.** The previous generated-workload study is historical diagnostic material and is not evidence for this project.

The verified matrix contains **36 runs**, **10,078,092 completed instance replays**, and zero rejected/unfinished instances. HPE, Huawei and Quanta each have the same 12 combinations, with fresh simulator state and one power curve per run.

## Exact data scope

Inputs are the existing **prepared Alibaba v2017 package in YAKSH_Task**: a fixed 64-host pool and 250/1,000/4,000 task-group samples, preserving original instance counts, requests and arrivals. Their declared group-mean observed duration model is unchanged. The runner verifies input/config hashes against the preparation manifest and requires original source-row identifiers. It does not invent or rescale jobs.

**This is not a fresh replay/preparation of the raw archive.** No raw archive exists locally, and this environment could not connect to Alibaba's archive download host. The use of Yaksh's prepared data is explicit in every result. Re-running an independently prepared raw trace pipeline remains a separate task; these files must not be described as such a replay.

## Modeled energy: same full grid under each curve

Values are modeled kWh. A positive reduction in the last column means that the energy-first memory variant beats its energy-first CPU baseline; a negative value means more energy.

| Curve | Groups | Original LR-MMT | Original memory-aware | Energy-first CPU | Energy-first memory | New memory reduction vs new CPU |
|---|---:|---:|---:|---:|---:|---:|
| hpe_dl360_gen9 | 250 | 9.567916 | 9.588541 | 9.566115 | 9.566193 | -0.001% |
| hpe_dl360_gen9 | 1,000 | 26.568034 | 28.498380 | 26.515317 | 27.585244 | -4.035% |
| hpe_dl360_gen9 | 4,000 | 83.592332 | 87.618801 | 83.528067 | 85.036042 | -1.805% |
| huawei_rh2288h_v3 | 250 | 9.367953 | 9.364693 | 9.327196 | 9.340754 | -0.145% |
| huawei_rh2288h_v3 | 1,000 | 26.250395 | 27.606150 | 25.580207 | 26.735493 | -4.516% |
| huawei_rh2288h_v3 | 4,000 | 80.666962 | 83.755507 | 79.790456 | 81.234247 | -1.809% |
| quanta_d51b_2u | 250 | 9.732144 | 9.752576 | 9.729775 | 9.733076 | -0.034% |
| quanta_d51b_2u | 1,000 | 27.304988 | 29.359701 | 27.166449 | 28.345135 | -4.339% |
| quanta_d51b_2u | 4,000 | 85.221298 | 89.658220 | 85.241429 | 86.871680 | -1.913% |

The energy-first memory variant saved energy in **0/9** paired comparisons against its CPU counterpart. This is the observed outcome, not a guarantee or a reason to replace the data with favorable generated workloads.

## Waiting, migrations and resource use: primary HPE curve

| Groups | Policy | Mean wait, s | p95 wait, s | Migrations | Mean powered hosts | Fragmentation index |
|---:|---|---:|---:|---:|---:|---:|
| 250 | energy_first_cpu | 8.055 | 10.000 | 2,061 | 4.336 | 0.0017 |
| 250 | energy_first_memory | 7.877 | 10.000 | 2,000 | 4.387 | 0.0019 |
| 1,000 | energy_first_cpu | 8.291 | 10.000 | 8,857 | 16.549 | 0.0331 |
| 1,000 | energy_first_memory | 7.589 | 10.000 | 9,405 | 18.514 | 0.0268 |
| 4,000 | energy_first_cpu | 226.400 | 938.178 | 10,039 | 51.395 | 0.1044 |
| 4,000 | energy_first_memory | 220.294 | 937.151 | 10,777 | 54.677 | 0.0816 |

Fragmentation is the instrumented residual-resource index, not an observed hardware measurement. Waiting includes queueing and wake latency; migration pause is reported separately in the full summaries. Lower fragmentation alone does not establish lower total energy.

## Controls and limits

The two original policies and the two energy-first variants all use the same LR/MMT controller, FIFO admission, physical CPU/memory constraints, sleep/wake settings and full-window-plus-drain stopping rule. The arrival window is 43,200 seconds, control interval 300 seconds, modeled sleep 5 W, idle timeout 60 seconds and wake latency 10 seconds. Migration assumes 64 GiB per normalized memory unit and independent 125 MB/s bandwidth; neither is an Alibaba measurement.

Three differently sized samples from the same prepared window are not independent random replications. No synthetic seed bootstrap or independent-window confidence intervals are attached to these results. These are benchmark outcomes under the stated model, not measured Alibaba electricity or proof of general production savings.

## Validation and reproduction

The active runner refuses altered/unverified trace CSVs and has no synthetic fallback. Per-run checks cover unique outcomes, completion counts, drained reservations, sampled capacities and per-host/energy-component reconciliation. Full verification checks complete per-curve coverage and matching input, implementation and assumption fingerprints.

```sh
python -m ENERGY_Study.run
python -m ENERGY_Study.verify
python ENERGY_Study/analysis/build_alibaba_report.py
```

[Full numeric comparison](alibaba_reports/comparison.csv) · [Per-run summaries](alibaba_reports/summaries.json) · [Validation](alibaba_reports/validation.json)
