# Simulator handoff and data dictionary

## Contract

Load `hosts_64.csv` once. For each experiment, replay one workload in ascending
`arrival_time_s`. For each group create exactly `instance_num` independent instances
with identical resource requests and the modeled `duration_s`. Assign each instance
its own stable synthetic ID; `scripts/load_workload.py` provides this iterator.
Queue/reject/placement rules belong to the simulator and must be shared across policies.
No scheduling policy should consult original host placements or future observed
usage/completion data. The engine uses runtime to generate a completion event only
after an instance starts; queuing shifts its completion time.

Task groups are compact storage, not gang scheduling units. For example, raw
CPU 50 with `instance_num=100` means 100 instances at 0.5 cores each, totaling
50 requested cores when concurrent. Resource counters must multiply by instance
count; Wh/task reporting must clearly distinguish completed instances from task
groups. A task group completes only when all its instances complete.

Default experiments have no background online load or source failures. Source
utilization already includes all workloads; adding it to replayed batch demand
would double-count usage. Later source utilization is not a time-varying demand
trace for these newly scheduled instances.

Process all arrivals before the configured horizon and then drain outstanding work.
Integrate energy to the same declared stopping rule across policies, include drain
time, and report unfinished/rejected instances explicitly. The offered-load metrics
in this package assume immediate start and serve only as demand diagnostics; they
are not simulated overload/SLA results. Peak aggregate demand above pool capacity
implies a burst must queue or reject under non-overcommit scheduling.

## Workload columns

| Column | Meaning |
|---|---|
| `task_group_id` | Stable derived key `j<job_id>_t<task_id>` |
| `job_id`, `task_id` | Source join keys; keep both |
| `instance_num` | Original declared number of instances, never downscaled |
| `arrival_time_s` | Task create time minus configured window start, seconds |
| `source_create_timestamp_s`, `source_modify_timestamp_s` | Original source task bounds |
| `source_status` | `Terminated` for the primary population |
| `source_row` | 1-based row in raw `batch_task.csv` |
| `plan_cpu_raw` | Unmodified raw batch CPU request |
| `cpu_request_cores` | Per-instance request, `plan_cpu_raw / 100` |
| `memory_request_normalized` | Per-instance request in source normalized memory units |
| `duration_s` | Mean valid completed first-attempt duration for this group |
| `duration_min_s`, `duration_max_s` | Range of contributing observed durations |
| `duration_observations` | Number of contributing source records |
| `duration_observation_coverage` | Observations / original `instance_num`; not an imputed completeness claim |
| `actual_cpu_mean_observed`, `actual_memory_mean_observed` | Means over available nonnegative finite per-instance averages; blank when unavailable |
| `actual_cpu_observations`, `actual_memory_observations` | Nonmissing counts contributing to those descriptive means |
| `resource_skew` | Request fraction ratio relative to median sampled host capacity |
| `time_bin` | `floor(arrival_time_s / 900)` |
| `multiplicity_band` | `1`, `2-100`, `101-1000`, or `1001+` |

Let `r = (cpu_request_cores / median_host_cpu) / (memory_request_normalized / median_host_memory)`.
`r > 2` is CPU-heavy, `r < 0.5` is memory-heavy; endpoints are balanced.
This is a relative classification, not a claim that a normalized memory unit is a GB.

## Host columns

`machine_id` is the original source ID. `cpu_capacity_cores`,
`memory_capacity_normalized`, and `disk_capacity_normalized` are the physical
capacity fields from the add record. `source_row` points to `server_event.csv`.
`usage_observations` and `mean_*_fraction` summarize available valid source usage
records; blank means unobserved. `host_stratum` is capacity plus coarse usage bands.
It is sampling metadata, not an initial utilization requirement.

`host_events.csv` preserves non-add source events. Zero capacities on software-error
rows do not replace the valid capacity in the add record. No failures are replayed
in the default scenario.

## Cleaning, bias and limitations

1. Preserve all six raw files. Verify archive checksum and extracted byte content.
   All rows are checked against the schema; only the known extra blank ninth field
   in container events is tolerated and counted.
2. Exclude nonterminated task groups, missing keys/requests, nonfinite or nonpositive
   requests/counts, pre-window arrivals and end times outside the chosen window.
   Negative timestamps mean pre-trace activity; exclude them from this clean-start
   scenario rather than clamping them to zero. These decisions introduce survivor
   and boundary bias; this is a selected completed-workload experiment.
3. Derive runtime only from `Terminated` instance trials with `seq_no=1`, known
   machines, positive duration, complete window coverage and intervals within the
   parent task's bounds. Exclude groups with no valid observation or more accepted
   trials than their declared multiplicity. A first attempt that failed then
   succeeded is not represented in that runtime estimate. Coverage is explicit.
4. The source has no reliable per-record instance identifier; do not deduplicate
   identical-looking records that can be distinct parallel instances. Derived IDs
   describe the modeled replay, not recovered source identities.
5. The mean runtime is applied to all declared instances, even with partial coverage.
   This compresses within-task stragglers and launch staggering. `duration_min_s`
   and `duration_max_s` permit a later runtime sensitivity experiment. Do not claim
   exact production instance replay or use task end-minus-create as processing time.
6. Task creation is the modeled release time. v2017 does not expose usable DAG edges
   for reconstructing dependencies. The simulation treats task groups as independent
   releases; it is not a dependency-faithful workflow replay.
7. Constant requested demand supports a controlled placement comparison, but removes
   within-instance usage variation. LR then observes changes in aggregate host load
   caused by arrivals, completions and migrations, not measured per-instance CPU
   histories. If LR needs empirical temporal demand, that needs a different workload
   model and a separately documented study.
8. Memory-normalized MMT ranking is possible when one common conversion is used,
   but migration seconds/energy require an explicit RAM-unit-to-bytes and bandwidth
   model. The data does not supply absolute RAM GB or migration bandwidth.
9. The host sample reserves at least one representative per rounded capacity class;
   this deliberately overrepresents the rarest class. Small samples can still omit
   rare host utilization or workload strata. Quotas control
   task-group resource proportions. Calibration swaps whole source rows inside
   the same arrival-bin/resource-skew cell, preserving group quotas and source
   values. Instance/request arrivals, runtime-weighted work and resource mix
   must meet the bounds in `config/default.json`; validation recomputes them
   independently. Exact burst magnitudes remain approximate. See
   [SAMPLING_QUALITY.md](SAMPLING_QUALITY.md).

The report records actual sampling deviations and stress diagnostics. Keep the
manifest and configs with results so all policies use exactly the same inputs.
