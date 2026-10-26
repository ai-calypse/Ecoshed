# EcoSched: Yaksh's data and sampling deliverable (D1)

This package completes the **Data & sampling** assignment in section 5 and the
**D1 reproducible workload package** in section 6 of the EcoSched AMS 560 proposal.
It contains the runnable preparation code, cleaned CSV inputs, a fixed mini-cluster,
three reproducible workloads, source fingerprints, validation and a data report.

Start with [REPORT.md](../REPORT.md) for the actual counts, exclusions and sampling
quality. Use [SIMULATOR_HANDOFF.md](SIMULATOR_HANDOFF.md) for integration.

## Ready-to-use files

| File | Use |
|---|---|
| `data/hosts_64.csv` | Identical fixed host pool for every scheduling policy and workload size |
| `data/workload_250.csv` | Small replay, 250 task groups; preserve `instance_num` |
| `data/workload_1000.csv` | Medium replay, 1,000 task groups |
| `data/workload_4000.csv` | Large replay, 4,000 task groups; inspect offered-load stress in the report |
| `data/tasks_clean.csv` | Entire eligible population for the configured batch window |
| `data/hosts_all.csv` | Clean inventory for all 1,313 original machines |
| `data/host_usage_sample.csv` | Observed utilization for selected source machines; characterization only |
| `data/host_events.csv` | Source host failures, retained for optional future experiments |
| `config/experiment_*.json` | Paths and model assumptions for each handoff |
| `manifest.json` | Seed, config, input/output SHA-256 fingerprints, and workload metrics |
| `reports/audit.json` | Full-file audit of all six source CSVs and exclusion counts |
| `reports/validation.json` | Independent saved-output verification results |
| `reports/*comparison.csv`, `arrival_profile.csv` | Population/sample representativeness evidence |

**No external Python packages are required. Python 3.10+ is sufficient.** The CSVs
are the proposal's allowed cleaned CSV format; no duplicate Parquet files are needed.
Raw data remains untouched in the parent `trace_201708` directory and is not copied
into this handoff package.

## Reproduce

Run from the proposal directory:

```sh
python3 YAKSH_Task/scripts/build_data.py
python3 YAKSH_Task/scripts/test_sampling.py
python3 YAKSH_Task/scripts/validate_data.py --raw trace_201708 --archive trace_201708.tgz
python3 YAKSH_Task/scripts/make_report.py
```

For another location, pass `--raw /path/to/trace_201708`, `--archive /path/to/trace_201708.tgz`,
`--output /path/to/new-output` and optionally `--config /path/to/config.json` to the builder.
The builder creates the data/report/config/schema files; copy `scripts/` and this
documentation as well if relocating the full package. Run the validator with
`--root /path/to/full-package`. It expects the package's builder source to be present.
Use a fresh output directory for a changed config so old experiment files cannot
be mistaken for current outputs. To regenerate the report elsewhere, pass
`--root /path/to/full-package` to `make_report.py`.

The full build streams the 819 MiB instance table once and retains only task-level
statistics. It does not materialize millions of instances or duplicate the raw trace.
The validator optionally streams the archive to confirm every extracted input is
identical to the checksummed release. It also checks all generated data fingerprints.

The supplied outputs were also compared with a fresh build in a separate directory.
To repeat that check, build with a fresh `--output /tmp/ecosched-fresh`, then run
`python3 YAKSH_Task/scripts/compare_builds.py YAKSH_Task /tmp/ecosched-fresh`.
Regenerate `REPORT.md` afterwards to include the comparison result.

To exercise the simulator adapter without writing expanded files:

```sh
python3 YAKSH_Task/scripts/load_workload.py YAKSH_Task/data/workload_250.csv
```

## Decisions that matter

- **Version:** Alibaba v2017. The proposal's `machine_meta` reference is a v2018
  filename; v2017 host capacities come from `server_event.csv`.
- **Window:** batch arrivals and completed records in `[0, 43200)` seconds, with
  task/instance completion allowed at 43200. This is an explicit first-12-hours
  batch experiment. The source files span different periods; the later server
  utilization samples are used for host characterization, not a simultaneous
  background-load replay. This avoids pretending unavailable observations are zero.
- **CPU:** divide raw batch `plan_cpu` by 100. The v2017 maintainer confirmed this
  correction in [issue 11](https://github.com/alibaba/clusterdata/issues/11).
  Host CPU capacity and actual instance CPU measurements are already in cores.
- **Memory:** retain the original normalized units for both host capacity and task
  request. Do not divide these fields by 100 or invent a RAM size in GB.
- **Runtime:** arithmetic mean of valid completed first-attempt instance runtimes,
  grouped by `(job_id, task_id)`. It is an explicit approximation, not the task's
  end-minus-arrival interval. Raw interval bounds and coverage are retained.
- **Multiplicity:** one task-group row represents `instance_num` independent
  schedulable instances. The adapter expands them lazily. Do not treat a whole
  task group as a single VM or require all instances to fit one host.
- **Demand:** constant requested CPU/memory per instance. Missing measured usage
  is retained as missing; no memory values are filled with zero or fabricated.
- **Sampling:** seed 560; host strata combine rounded capacity and mean CPU/memory
  utilization quartile bands, reserving at least one host per rounded capacity
  class so rare host types remain present. Workload sampling enforces resource-skew proportions,
  then allocates by 15-minute arrival bin and instance-count band using largest
  remainders; stable SHA-256 ranks choose rows within cells. Sizes are independent
  fixed samples, not guaranteed nested. Arrival timestamps and multiplicities are
  unchanged. Sampling preserves task-group proportions approximately; inspect
  instance-weighted differences and load peaks as well.
- **Fairness:** compare policies using the same files, no original placements,
  no replayed online load or host failures by default. No energy or scheduler
  performance claims are produced by this data package.

## Scope and sources

Yaksh completed this data and sampling assignment. The simulator/power model (Brave), scheduling policies
(Rohan), memory-aware extension and experiment analysis (Rushi), and experiment
pipeline/presentation (Yaksh) are separate D2-D6 work. Configuration handoffs here
do not implement those components. The data is ready for their integration.

Source: [Alibaba Cluster Trace Program](https://github.com/alibaba/clusterdata),
[v2017 schema](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2017/schema.csv),
[trace description](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2017/trace_201708.md),
[published SHA-256](https://raw.githubusercontent.com/alibaba/clusterdata/master/cluster-trace-v2017/SHA256SUM).
Copies of these source documents and the CPU clarification are in `docs/upstream/`.
The raw download is for academic/research use under the publisher's stated terms.
