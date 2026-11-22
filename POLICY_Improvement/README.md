# Algorithm improvement experiment

**Historical experiment, excluded from active project scope.** The user removed
payback from consideration. Do not use these variants to evaluate the proposal or
run this experiment as part of the active project workflow. Code and outcomes are
preserved for provenance. The active comparison is
[LR-MMT versus CPU/memory-aware placement](../BASELINE_Comparison/reports/REPORT.md).

This package tests two changes to the scheduler on exactly the verified raw-derived
Alibaba inputs used in `RAW_Alibaba/reports`. It preserves the original results.

- **Tighter packing:** when incremental power ties, fill CPU/memory capacity more
  tightly rather than equalizing the two utilization fractions.
- **Migration payback:** only execute a proposed source-host group of moves when
  projected energy savings justify copying, waking and waiting for the source to
  sleep. Use current requests and elapsed age; never read future durations.

The fixed protocol is in `config.json`. It includes CPU-only and memory-aware
versions of the payback controller, so gains from the controller cannot be
misattributed to memory awareness. All candidate results are retained, including
negative results. These are in-sample algorithm development results.

Run from the repository root after independent raw-data preparation/validation:

```powershell
python -m unittest POLICY_Improvement.test_policies -v
python -m POLICY_Improvement.run --curve hpe_dl360_gen9
python -m POLICY_Improvement.run --curve huawei_rh2288h_v3
python -m POLICY_Improvement.run --curve quanta_d51b_2u
python -m POLICY_Improvement.report
```

Each of the three curves has 18 fresh simulator runs (three workload sizes times
six policies). The report checks all 54 outcomes, input/source hashes, completion
counts, and exact reproduction of 18 original CPU/memory baseline runs.

See [the complete results](reports/REPORT.md), [every comparison](reports/comparison.csv),
and [validation](reports/validation.json). Source-host proposal audits are retained
as `reports/runs/<curve>/<size>/<policy>/gate.json`.

## Observed verdict

The memory-aware payback variant wins 6/9 against the original CPU policy, up
from the original memory policy's 4/9. However, it loses 6.72–7.45% on the largest
workloads. Against CPU scheduling with the same payback controller, memory wins
only 3/9. Increasing the win count alone therefore does not establish a stronger
memory-aware scheduling claim.
Summing the nine fixed benchmark runs, original memory uses 4.20% more energy
than original CPU; memory with payback uses 4.89% more. This sum describes this
benchmark grid only, not a production workload distribution.

CPU-only payback wins energy in all nine cases (0.37–0.53%), with eight passing
the fixed waiting/pressure limits; the largest HPE case exceeds the pressure
limit. Tighter packing alone wins 1/9. Combining both changes wins energy in 3/9,
but all three exceed performance limits. None is a universal replacement for the
original policy. Keep these as evaluated development variants.

All 54 runs passed completion/provenance checks, 18 baseline cases reproduced
exactly, and all 58 unit/regression checks passed. These tests include tiny
analytical fixtures; the experiment workloads themselves are exclusively Alibaba.

The projection assumes current requests remain present for one 300-second control
interval. It is an estimate and can be wrong when tasks end or arrive. Waiting and
requested-resource pressure must therefore be assessed alongside energy. It does
not establish algorithmic novelty or prove savings across the full Alibaba trace.
