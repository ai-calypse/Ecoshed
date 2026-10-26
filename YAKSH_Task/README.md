# Yaksh's task: data preparation and teammate handoff

**Owner:** Yaksh Gandhi (`ai-calypse`)

**Status:** Complete — D1, the reproducible workload package.

This is the data-preparation work completed by Yaksh. The original proposal is kept unchanged as a historical reference; its initial ownership table is not the ownership of this handoff.

## What I completed

- Verified the Alibaba v2017 download against the publisher's checksum and checked all six extracted files.
- Checked all 16,094,656 instance records and cleaned the task data for a documented 12-hour experiment.
- Kept **39,861 eligible task groups**, representing **6,342,960 declared instances**.
- Selected a fixed **64-host pool**, including each source host-capacity class.
- Created **250 / 1,000 / 4,000-group workloads** with fixed seed 560 and original instance counts. Calibrated their instance, CPU and memory arrival patterns against the cleaned population.
- Supplied reproducible scripts, experiment configs, a data-quality report and an instance loader for the simulator.
- Passed **15 regression tests and 117 full-source/output checks**. A separate rebuild produced the same 20 generated files and manifest byte for byte.

## Files the next teammate needs

| File | Use it for |
|---|---|
| [data/hosts_64.csv](data/hosts_64.csv) | The same machine pool for every experiment |
| [data/workload_250.csv](data/workload_250.csv) | First integration and smoke run |
| [data/workload_1000.csv](data/workload_1000.csv) | Next comparison run |
| [data/workload_4000.csv](data/workload_4000.csv) | Heavy burst stress run |
| [config/](config/) | One config per workload; file paths are relative to the config |
| [scripts/load_workload.py](scripts/load_workload.py) | Lazy iterator that turns each group into individual instances |
| [docs/SIMULATOR_HANDOFF.md](docs/SIMULATOR_HANDOFF.md) | Exact field definitions and simulator behavior |

## Next steps: simulator teammate (Brave)

1. Load `hosts_64.csv` and start with `workload_250.csv`.
2. Use `iter_instances()` in `scripts/load_workload.py`. A row with `instance_num=100` means **100 separate instances**, not one large task.
3. Add arrivals, placement, a shared queue/admission rule and completion events. An instance finishes after its modeled duration from its actual simulated start.
4. Enforce CPU and memory capacity. Track active hosts, completed/rejected instances, queuing, overload and migrations.
5. Add the SPECpower curve, sleep model and energy integration. Use the same assumptions for all policies.
6. Hand the working simulator to Rohan/Rushi for the two placement policies. The experiment team can then run the same configs for each policy.

The simulator, power model, schedulers and experiment results are the next work; this package supplies their inputs.

## Quick checks

Run from the repository root:

```sh
python3 -m unittest discover -s YAKSH_Task/scripts -p 'test_*.py'
python3 YAKSH_Task/scripts/validate_data.py
python3 YAKSH_Task/scripts/load_workload.py YAKSH_Task/data/workload_250.csv
```

The loader should report **40,381 instances** for the 250-group workload. Both check commands are read-only. The validator independently recomputes sampling quality from the CSVs without requiring the raw download. It prints results and preserves the recorded full-source report and checksums. Use `--output /tmp/ecosched-check.json` only if you want a separate saved result.

## Four details to get right

- **CPU:** use `cpu_request_cores`. Raw batch CPU `50` means **0.5 cores**; the conversion is already applied.
- **Memory:** use the existing normalized units for both hosts and requests. They are not GB. Missing actual measurements have not been filled with zero.
- **Runtime:** each instance uses its group's mean completed first-attempt runtime. This is a documented replay approximation; it does not recover DAG dependencies or straggler behavior.
- **Load:** the largest workload has bursts above cluster capacity. Queue/rejection rules must be the same for all policies. The source's observed host utilization is for characterization, not background load to add to the replay.

## Sampling quality after review

Task-group counts alone can hide bursts from tasks containing thousands of instances. The revised samples are checked by **instance count, CPU requests, memory requests and estimated work**, as well as group counts. Every size passes the declared limits.

| Task groups | Replayed instances | Instance-arrival distance | CPU-request arrival distance | Memory-request arrival distance |
|---:|---:|---:|---:|---:|
| 250 | 40,381 | 0.040 | 0.028 | 0.066 |
| 1,000 | 160,813 | 0.019 | 0.013 | 0.022 |
| 4,000 | 638,647 | 0.013 | 0.011 | 0.024 |

Distance is total variation: **0 means identical distribution, 1 means disjoint**. These arrival measures must be <= 0.10. Runtime-weighted work has a separate <= 0.20 bound; weighted resource mix must be <= 0.05. These project limits describe an approximation, not exact production replay.

The selected task groups changed in release **data-v1.1.0**. Keep the manifest with experiment results and use all policy inputs from the same version. See [sampling method and review fixes](docs/SAMPLING_QUALITY.md).

## Reports and rebuilding

- [REPORT.md](REPORT.md): cleaning counts, exclusions, sampling quality, workload pressure and known limits.
- [reports/sampling_quality.json](reports/sampling_quality.json): enforced limits and observed values.
- [reports/weighted_sampling_comparison.csv](reports/weighted_sampling_comparison.csv): full weighted arrival/mix profiles.
- [reports/validation.json](reports/validation.json): recorded full-source/output verification.
- [reports/reproducibility.json](reports/reproducibility.json): fresh-build comparison.
- [manifest.json](manifest.json): exact configuration, seed and input/output fingerprints.
- [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md): full reproduction commands and methodology.
- [../docs/RAW_DATA.md](../docs/RAW_DATA.md): optional raw-data download and extraction.

The prepared CSVs are sufficient for handoff. No raw-data processing or dependency installation is needed for the next teammate to begin.
