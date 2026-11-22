# Raw Alibaba v2017: verified fields and deferred work

The active experiment now uses the existing verified Alibaba-derived package.
Only direct raw-archive download/preparation remains deferred. The earlier
synthetic diagnostics are historical and cannot be used as Alibaba evidence.

The user supplied the [official v2017 repository folder](https://github.com/alibaba/clusterdata/tree/master/cluster-trace-v2017).
That folder contains documentation, a schema and checksum instructions. The full
trace is hosted separately in Alibaba Object Storage, as described in the
[publisher's download README](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2017/README2017.md).
This study did not download the archive or perform raw-trace cleaning/replay.

The [official schema](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2017/schema.csv)
and [field description](https://github.com/alibaba/clusterdata/blob/master/cluster-trace-v2017/trace_201708.md)
confirm:

- `batch_task.csv`: task create/end bounds, job/task IDs, original instance count,
  requested CPU and normalized requested memory.
- `batch_instance.csv`: individual attempt start/end times, IDs, source machine,
  status/trial information and maximum/average CPU and normalized memory. These
  are not per-batch-instance CPU/memory time series.
- `server_event.csv`: source capacity and availability events.
- `server_usage.csv`: total machine utilization, including all workloads and OS.
- `container_usage.csv`: usage histories for online containers, identified by
  container IDs; these are not histories for the batch instances.

Consequently the raw source can support retaining individual runtime observations
and independently building development/evaluation windows. It does not directly
supply batch-instance dynamic demand histories, memory byte conversion,
migration throughput, sleep/wake power calibration or a measured server-energy
trace. Measured total machine usage cannot be added unchanged to replayed batch
requests without accounting for their original contribution.

Deferred raw-trace track, per the instruction to leave cleaning aside for now:

1. Download and verify the publisher's archive/checksums; retain source attribution.
2. Independently join task/attempt records with explicit units, missing-record and
   retry rules; preserve original multiplicity and available duration variation.
3. Separate development and evaluation windows, and sample host pools without
   using outcomes to choose favorable workloads.
4. Replay both policies with identical source-derived inputs, admission rules,
   stopping rules and migration assumptions; report all selected windows.
5. Keep request-based replay claims separate from any later validated dynamic
   demand model. Use external calibration or sensitivity ranges for unavailable
   physical parameters instead of inventing measured values.
