# Fresh Alibaba raw-archive experiment results

**These experiments were built directly from the uploaded raw Alibaba archive. No Yaksh cleaned CSVs, data loader or cleaning code were used to prepare/replay these inputs. No artificial workloads were substituted.** Shared simulator and scheduling code is reused.

**54 verified runs**, **8,338,968 completed instance replays**, zero rejected/unfinished instances. Each power curve has the same 18 combinations: three sample sizes and six policies. Every simulation starts fresh and uses exactly one curve.

## Archive integrity and provenance

Uploaded file: `alibaba-trace-2017.tar.gz`. SHA-256: `b7efe9dc9caa75352de41b9ac34b329602cde3414fd7cab87c1d21a9a9871d66`. Gzip CRC/trailer, tar members and all six extracted CSV lengths/hashes were checked. Every input and implementation file is fingerprinted.

**The compressed archive does not match Alibaba's published legacy `trace_201708.tgz` hash.** The newer download is named `alibaba-trace-2017.tar.gz`; an [upstream issue](https://github.com/alibaba/clusterdata/issues/209) reports that discrepancy. We do not mark the publisher's compressed checksum as passed. Separately, all six extracted CSV hashes match raw-file fingerprints recorded in the earlier package audit. That comparison corroborates the raw bytes; it does not supply any cleaned experimental inputs. See [archive_audit.json](archive_audit.json) and [archive_content_corroboration.json](archive_content_corroboration.json).

## Fresh preparation and observation fidelity

The pipeline read **80,553 raw task rows**, **16,094,656 raw instance-attempt rows**, and **1,352 host-event rows**. It found **37,407 eligible complete groups**. Every included group has exactly its original declared number of valid completed first-attempt records. Missing observations are not fabricated and multiplicity is not reduced.

Each included instance keeps its own observed source `end - start` duration. There is no group-mean runtime substitution. Task creation is still the modeled release; original host assignment and launch staggering are not replayed. Source host capacity records supply a newly selected fixed 64-host pool with seed 2026.

| Task groups | Observed instances | Groups with variable runtimes |
|---:|---:|---:|
| 250 | 16,534 | 128 |
| 1,000 | 68,457 | 527 |
| 4,000 | 378,285 | 2,074 |

Selection uses fixed quotas over 15-minute arrival bins, relative resource skew and multiplicity bands, with no energy outcome used in sampling. These are group-level quotas; they do not establish identical instance-weighted bursts or exact representativeness. Complete-observation and completed-window filters introduce selection/boundary bias. The smaller samples share groups with the larger sample and are not independent replications.

**Do not compare absolute kWh against the historical handoff as if the workloads were identical:** the eligible population, selected groups, host pool and per-instance runtime model differ. All policies below are rerun on the same freshly prepared inputs for a fair within-study comparison.

## Modeled energy, kWh

Columns compare first-fit (FF), CPU best-fit (BF), original CPU-oriented LR-MMT (LR), original weighted memory-aware LR-MMT (LR+M), energy-first CPU (EF-CPU), and energy-first memory (EF-M). A positive last column means EF-M used less energy than EF-CPU.

| Curve | Groups | FF | BF | LR | LR+M | EF-CPU | EF-M | EF-M reduction vs EF-CPU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HPE DL360 Gen9 | 250 | 5.196158 | 5.202633 | 5.217227 | 5.196949 | 5.216789 | 5.192312 | +0.4692% |
| HPE DL360 Gen9 | 1,000 | 8.975435 | 8.995054 | 9.032048 | 9.152858 | 9.018430 | 9.031747 | -0.1477% |
| HPE DL360 Gen9 | 4,000 | 34.151822 | 34.198514 | 34.269962 | 39.136094 | 34.129353 | 36.117004 | -5.8239% |
| Huawei RH2288H V3 | 250 | 5.160144 | 5.166418 | 5.189138 | 5.158752 | 5.179556 | 5.154031 | +0.4928% |
| Huawei RH2288H V3 | 1,000 | 8.797097 | 8.815802 | 8.969770 | 8.964688 | 8.847797 | 8.856492 | -0.0983% |
| Huawei RH2288H V3 | 4,000 | 32.828993 | 32.870935 | 34.017004 | 37.745319 | 32.991997 | 34.951618 | -5.9397% |
| QuantaGrid D51B-2U | 250 | 5.248996 | 5.255867 | 5.270602 | 5.244489 | 5.270635 | 5.245165 | +0.4832% |
| QuantaGrid D51B-2U | 1,000 | 9.158216 | 9.179279 | 9.230472 | 9.356722 | 9.215057 | 9.214876 | +0.0020% |
| QuantaGrid D51B-2U | 4,000 | 35.036588 | 35.085098 | 35.333163 | 40.477587 | 35.243717 | 37.441601 | -6.2362% |

EF-M saved energy in **4/9** paired workload/curve comparisons. A small positive difference, especially below 0.01%, should not be presented as robust production savings. All gains and losses are retained; no independent-window confidence interval or measured electricity-saving claim is made.

## Waiting, migrations and powered hosts: primary HPE curve

| Groups | Policy | Mean wait, s | p95 wait, s | Migrations | Mean powered hosts | Pressure fraction |
|---:|---|---:|---:|---:|---:|---:|
| 250 | energy_first_cpu | 8.421 | 10.000 | 270 | 1.234 | 0.0037 |
| 250 | energy_first_memory | 8.380 | 10.000 | 276 | 1.187 | 0.0032 |
| 1,000 | energy_first_cpu | 5.742 | 10.000 | 1,654 | 4.389 | 0.0183 |
| 1,000 | energy_first_memory | 5.254 | 10.000 | 1,664 | 4.509 | 0.0160 |
| 4,000 | energy_first_cpu | 56.141 | 466.000 | 7,519 | 23.677 | 0.1842 |
| 4,000 | energy_first_memory | 55.212 | 466.000 | 8,622 | 27.712 | 0.1737 |

Pressure fraction integrates reserved CPU or memory above 0.9 over host-time; it is not an observed SLA failure rate. Mean/p95 waits include queueing and waking, while migration pauses are separate and included in actual completion timing. The full summaries also include fragmentation, stranded-capacity probes and sleep/wake/active energy components.

## Shared assumptions and limitations

All policies use the same host pool, original resource requests, original observed durations, independent-instance FIFO admission, capacity limits and window-plus-drain rule. LR/MMT controller settings and migration/sleep assumptions are shared by the four migration policies; FF/BF are non-migrating baselines. The energy-first pair differs only in its power tie-break.

Task CPU is divided by 100 under [Alibaba's unit clarification](https://github.com/alibaba/clusterdata/issues/11). Memory remains normalized for placement. Migration assumes 64 GiB per normalized unit and 125 MB/s per concurrent transfer. Sleep is modeled at 5 W after 60 seconds idle; wakeup takes 10 seconds. These parameters are assumptions, not measurements supplied in the trace.

The model replays selected completed batch work, not production DAG dependencies, failures, background online load or empirical per-batch-instance usage histories. SPECpower is a whole-server surrogate curve applied at requested CPU fraction, not a calibration of Alibaba hardware or its electricity bill. No future durations or original placements are exposed to scheduling policies.

## Validation and reproduction

The independent validator reread raw task, host and attempt rows and matched every selected request, capacity, release and individual duration, plus complete original multiplicity. Replay validates unique outcomes, completed work, full drain, capacity samples, energy sums and observed runtime plus migration pauses. The final verifier checks full equal per-curve coverage and unchanged implementation/input hashes.

```sh
python -m RAW_Alibaba.extract
python -m RAW_Alibaba.prepare
python -m RAW_Alibaba.verify_data
python -m RAW_Alibaba.run
python -m RAW_Alibaba.verify
python RAW_Alibaba/analysis/build_report.py
```

[Preparation manifest](prepared/manifest.json) · [Raw-row validation](data_validation.json) · [Full comparison](reports/comparison.csv) · [Final validation](reports/validation.json)
