# D6 Phase 4 — verified real Kafka replay

Authentic Alibaba-derived arrival transport, not live scheduling, energy measurement or a scheduler benchmark.

## Broker and environment

- Image: `apache/kafka:4.4.0@sha256:833b867a9585a141da455dc2b57431c65cbccb27f11c91f694444cca9f777e0f`; actual architecture: **arm64**; health: **healthy**.
- Single KRaft combined broker/controller; localhost external port 19092, internal 9092, controller 9093.
- One partition and one replica. Named persistent volume, 24-hour/1-GiB log retention, 256–512 MiB JVM heap and 1,536 MiB container limit.
- Python 3.12.15; dependencies: streamlit 1.67.0, plotly 7.2.0, pandas 3.1.1, kafka-python 3.0.13.

## Full authentic workload transport results

| Task groups | Confirmed / distinct | Groups verified | Invalid / gaps | Session elapsed (s) | Distinct instances/s |
|---:|---:|---:|---:|---:|---:|
| 250 | 16,534 / 16,534 | 250 | 0 / 0 | 3.934 | 4202.60 |
| 1000 | 68,457 / 68,457 | 1000 | 0 / 0 | 11.393 | 6008.79 |
| 4000 | 378,285 / 378,285 | 4000 | 0 / 0 | 54.600 | 6928.26 |

Every persisted event was compared with the Phase 3 source, including original IDs, arrival time, requests, skew, manifest identity, sequence and complete group multiplicity. Source-stream digests match. These rates include session execution and final verification; they are not scheduler benchmarks.

## Failure, duplicate and restart checks

- Exact redelivery: 33,068 accepted deliveries, 16,534 duplicates, still exactly 16,534 distinct instances; full event verification passes.
- Consumer interruption: 317 instances were durable before restart, at next offset 1406930; restart reached all 16,534 instances without count loss/inflation.
- Bounded timing: first 250 original arrivals at 600x, explicitly **partial**; producer elapsed 1.189s and maximum recorded positive drift 0.005184s. Original trace times remain unchanged.
- Cooperative stop: status **cancelled**, 20 confirmed / 20 distinct arrivals; duplicate start rejected and no running controller remained.
- The real dedicated broker was stopped; connectivity and controller startup failed clearly, then the broker restarted healthy with its volume/topic intact.
- Conflicting duplicates, malformed payloads, sequence gaps, rollback, send/ack failures and crash-before-offset-commit paths pass isolated synthetic unit tests. Such fabricated invalid messages were not used as Alibaba demonstration evidence.
- Standalone producer CLI, consumer CLI and verifier also completed a separate full 250-group replay successfully.

## Tests, persistence and preservation

- **248 distinct tests pass**: 154 ordinary D6, 84 teammate and 10 real-broker tests. The original 200 are preserved.
- Ordinary discovery skips the ten opt-in broker tests; the explicit real-broker invocation passes all ten.
- Dependency, syntax and type checks pass. All seven offline dashboard pages pass application tests, and localhost:8501 remains healthy.
- SQLite WAL/FULL synchronous persistence records sessions, source payload/digests, group counts, offered demand, throughput, errors and heartbeats. Kafka offset commits occur after SQLite COMMIT.
- Delivery is **at least once with idempotent persistence**, not distributed exactly once. Consumer restart is supported; ambiguous producer continuation is not.
- Read-only Phase 5 interface: `ARNAV_Task.kafka.state.read_sessions` and `read_metrics`.
- All **508 original tracked files**, Phase 1 exports, Phase 3 inputs/reports and the seven-page UI remain unchanged. Only D6 README/requirements and new Phase 4 files are changed. No commits or pushes.
- Three historical provenance hash discrepancies remain unresolved. No scheduler simulations were executed.

## Actual Kafka message

Read independently from Kafka during the 250-group integration test:

```json
{
  "arrival_time_s": 77,
  "cpu_request_cores": 0.5,
  "event_type": "workload_arrival",
  "input_manifest_sha256": "4e295b76cacf10326cd5e81fbcdd6cd8ea2261244d5d01ceaca3f051fdccb42c",
  "instance_id": "raw_attempt_row_3382192",
  "job_id": "7030",
  "memory_request_normalized": 0.0040587062873709,
  "replay_id": "72306d47-074a-492f-8ece-334195b12df6",
  "resource_skew": "balanced",
  "schema_version": 1,
  "sequence": 1,
  "task_group_id": "j7030_t41458",
  "workload_groups": 250
}
```

## Commands and limitations

See [README](../README.md#real-kafka-workload-replay-phase-4) for exact installation, Compose, controller, consumer and verification commands. Full machine-readable evidence, session UUIDs, offsets, worker state, source hashes and event-stream digests are in `phase4_verification.json`.

- One broker and replication factor one provide no high availability.
- Local plaintext listener, not production authentication/TLS.
- Kafka/SQLite do not share an atomic transaction; at-least-once delivery is explicit.
- Fatal schema/delivery errors remain failures; producer resume is deliberately disabled.
- Kafka retention can remove old broker records; SQLite histories also require deliberate disk management.
- Measured transport throughput is a laptop observation, not scheduler performance or a statistical benchmark.
- Timed test covers only the first 250 authentic arrivals at 600x; it is explicitly partial.
- No Phase 5 live dashboard page, final academic report or presentation is implemented.

The dedicated broker is left healthy; no replay workers remain active. The arrival transport is ready for Phase 5 dashboard integration.
