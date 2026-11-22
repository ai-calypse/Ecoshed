# Brave's task: simulator and power model

**Owner:** Brave Desai. **Deliverable:** D2 from section 5 of
[the proposal](../docs/EcoSched_Proposal.pdf): host/job state, event engine,
SPECpower interpolation and integration, sleep model, common metrics, unit tests.

The implementation is in [`ecosched/`](../ecosched/). It uses Yaksh's existing
`iter_instances()` adapter and the unchanged prepared CSV/config files. Python
3.10+ and the standard library are sufficient. Run commands from the repository
root (`Ecoshed-main` if extracted from the GitHub ZIP).

## Run and verify

```sh
python -m unittest discover -s tests -v
python -m ecosched
python -m ecosched --all-curves
python -m ecosched --config YAKSH_Task/config/experiment_1000.json --curve huawei_rh2288h_v3
python -m ecosched --config YAKSH_Task/config/experiment_4000.json --curve quanta_d51b_2u
```

Default: 250 task groups, 64 hosts, first-fit placement and HPE power. `--all-curves`
replays the same inputs separately with each of the three curves. First-fit
provides a working integration baseline. LR-MMT, the memory-aware extension,
consolidation decisions and research comparisons are D3 work for the policy team.

Each run writes `results/<workload>/<curve>/` containing:

- `summary.json`: counts, timing, energy, host metrics, complete simulator
  settings, input/config/curve/source SHA-256 hashes, and data-manifest hash.
- `instances.csv`: one completed/rejected outcome per arrived instance, including
  start/finish/wait times and resource requests for completions.
- `host_samples.csv`: per-host reservations, state and watts at control intervals.
- `migrations.csv`: source/destination, transfer start/end, pause and extra joules;
  empty when no migrations were requested.

Use `--output <directory>` to change the destination. Reusing an output path
replaces that run's files. Large generated logs are ignored by Git; compact
integration summaries are retained in [`reports/`](reports/).

## Engine and queue contract

Every group expands to its original `instance_num` **independent instances** with
stable IDs. There is no gang scheduling. Requests reserve both CPU cores and
normalized memory; runtime starts at the actual start, after queuing and wakeup.
Original placements and observed future CPU/memory statistics are never passed to
policies. Hosts start asleep unless sleep is disabled.

Arrivals must be ordered. Duplicate IDs, invalid demands/runtimes, unsupported
experiment assumptions, unknown host choices and policy overcommit fail explicitly.
An instance that cannot fit any physical host is rejected. Other instances enter
one strict FIFO queue; the head can block smaller followers. This common admission
rule is independent of placement. A policy that defers the last feasible queued
work with no executing work raises an error instead of hanging forever.

At equal timestamps the engine processes completions, transfer finishes and wakes,
then arrivals, FIFO dispatch, the controller, and finally sleep timers. New work
cancels old idle timers. Intervals between events have constant reserved load,
so energy is exactly `watts * seconds` on each interval; watts are never averaged
across a discontinuous placement event.

Accept arrivals in `[0, arrival_window_s)` and stop at
`max(arrival_window_s, last actual completion)`. Account for idle/sleep power over
the entire window and include drain time. Sleep timers and stale completion events
cannot extend a fully drained run beyond that rule. Source failures and online
background utilization are not replayed.

## Three measured power curves

The checked-in [curve file](../ecosched/power_curves.json) records all 11 published
whole-server AC measurements at **target loads** 0, 10, ..., 100%. At zero use
SPEC's **Active Idle**, which is distinct from sleep. Interpolate linearly between
target loads using `reserved_cpu_cores / source_host_cpu_capacity`.

| CLI curve ID | Role / SPEC result | Idle W | Full W |
|---|---|---:|---:|
| `hpe_dl360_gen9` | Primary / [20151215-00708](https://www.spec.org/power_ssj2008/results/res2016q1/power_ssj2008-20151215-00708.html) | 45.0 | 276 |
| `huawei_rh2288h_v3` | Secondary / [20150829-00703](https://www.spec.org/power_ssj2008/results/res2015q3/power_ssj2008-20150829-00703.html) | 44.8 | 266 |
| `quanta_d51b_2u` | Third / [20141124-00679](https://www.spec.org/power_ssj2008/results/res2014q4/power_ssj2008-20141124-00679.html) | 49.6 | 272 |

These SPEC systems each have 2 sockets, 36 enabled cores, 72 hardware threads and
64 GB RAM. Hardware availability is November 2015, May 2015 and September 2014,
respectively. HPE's result was published January 7, 2016, hence its `res2016q1` URL.

Apply one selected curve uniformly to all 64 sampled hosts per run. Preserve
Alibaba host capacities and normalized memory; do not replace them with the SPEC
configuration or scale power by core count. This is a common surrogate power
model and a sensitivity study, not calibration of Alibaba servers. CPU drives
the power lookup; memory constrains placement but does not introduce an invented
memory-power component. CPU demand is a constant request model, not measured
time-varying utilization. Results are **modeled energy**, not production electricity.

## Sleep and migration assumptions

`SimulationConfig` defaults are explicit modeling choices, not SPEC measurements:

| Setting | Default | Meaning |
|---|---:|---|
| `idle_timeout_s` | 60 | Sleep after uninterrupted idle; `null` keeps every host on |
| `sleep_watts` | 5 | Whole-server modeled sleeping power |
| `wake_latency_s` | 10 | Reserve capacity immediately; execution waits for host readiness |
| `wake_energy_j` | 0 | Optional extra transition joules, added once per wake |
| `control_interval_s` | 300 | Sample host state and call the optional policy controller |
| `overload_threshold` | 0.9 | CPU **or** memory reservation fraction above this threshold |
| `memory_unit_bytes` | `null` | Explicit bytes per normalized memory unit; required for migration |
| `migration_bandwidth_bytes_s` | 125000000 | Assumed transfer bandwidth, only used if migration requested |
| `migration_extra_watts` | 0 | Extra transfer power beyond the two hosts' modeled power |

Waking power is conservatively the selected curve's full-load watts. A disabled
sleep model starts all hosts active. To override settings, copy a prepared config,
fix its relative `hosts`/`workload` paths and add a `simulator` object containing
the settings above, or construct `SimulationConfig` in Python. Every resolved
setting is saved with results; hold them fixed across policies.

Migration uses an explicit **stop-and-copy approximation**. Reserve destination
CPU/memory while retaining the source reservation. Pause the instance until the
destination is awake and `request_memory * memory_unit_bytes / bandwidth` seconds
of copying finish. Release the source, retain the destination, and extend completion
by the pause, invalidating the original completion event. Both hosts are charged
their reserved-load power during transfer; optional extra watts apply during
copying, once per transfer. Concurrent transfers each receive the configured
bandwidth (no shared-link contention). Migration time is not inferred from an
assumed GB conversion. A policy requesting migration without a conversion fails.

## Policy-team integration

```python
from ecosched import Migration, Simulator
from ecosched.__main__ import load_experiment
from ecosched.policies import FirstFit
from YAKSH_Task.scripts.load_workload import iter_instances

class MyPolicy(FirstFit):
    name = "my_policy"

    def select_host(self, request, hosts, now):
        # Immutable Request: ID, group, CPU, memory, arrival; no runtime.
        # Immutable HostView: capacities, reservations, state; .fits(request).
        return super().select_host(request, hosts, now)

    def on_tick(self, now, hosts, running):
        # Keep your own past utilization history for LR. RunningView exposes
        # request, host_id, actual scheduled start and state, not completion.
        # Return [Migration(instance_id, destination_host_id), ...] if desired.
        return []

hosts, workload, settings, provenance = load_experiment("YAKSH_Task/config/experiment_250.json")
engine = Simulator(hosts, settings, policy=MyPolicy())
summary = engine.run(iter_instances(workload))
```

Implement the shared LR detector/MMT selector and the two placement rules behind
this interface. `select_host` can select sleeping/waking hosts; the engine handles
readiness. Use a fresh engine and policy instance for every experiment. A rejected
migration/placement plan raises an error; it is not silently counted as successful.

## Metric definitions and verification

Energy: `kWh = joules / 3,600,000`. Report both Wh/completed **instance** and
Wh/completed **task group**; the latter counts a group only if all declared
arrived instances completed. A zero denominator produces JSON `null`. A rejected
group is included in unfinished groups. Rejected and unfinished instance counts
are separate; successful draining gives zero unfinished instances.

Wait is actual start minus arrival, including wake delay. Queue-instance-seconds
counts only time before dispatch; wake delay is represented in wait metrics.
Active-host-seconds includes waking hosts; busy-host-seconds includes reservations.
Overload is a time integral of hosts whose CPU **or** memory reservation exceeds
the configured threshold, including reservations during wake/migration. It is a
**pressure proxy**, not observed SLA failures. Physical overcommit is prohibited.
The overload fraction denominator is all hosts times the full simulated duration.
`peak_queue_before_dispatch` includes newly arrived work before scheduling it.
Migration pause and extra energy are reported separately; extra energy is already
included in total energy. No energy-saving percentage is meaningful until the
experiment team supplies a same-workload baseline and computes
`100 * (baseline_kwh - policy_kwh) / baseline_kwh`.

The unit suite includes independent analytical joule calculations, migration
completion invalidation, FIFO behavior, memory bottlenecks, horizon boundaries,
invalid inputs, reproducibility, and a randomized trace whose recorded intervals
are independently audited for CPU/memory capacity and integrated energy. The
GitHub workflow also replays the 250-group input under all three curves. Existing
data tests and the read-only validator remain separate.
