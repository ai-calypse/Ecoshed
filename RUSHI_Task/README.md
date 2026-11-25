# Rushi's task: memory-aware placement analysis (D5)

**Owner:** Rushi Jhala. **Deliverable:** D5 from section 5 of
[the proposal](../docs/EcoSched_Proposal.pdf): analysis of CPU+memory-aware
placement, resource-skew (task type) breakdown and result sanity checks.

Rohan implemented the proposed policy (`lr_mmt_memory` in
[`ROHAN_Task/policies.py`](../ROHAN_Task/policies.py)) and Brave ran it in the
36-run comparison ([`BASELINE_Comparison`](../BASELINE_Comparison/reports/REPORT.md)).
That comparison showed **what** happened: the proposed placement saves energy in
4/9 cases but uses 10.96–14.56% more on the largest workload. This folder explains
**why**. Nothing here changes a workload, policy or simulator setting, and no new
policy variant is added (AGENTS.md scope).

Full results: **[reports/REPORT.md](reports/REPORT.md)**.

## What I found

1. **Result.** The proposed placement saves energy in 4/9 cases: all three 250-group
   cases and the 1,000-group Huawei case, by only 0.06–0.59%. On the largest workload
   (4,000 groups) it uses **10.96–14.56% more** energy on every curve.
2. **Where the extra energy goes.** On the largest workload, about **88%** of the extra
   kWh is servers kept switched on **while running work** (about 106 extra server-hours
   on the HPE curve). Servers idling contribute about 0%. Load-dependent power adds 24%,
   and fewer wake-ups give back 12%. The split is exact, not estimated.
3. **Why: the score arithmetic.** Waking a sleeping server costs 0.17–0.20 in Rohan's
   score. The balance term (at most 0.25) could only justify that with a 69–80-point
   balance gain, so the proposed policy wakes servers **less** often (1,122 vs 1,974
   wake-ups, HPE). But a busy server here sits at about 30% CPU and 57% memory, so it is
   memory-heavy. For a typical tiny task (0.78% of a server's CPU), its balance penalty
   is 7–9× larger than its power advantage, so the proposed rule sends tasks to emptier
   servers.
4. **Evidence from every placement decision** (378,285 per run). When the two rules
   disagree, the proposed policy picks the less-loaded server 62% of the time, against
   17% for CPU-only (HPE, largest workload). On average 32.5 servers are on instead of
   24.2, at 21% instead of 30% CPU load. The consolidation controller works twice as hard
   (931 vs 464 hosts planned for evacuation) but cannot undo the spreading.
5. **By task type (the proposal's question).** Memory-heavy tasks gain the most: the
   share that had to wait drops from 41.8% to 25.2% (balanced tasks: 52.8% to 38.5%,
   HPE), mostly because fewer tasks wait for a server to wake up. Mean waits change by at
   most 1.8 s, and P95 waits barely move. At 250 and 1,000 groups every wait is a 10 s
   wake-up wait.
6. **Trade-off.** On the largest workload the proposed placement lowers fragmentation
   (0.0198 → 0.0086, HPE), overload pressure (18.5% → 14.1%) and mean wait (−1.6 s), at
   the cost of 11–15% more energy. It does what it was designed to do, but in this
   simulator energy is driven by how many servers are on, so it does not deliver
   consistent energy savings.

## What I did, step by step, and why

| Step | What | Why | How it was checked |
|---|---|---|---|
| 1 | Rebuilt the prepared inputs from the team's `data-v1.0.0` release archive (`trace_201708.tgz`) with the unchanged `RAW_Alibaba.extract` and `RAW_Alibaba.prepare`, writing outside the repo | The prepared CSVs are git-ignored, and re-recording decisions needs them | The archive matches Alibaba's published SHA-256. All six raw CSVs and all five prepared CSVs match the committed fingerprints byte-for-byte, and `RAW_Alibaba.verify_data` passed |
| 2 | Split each run's energy into the states the simulator charges for: asleep, waking, on with work, on without work, plus load-dependent power ([`accounting.py`](accounting.py)) | To say where the extra kWh come from without any modelling assumption | Every split adds up exactly to the simulator's own total (unit tests, plus a check inside every call) |
| 3 | Worked through Rohan's placement score with the real SPECpower curves and the real median task size | To explain the mechanism, not just describe it | Unit tests compare the formulas with `LRMMT._score` itself |
| 4 | Wrapped the real policy in a read-only recorder ([`observer.py`](observer.py)) and re-ran the primary pair: 3 sizes × 3 curves × 2 policies = 18 runs ([`rerun.py`](rerun.py)) | To see every placement decision, plus what the other rule would have picked from the same snapshot | All 18 re-runs reproduce their committed `RAW_Alibaba` summaries field for field. Recomputing each choice found 0 mismatches, so the recorder changed nothing |
| 5 | Broke waits and migrations down by task type (balanced / memory-heavy / CPU-heavy, the labels from `RAW_Alibaba/prepare.py`) | This is the proposal's research question | Instance counts per type equal the manifest's counts |
| 6 | Wrote 11 tests ([`tests/`](tests/test_analysis.py)) | So the next person can trust and rebuild the numbers | `python -m unittest discover -s RUSHI_Task/tests -v` |

## Files for the next teammate (D6: report, slides, demo)

| File | What it shows | Use it for |
|---|---|---|
| [reports/REPORT.md](reports/REPORT.md) | Full D5 write-up with every table | Final report, results/analysis section |
| [reports/energy_gap_breakdown.svg](reports/energy_gap_breakdown.svg) | Where the extra energy goes on the largest workload | Main results slide |
| [reports/servers_over_time.svg](reports/servers_over_time.svg) | Servers on over the 12 hours, and their CPU load | "Why" slide |
| [reports/who_picks_the_emptier_server.svg](reports/who_picks_the_emptier_server.svg) | When the rules disagree, which server each picks | "Why" slide |
| [reports/wait_by_task_type.svg](reports/wait_by_task_type.svg) | Mean wait for balanced / memory-heavy / CPU-heavy tasks | Research-question slide |
| [reports/pair_energy_gap.csv](reports/pair_energy_gap.csv) | The energy split for all 9 cases | Report table |
| [reports/tradeoffs.csv](reports/tradeoffs.csv) | Energy vs wait, pressure, migrations and fragmentation | Trade-off discussion |
| [reports/placement_decisions.csv](reports/placement_decisions.csv), [placement_load_bands.csv](reports/placement_load_bands.csv) | Where tasks were placed, and how loaded the chosen server was | Backup slide |
| [reports/outcomes_by_task_type.csv](reports/outcomes_by_task_type.csv) | Waits and migrations by task type, all 18 runs | Report table |
| [reports/runs/](reports/runs/) | Compact recording per re-run (decisions, time series, per-type outcomes) | Kafka/dashboard demo data source |
| [reports/validation.json](reports/validation.json) | Every check this analysis ran | Reproducibility appendix |

## Run

From the repository root (Python 3.10+, standard library only):

```sh
python -m unittest discover -s RUSHI_Task/tests -v
python -m RUSHI_Task.analyze      # rebuilds reports/ from committed files; no archive needed
```

Re-recording decisions needs the prepared inputs (about 20 minutes for all 18 runs):

```sh
gh release download data-v1.0.0 -R ai-calypse/Ecoshed -p trace_201708.tgz -D ../EcoshedData/archive
python -m RAW_Alibaba.extract --archive ../EcoshedData/archive/trace_201708.tgz --output ../EcoshedData/raw
python -m RAW_Alibaba.prepare --raw ../EcoshedData/raw --output ../EcoshedData/prepared
cp ../EcoshedData/prepared/*.csv RAW_Alibaba/prepared/     # git-ignored; keep the committed manifest.json
python -m RUSHI_Task.rerun
python -m RUSHI_Task.analyze
```

Passing `--output` keeps `extract` from overwriting the committed `RAW_Alibaba/archive_audit.json`.

## Notes for Brave (repo housekeeping, not changed here)

1. `RAW_Alibaba/prepared/manifest.json` hashes to `91de65a6…`, but all 54 committed
   summaries and `RAW_Alibaba/data_validation.json` record `110e6497…`. The two
   manifests differ only in the archive name and fingerprint; the prepared CSVs
   match the committed manifest. Because of this, `python -m BASELINE_Comparison.build`
   and `python -m RAW_Alibaba.run` stop with a validation error on a fresh clone,
   even after the inputs are prepared. Committing the `110e6497…` manifest would fix
   it, or re-running `verify_data`, `RAW_Alibaba.run`/`verify` and the baseline build.
2. `BASELINE_Comparison/reports/validation.json` records the summaries hash
   `b64f374f…`, but the committed `RAW_Alibaba/reports/summaries.json` is
   `479d3c44…`. The 36 rows are identical to `BASELINE_Comparison/reports/summaries.json`,
   so only the recorded hash is stale.

This analysis checks content equality instead of those two hashes and reports both
in [reports/validation.json](reports/validation.json).

## Open questions for the team

- **Balance weight.** The analysis keeps the implemented weight of 0.25. A small
  sensitivity check (for example 0, 0.05 and 0.1; weight 0 must reproduce `lr_mmt`)
  would test the mechanism directly. AGENTS.md currently excludes new placement
  variants and the core freeze applies, so it was not run. It needs the team's OK,
  and the result would have to be labelled as tuned on the same data.
- **Untouched samples** (midterm plan, D4) are outside this D5 analysis.

## Limits

Simulation estimates from requested resources and whole-server SPECpower curves,
not measured Alibaba electricity. The nine cases overlap and are deterministic,
so they are not independent replications. Energy is charged per server, so it is
not split by task type; waits and migrations are. See the Limits section of
[reports/REPORT.md](reports/REPORT.md).
