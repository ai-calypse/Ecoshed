# D6 Phase 5 — verified live replay dashboard

Real Kafka workload arrival transport monitoring; offline scheduler results remain separate. No live scheduler or live energy model.

## Implemented integration

- Eighth native page: **Live Workload Replay**, at http://localhost:8501/live_replay. Seven existing offline view scripts are unchanged.
- Start/Stop invoke the supported external controller with validated argument lists. Workers survive browser reload/navigation; controller lock and SQLite remain authoritative.
- Read-only, bounded SQLite snapshots; two-second active fragment updates, reduced historical polling and no idle/completed polling. Broker client is reused and observation timestamps are visible.
- Twelve live KPIs, distinct-instance progress, actual throughput/demand/lag charts, worker/errors panel, retained verifier receipts and recorded-session downloads.
- Additive offset/verification tables retain real observations. Event persistence and Kafka commit semantics are unchanged.

## Actual Chrome verification

- Dashboard-started full replay: `49dc2730-14b9-48a1-b05b-d2c3eb290b38`; 250 groups at 600×.
- **16,534 confirmed publications, 16,534 distinct consumed instances, 250 groups; 0 invalid messages and 0 sequence gaps.**
- Complete event-level source verification passed. Source stream SHA-256: `bdd55b9e3e25240e953c6626c969905a5186e857fab9b87a443ab83195cc14fd`.
- Session elapsed: 72.698 s; average distinct persistence: 227.43/s, including timed replay and verification. This is not scheduler performance.
- Browser reload and navigation to/from the offline energy page preserved the same replay UUID and external worker.
- A second browser showed Start disabled with zero rendering exceptions. Controller-level duplicate protection also passed the real Kafka regression suite.
- Browser cancellation: `ddf43e21-6b0b-4f31-96cd-e90ed77b9e8d`, 3,684 confirmed / 3,684 distinct, status **cancelled**. No full verification was claimed.
- A new browser-started 1,000-group fast replay then completed: `53cba36e-b1bd-49df-ac2e-8e88b9b49399`, 68,457 instances in 10.987 s (6230.59/s).
- Historical selection downloaded actual JSON and CSV for the earlier 250-group UUID, with its own 16,534-instance count rather than the newer session count.
- Actual broker stop displayed unavailable/startup instructions and disabled Start; the offline scheduler comparison still rendered. Broker restart/reconnect restored reachability.
- All eight pages were visited in Chrome without exceptions. Live layout was checked at 1440px and 1152px; no horizontal overflow.
- The timestamp-formatting bug found with mixed active/completed history was corrected, covered by a regression test and rechecked in Chrome.

## Tests and preservation

- **275 distinct passing tests:** 181 ordinary D6 + 84 teammate + 10 real-broker integration tests. This preserves all prior 248 and adds 27 Phase 5 tests.
- Ordinary discovery explicitly skips the ten opt-in broker tests; their separate invocation passes all ten. These include complete real 250/1,000/4,000-group replays, duplicate redelivery, consumer restart, cancellation and broker recovery.
- Dependency, syntax and type checks pass; all eight pages pass live runtime agent checks.
- All **508 original tracked files**, Phase 1 exports, recovered Phase 3 files/reports and original Phase 4 reports remain unchanged. All changes are under ARNAV_Task; nothing was committed or pushed.
- Offline numerical validation still passes 39 grouped checks. Historical lineage remains unresolved.

## Screenshots

- [active replay](phase5_screenshots/active_replay.png) — actual Chrome capture, 1440 × 1050.
- [broker unavailable](phase5_screenshots/broker_unavailable.png) — actual Chrome capture, 1440 × 1050.
- [completed verified replay](phase5_screenshots/completed_verified_replay.png) — actual Chrome capture, 1440 × 1050.
- [idle configuration](phase5_screenshots/idle_configuration.png) — actual Chrome capture, 1440 × 1050.
- [laptop 1152](phase5_screenshots/laptop_1152.png) — actual Chrome capture, 1152 × 1050.
- [live throughput and demand](phase5_screenshots/live_throughput_and_demand.png) — actual Chrome capture, 1440 × 1050.
- [session history](phase5_screenshots/session_history.png) — actual Chrome capture, 1440 × 1050.

## Operation and remaining limitations

See [README](../README.md#live-dashboard-integration-phase-5) for installation, broker startup, dashboard launch, browser demonstration, metrics and recovery instructions. Detailed session receipts, observations, offsets, test results and image hashes are in `phase5_verification.json`.

- Three historical research provenance hash references remain unresolved.
- Arrival transport is not live scheduling, energy measurement, utilization, allocation or observed SLA outcomes.
- Publication throughput history is not recorded; the UI shows actual acknowledged totals rather than an invented series.
- Resource-skew composition is the whole verified source population; consumed skew aggregates are not inferred.
- Controller acknowledgement totals persist in batches and can temporarily trail consumption.
- Broker reachability is an observed check cached up to ten seconds, with its timestamp shown.
- Old sessions may have no lag samples or detailed receipt; absence stays explicit until optional verification.
- A dead controller requires documented controller/CLI recovery; the UI does not erase history or silently clear active state.
- At-least-once transport with idempotent SQLite persistence; single broker, no high availability.
- Measured timing/throughput are local transport observations, not scheduler benchmarks.

The broker and dashboard are left running. No replay workers remain active. Phase 6 may use the completed offline/live platform without rebuilding the transport. No final academic report or presentation was generated.
