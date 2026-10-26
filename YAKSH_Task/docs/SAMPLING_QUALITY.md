# Sampling quality and review fixes

The review found two gaps: task-group counts could hide resource bursts, and a
quick validation run overwrote the saved full-source evidence. Both are addressed
in **data-v1.1.0**. The source trace, clean population, fixed 64 hosts, CPU/memory
units and simulator contract are unchanged. The selected workload rows changed.

## 1. Check the work that actually arrives

One group can represent one instance or thousands. Matching group counts in each
15-minute bin is insufficient to establish that a sample has similar demand.

The builder starts with the existing deterministic group quotas, then calibrates
the sample by swapping whole source rows inside the same time-bin/resource-skew
cell. It considers instance counts, CPU/memory requests and estimated CPU/memory
work, plus the resource mix. It never edits a source arrival, request, runtime or
`instance_num`. Group quotas stay fixed; multiplicity-band counts may change.
The seed, maximum passes and calibration penalty are recorded in the config.
This bounded deterministic search is a calibration heuristic, not a proof of an
optimal sample; the explicit acceptance checks decide whether its result is usable.

For a profile, total variation (TV) is half the sum of the absolute differences
between the normalized source and sample shares. **0 is identical; 1 is disjoint.**
Each profile is normalized separately, so this compares shape while allowing
different workload sizes. The reference is the cleaned completed-work population,
not every original production record.

| Profile | Maximum TV | Why it is checked |
|---|---:|---|
| Arrival bins, weighted by task groups | 0.10 | Preserve release timing at group level |
| Arrival bins, weighted by instances | 0.10 | Preserve multiplicity-weighted arrival bursts |
| Arrival bins, weighted by CPU or memory requests | 0.10 | Preserve arriving resource-demand mix over time |
| Arrival bins, weighted by CPU or memory work | 0.20 | Include estimated runtime as well as requests |
| Resource-skew classes, weighted by instances, CPU or memory requests | 0.05 | Avoid improving timing at the cost of a different resource mix |

Work equals `instance_num × request × duration_s`, assigned to the group's arrival
bin. It is an arrival-work profile, not a measured utilization curve. Its looser
bound accounts for the additional variability from estimated runtime and large
groups. These are declared project approximation limits, not external standards.
The group-skew quota also retains its original rounding bound, `3 / sample_size`.

The build fails on an exceeded limit. The independent validator recalculates every
profile from the saved CSVs and compares it with the manifest; it does not accept
the builder's reported metrics without checking them.

| Groups | Instance-arrival TV, before → after | CPU-request arrival TV, before → after | Memory-request arrival TV, before → after |
|---:|---:|---:|---:|
| 250 | 0.314 → 0.040 | 0.299 → 0.028 | 0.390 → 0.066 |
| 1,000 | 0.223 → 0.019 | 0.226 → 0.013 | 0.222 → 0.022 |
| 4,000 | 0.144 → 0.013 | 0.156 → 0.011 | 0.172 → 0.024 |

The full results, including work and skew distances, are in
[`reports/sampling_quality.json`](../reports/sampling_quality.json),
[`reports/weighted_sampling_comparison.csv`](../reports/weighted_sampling_comparison.csv)
and [REPORT.md](../REPORT.md). Peak demand remains a separate stress diagnostic.
Passing profile bounds does not establish exact burst peaks or exact production replay.

## 2. Keep verification evidence intact

The default command prints results and does not write files:

```sh
python3 YAKSH_Task/scripts/validate_data.py
```

To save a separate quick-check result:

```sh
python3 YAKSH_Task/scripts/validate_data.py --output /tmp/ecosched-check.json
```

Only an explicit full-source command should replace the recorded evidence:

```sh
python3 YAKSH_Task/scripts/validate_data.py --raw trace_201708 --archive trace_201708.tgz --output YAKSH_Task/reports/validation.json
```

Regression tests verify that a quick check leaves every package file unchanged,
that a separate output stays separate, and that altered reported quality metrics
are rejected. CI also checks that testing/validation leave tracked files unchanged.

## For the next teammate

Continue using the same host file and lazy instance loader. The 250-group workload
now expands to **40,381 instances**; the 1,000- and 4,000-group workloads expand to
**160,813** and **638,647**. Use the new manifest with every policy run. Results
from data-v1.0.0 use different sampled rows and should not be mixed into the same
controlled policy comparison.
