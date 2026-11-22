# Rohan's task: scheduling policies and consolidation

**Owner:** Rohan Rane. **Deliverable:** D3, section 5 of the
[proposal](../docs/EcoSched_Proposal.pdf): LR-MMT, LR-MMT with CPU/memory-aware
placement, baseline heuristics, consolidation and migration decisions.

This folder contains runnable policy implementations, tests, experiment settings,
results and the policy handoff. It directly imports **Yaksh's workload loader and
prepared data** and **Brave's simulator and three power curves**. Those components
are reused without changing their code or input files. Python 3.10+ and the
standard library are sufficient.

## Run

From the repository root (`Ecoshed-main` after extracting the GitHub ZIP):

```sh
# Policy tests
python -m unittest discover -s ROHAN_Task/tests -v

# Small comparison: four policies, 250 groups, primary HPE curve
python -m ROHAN_Task.run --sizes 250 --curves hpe_dl360_gen9

# Full matrix: 3 sizes x 3 power curves x 4 policies = 36 runs
python -m ROHAN_Task.run

# Reconcile the complete matrix and create compact reports
python -m ROHAN_Task.verify
```

Use `--policies lr_mmt lr_mmt_memory` for the main comparison, `--sizes 1000` for
the medium workload, or `--details` to also save instance and host-sample CSVs.
`--output <directory>` selects a separate destination. Repeating a run replaces
its output files. The aggregate `comparison.csv` reflects the selected invocation.
The verifier recursively combines disjoint result partitions, so the three curves
can also be run separately under different output subdirectories.

See [the result report](REPORT.md), [comparison.csv](reports/comparison.csv) and
[machine-readable validation](reports/validation.json) for the completed matrix.
Full migration/decision logs stay under ignored `results/`; the compact reports
are retained for review.

## Files and ownership

| File | Purpose |
|---|---|
| [policies.py](policies.py) | LR detector, MMT selector, safe migration planner and baseline |
| [run.py](run.py) | Integration runner using existing data configs and engine |
| [verify.py](verify.py) | Matrix coverage, shared settings and provenance verification |
| [config/default.json](config/default.json) | Explicit, common experimental settings |
| [tests/test_policies.py](tests/test_policies.py) | Policy and simulator integration tests |
| [reports/](reports/) | Results for all completed comparisons |
| [../ecosched/](../ecosched/) | Brave's shared simulator; no duplicate engine |
| [../YAKSH_Task/](../YAKSH_Task/) | Original inputs and lazy instance expansion |

## Implemented policies

| Policy ID | Placement | Controller |
|---|---|---|
| `first_fit` | Brave's powered-host-first first fit | None |
| `best_fit` | Pack fullest feasible CPU host, preferring powered hosts | None |
| `lr_mmt` | Smallest incremental steady-state server power | Shared LR/MMT + evacuation |
| `lr_mmt_memory` | Same power score plus CPU/memory imbalance penalty | Identical shared controller |

All four use the engine's same strict FIFO admission, independent instances,
physical CPU/memory capacity limits, power integration, sleep/wake settings and
full-window-plus-drain stopping rule. Both LR-MMT variants use one implementation
with a `memory_aware` flag. Only the destination/placement score changes. The
baselines intentionally have no consolidation controller, so their comparison
includes both placement and migration overhead; the primary pair is the placement
ablation.

For request `r` and host `h`, let `u_cpu` and `u_mem` be the **post-placement**
fractions. The CPU score is
`(P(u_cpu) - P_before) / max(1, P_full - P_idle)`.
`P_before` is active CPU power for powered hosts and modeled sleep watts for a
sleeping host. The memory-aware score adds
`0.25 * abs(u_cpu - u_mem)`. This favors balanced resource occupancy while retaining
the energy term. Both variants enforce memory feasibility, even when the score
uses CPU alone. Ties use the stable host ID. The score approximates steady-state
incremental watts; Brave's engine accounts for actual wake and transfer energy.

This is an **online, batch-instance adaptation** of LR-MMT with power-aware
placement. FIFO arrival admission does not sort an offline VM batch in decreasing
CPU order, so the placement rule is not an exact PABFD implementation. The
CPU/memory score is an explicit project heuristic, not a claimed reproduction of
Tetris or Li et al.'s algorithm. Rushi can tune or replace this score while holding
the common controller and simulator fixed.

## Local regression and migration selection

The controller samples aggregate requested CPU at each 300-second engine tick.
It keeps the last 10 samples per host. During warmup it uses a 0.9 CPU threshold.
Thereafter it fits a tricube-weighted local straight line and extrapolates at least
one interval, or enough intervals to cover the largest resident instance's modeled
copy time. The CPU forecast is multiplied by 1.2. Forecast at or above 1 indicates
overload. A static 0.9 memory guard applies to both policies at every tick.

When trying hypothetical removals/additions, adjust the forecast by the change
from the latest sampled CPU load. Predictions use only past/current reservations,
never observed future usage or an instance's private duration/completion time.
LR therefore models scheduler-induced aggregate changes in this workload; it does
not recover empirical per-instance CPU histories.

On an overloaded host, choose eligible instances in **Minimum Migration Time**
order: smallest normalized memory first, with stable instance-ID ties. A common
conversion and bandwidth make that equivalent to smallest modeled copy time.
Continue until projected pressure is relieved, no safe destination exists, or the
256-migrations-per-tick budget is reached. Destination reservations must fit both
resources and pass the same pressure guard. New arrival placement can use full
physical capacity; it does not apply a different queue/rejection threshold.

The conceptual reference is Beloglazov & Buyya, *CCPE* 2012,
[doi:10.1002/cpe.1867](https://doi.org/10.1002/cpe.1867), and CloudSim's
[LR controller documentation/source](https://github.com/Cloudslab/cloudsim/blob/master/modules/cloudsim/src/main/java/org/cloudbus/cloudsim/power/PowerVmAllocationPolicyMigrationLocalRegression.java).
The regression implementation here is independent and uses explicit positive
tricube weights; it is not a bit-for-bit port of CloudSim's numerical helper.

## Consolidation safeguards

Hosts below 0.3 on **both** resource fractions can be evacuated. Consider the
least CPU-loaded first and try their residents in decreasing CPU order. Every
resident must fit an existing active recipient; otherwise roll back the whole
tentative evacuation. Underload consolidation never wakes a new host. Brave's
normal idle timer puts an emptied source to sleep.

Planning maintains a physical shadow of destination reservations. It does not
credit source releases before copying ends. A host chosen as a destination cannot
also be evacuated in the same tick, and overloaded/source/locked hosts cannot be
destinations. In-flight/waking instances cannot migrate. Transfer endpoints stay
locked through a conservative transfer bound, and each migrated instance has a
600-second cooldown after that bound. A draining host is avoided for new arrivals
where other capacity exists; if it is the only physical fit, admission still uses
it to preserve the common FIFO feasibility rule.

These safeguards prevent conflicting plans and partial underload evacuation.
They cannot guarantee savings: a migrated batch instance may finish soon after
transfer, and the policy deliberately has no access to that future runtime.

## Explicit experimental assumptions

The data supplies normalized memory, not bytes. These runs assume **one normalized
unit = 64 GiB**, **125,000,000 bytes/s per concurrent transfer**, and no extra
migration watts beyond Brave's source/destination reservation power. The conversion
is an experimental setting, not a measured Alibaba value or a calibration from
SPEC's 64-GB RAM. It does not replace host memory capacities. Migration uses
Brave's stop-and-copy pause and completion extension. Different RAM conversion or
bandwidth can change the policy ranking and should be part of later sensitivity
analysis.

The unchanged engine defaults include 5-W sleep, a 60-second idle timeout and
10-second full-power wakeup. HPE DL360 Gen9 is primary; Huawei RH2288H V3 and
QuantaGrid D51B-2U are the alternative measured curves. Each run records the full
resolved engine settings, policy parameters, source/input/config fingerprints,
assumptions, and validation results. A fresh engine and policy are created for
every run. The experiment team can extend the matrix using the same interfaces.

## Validation and limits

Tests check LR's known constant/linear solutions, fallback and forecast adjustment,
MMT ordering, the isolated placement-score change, CPU/memory feasibility, shadow
reservations, transactional rollback, cooldown, migration budgets and integration
with Brave's actual completion/energy events. Runtime inputs remain invisible to
policies. Run validation checks every outcome ID and start/finish ordering,
sampled capacity, drained reservations, counts and energy sums. Matrix verification
checks all 36 unique combinations and shared settings/source hashes.

Energy is modeled; overload is Brave's reservation-pressure proxy, not measured
SLA failures. Report queueing and migration pause alongside kWh. A positive energy
reduction percentage means savings; a negative value means the policy used more
energy. Deterministic workload replays do not supply statistical confidence
intervals or establish production savings. Kafka, dashboards, final statistical
analysis and presentation remain the experiment/presentation team's work.
