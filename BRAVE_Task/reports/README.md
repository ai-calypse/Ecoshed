# Verified integration runs

These are **first-fit simulator checks**, not LR-MMT research results. All runs use
the fixed 64-host pool, original instance counts and unchanged data handoff configs.
The summaries record resolved sleep/wake settings and input/implementation hashes.

| Task groups | Curve | Completed instances | Rejected / unfinished instances | Modeled kWh |
|---:|---|---:|---:|---:|
| 250 | HPE DL360 Gen9 | 40,381 | 0 / 0 | 9.382510 |
| 250 | Huawei RH2288H V3 | 40,381 | 0 / 0 | 9.157475 |
| 250 | QuantaGrid D51B-2U | 40,381 | 0 / 0 | 9.546205 |
| 1,000 | HPE DL360 Gen9 | 160,813 | 0 / 0 | 25.835535 |
| 4,000 | HPE DL360 Gen9 | 638,647 | 0 / 0 | 83.269500 |

The 250-group schedule is identical across the three curves: mean wait 8.281048 s,
maximum wait 10 s, peak 34 powered hosts. First-fit does not use watts to choose
placements, so changing the curve changes energy only. This equality was checked
against saved summaries. The 1,000/4,000-group maximum waits are 427.786370 s and
1,884.284970 s, respectively, confirming that queued work starts later and drains.

Validation completed locally with Python 3.14:

- **18 simulator unit tests passed**, including independent interval-by-interval
  capacity/energy checks and stop-and-copy migration accounting.
- **15 existing data-preparation tests passed**.
- **104 read-only prepared-data validation checks passed**. Raw source files were
  not re-downloaded; this is not a new full-source validation.
- All 250-group output CSVs reconciled to 40,381 unique instance outcomes with
  `finish >= start >= arrival`. Per-host joules sum to each result's total.
- All five summaries' implementation hashes match the checked-in Python sources;
  compilation checks passed for `ecosched/` and `tests/`.

Reproduce the small runs with `python -m ecosched --all-curves` from repository
root. For each larger input, run
`python -m ecosched --config YAKSH_Task/config/experiment_1000.json` (or `4000`).
The runner writes full CSVs under ignored `BRAVE_Task/results/`; this directory
retains only compact summaries for review.
