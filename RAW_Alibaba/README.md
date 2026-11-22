# Alibaba v2017: fresh raw-archive preparation and simulation

This is the active project pipeline. It reads the user-downloaded
`alibaba-trace-2017.tar.gz`, extracts the original CSV bytes, independently prepares
inputs, and evaluates all six policies under each SPECpower curve separately.
**No Yaksh cleaned CSVs, loader or cleaning code are used by preparation or replay.**
No artificial workloads are substituted. Small parser fixtures in unit tests are
not experiment results.

## Run from repository root

Python 3.10+ and the standard library:

```sh
python -m RAW_Alibaba.extract
python -m RAW_Alibaba.prepare
python -m RAW_Alibaba.verify_data
python -m RAW_Alibaba.run
python -m RAW_Alibaba.verify
python RAW_Alibaba/analysis/build_report.py
```

`python -m ENERGY_Study.run` and `python -m ENERGY_Study.verify` now delegate to
this raw-archive runner and verifier. They do not silently fall back to prepared
handoff files or generated jobs. Full input/preparation stages need the local
archive. The benchmark can be rerun from its independently prepared files after
the manifest and raw-row validation pass.

Use `--sizes 250 --curves hpe_dl360_gen9 --output RAW_Alibaba/smoke` for a real-data
smoke run. Verify it with
`python -m RAW_Alibaba.verify --source RAW_Alibaba/smoke --reports RAW_Alibaba/smoke --allow-partial`.
The full verifier requires all **54 combinations: three sizes x six policies x
three curves**. Each curve gets the identical 18-case grid. Curves are never
averaged or mixed within one simulation.

## Provenance and checksum caveat

The uploaded archive is 243,321,159 bytes. Its recorded SHA-256 is
`b7efe9dc9caa75352de41b9ac34b329602cde3414fd7cab87c1d21a9a9871d66`.
This does **not** match the old `trace_201708.tgz` checksum currently listed by
Alibaba. A [reported upstream issue](https://github.com/alibaba/clusterdata/issues/209)
describes the newer archive filename/checksum discrepancy. We do not mark that
legacy checksum as passed.

Gzip CRC/trailer, tar member types, complete file lengths and six extracted CSV
fingerprints were checked. All six CSV byte hashes also match raw-file fingerprints
in the earlier package's audit; that comparison is **corroboration only**, not a
cleaned-data input to this pipeline. See [archive_audit.json](archive_audit.json)
and [archive_content_corroboration.json](archive_content_corroboration.json).
The archive and extracted raw CSVs are preserved unchanged locally and ignored by
Git. The archive mismatch remains visible in every result and the final report.

## Independent preparation

- Read source host `add` records, retaining physical CPU and normalized memory.
  Select 64 deterministic hosts with seed 2026, retaining every rounded capacity
  class. Historical source utilization is not added as background replay load.
- Read terminated task rows within `[0, 43200]`, with positive requests/counts,
  unique keys and single-host feasibility. Convert task CPU by dividing by 100,
  following [Alibaba's unit clarification](https://github.com/alibaba/clusterdata/issues/11).
- Scan all raw instance attempts, joining source job/task IDs. Keep completed
  first attempts on known source machines with positive duration fully inside
  the parent's bounds. Missing optional usage fields are not imputed or treated
  as zero demand; they do not drive the request-based workload model.
- Admit a task group only when it has exactly the original `instance_num` valid
  observations. Preserve each observation's own `end - start` runtime. Do not
  replace durations with a group mean, downscale multiplicity or fabricate missing
  instances. Incomplete/overobserved groups are excluded and counted.
- Select 250/1,000/4,000 groups using deterministic quotas over 15-minute arrival
  bins, relative CPU/memory skew and multiplicity bands. No energy results are used
  in selection. Group quotas do not guarantee identical instance-weighted bursts.
- Preserve raw source-row pointers and release every instance at task creation.
  IDs such as `raw_attempt_row_123` identify actual raw records, not recovered
  production instance IDs, which this trace does not expose reliably.

The resulting workloads have **16,534 / 68,457 / 378,285 observed instances**.
Of the 4,000 groups, 2,074 have variable observed runtimes, and that variation is
preserved. Source filters, counters, input/output hashes and known limitations
are recorded in [prepared/manifest.json](prepared/manifest.json).

## Validation and model limits

[verify_data.py](verify_data.py) independently rereads the source tables and checks
every selected task, host and observed instance row. It checks original requests,
release bounds, per-record duration, uniqueness and complete multiplicity.
[data_validation.json](data_validation.json) records the outcome. Replay refuses
a stale validation whose manifest hash no longer matches.

The experiment reuses Brave's event engine and Rohan's policy implementations,
adding existing energy/resource instrumentation. It does not expose true future
duration/completion to policies. The same FIFO admission, capacity limits,
migration/sleep assumptions and stopping rule apply to all policies. Every curve
uses a fresh simulator and a single selected whole-server SPECpower curve.

This remains a modeled, selected completed-batch replay. Task creation is the
modeled release, so original launch staggering and DAG dependencies are not
reconstructed. Requested demand stays constant; per-instance empirical CPU demand
histories are not supplied by this trace. Complete-observation and window filters
introduce selection/boundary bias. These samples, host pool and individual-duration
model differ from the historical handoff; do not compare their absolute kWh as if
they were the same workload. No confidence interval from independent production
windows is claimed.

Memory-to-bytes conversion, migration bandwidth and sleep/wake behavior remain
explicit assumptions. The SPEC curve is a surrogate, not a calibrated measurement
of Alibaba's servers or electricity bill. Read [REPORT.md](REPORT.md) for outcomes.
