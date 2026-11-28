"""Rebuild classroom procedures and evidence-based defense notes."""
from pathlib import Path
from .evidence import Evidence, FINAL, safe_output


def build(output=FINAL/'demo'):
    output=safe_output(output);e=Evidence();output.mkdir(parents=True,exist_ok=True)
    docs={
    'demo_runbook.md':'''# EcoSched classroom demonstration runbook

AMS 560 Big Data · Stony Brook University. Presenter assignment is provisional: Arnav operates the D6 system; teammates explain their modules. Adapt the suggested schedule after confirming the actual classroom time limit; none was found in the repository.

## Before class

Use the prepared laptop and existing validated active package. Connect power, check Docker Desktop, reserve a browser tab at 1440px or 1152px and avoid starting another replay. The active inputs are seed {seed}, {hosts} hosts; historical seed-560 inputs must not be substituted. Keep the PDF deck and Phase 5 screenshots available offline.

```bash
source ARNAV_Task/.runtime/venv/bin/activate
python -m pip check
python -m ARNAV_Task.documentation.validate_final
python -m ARNAV_Task.workload.prepare_replay --size 250
docker compose -f ARNAV_Task/docker-compose.yml up -d --wait
python -m ARNAV_Task.kafka.admin --ensure-topic
python -m ARNAV_Task.kafka.controller status
streamlit run ARNAV_Task/dashboard/app.py
```

If port 8501 is already serving the dashboard, reuse it instead of starting another server. Open http://localhost:8501. Do not launch a producer separately from the controller. No topic/database deletion or volume removal is part of this demonstration.

## Suggested sequence (approximately 5–6 minutes, adjustable)

1. **Overview (45 s):** show the {runs}-outcome matrix, four active policies, three sizes and three separate power curves. Explain that these pages contain previously executed offline scheduler simulations.
2. **Scheduler/energy comparison (45 s):** choose one matched condition, then the largest workload. Positive reduction means savings. The memory-aware variant wins {wins}/{pairs} cases but incurs {penalty_lo:.2f}–{penalty_hi:.2f}% largest-workload penalties. Do not switch to historical policies.
3. **D5 findings (45 s):** show powered-host time and energy decomposition. Explain the CPU/memory balance penalty and why fewer wakeups/migrations do not guarantee lower energy. Pressure is a modeled SLA proxy.
4. **Live page setup (20 s):** navigate to Live Workload Replay. Select **250 groups**, confirm **{instances_250:,} expected instances**, and choose **600×**. Show broker, topic, input identity and no active session.
5. **Start exactly once:** use the dashboard Start button. Note the replay ID. The external controller owns workers; browser refresh/navigation must not restart them.
6. **Monitor real transport (about 1–2 min):** show confirmed publication, accepted deliveries and distinct persisted instances as different counters. Explain wall-clock throughput, logical trace progression, offered CPU/normalized-memory arrival requests, and actual session/topic lag. This is not live scheduling, resource allocation, host utilization, energy or SLA measurement.
7. **Verify completion (20 s):** wait for the complete event-level verification receipt, not only a full progress bar. Confirm {instances_250:,} distinct instances and 250 original groups, with no invalid events, gaps or conflicts.
8. **History (20 s):** select an actually retained completed 1,000- or 4,000-group session, label it recorded, inspect verification and download its summary. If runtime history is absent, use the frozen Phase 4/5 report explicitly as recorded evidence.

The actual Phase 5 browser-driven 600× session took **{timed_duration:.3f} seconds**, averaging **{timed_rate:.2f} distinct instances/s**. This is a recorded laptop observation, not a guaranteed classroom duration or scheduler benchmark. Leave slack for startup, UI switching, verification and interruptions.

## Recorded fallback — never fake a live session

If Docker, Kafka, input files or the classroom environment fail, say: “The live transport is unavailable here. The following is previously recorded, fully verified evidence.” Continue using the seven offline research pages, retained historical sessions, S01–S04, phase4/phase5_verification.json and actual screenshots in ARNAV_Task/reports/phase5_screenshots/. The completed browser session is identified in that receipt. Do not animate counters or imply a screenshot is current.

## Finish safely

After successful completion, inspect controller status. If interrupted, use the dashboard Stop button or the supported CLI:

```bash
python -m ARNAV_Task.kafka.controller stop
python -m ARNAV_Task.kafka.controller status
# Optional broker shutdown after the demonstration, preserving its named volume:
docker compose -f ARNAV_Task/docker-compose.yml stop
```

Cancelled/partial sessions are incomplete and cannot be presented as complete verified workloads. Do not close the browser to stop workers; navigation is independent of their lifecycle.
''',
    'demo_checklist.md':'''# Classroom demonstration checklist

- [ ] Confirm actual presentation time, submission format and presenter allocation with the course/team.
- [ ] Activate the existing Python 3.12 environment; run dependency and final-artifact validation.
- [ ] Confirm authentic active inputs and expected 250-group count: {instances_250:,} instances.
- [ ] Start Docker Desktop; start the existing Compose broker and ensure the single-partition topic.
- [ ] Check no active replay exists; retain previous session history.
- [ ] Reuse http://localhost:8501 if already running; verify all eight navigation entries.
- [ ] Open report/deck PDF and actual fallback screenshots before presenting.
- [ ] Explain offline scheduling evidence before switching to live arrival transport.
- [ ] Select 250 groups / 600× and start once; note replay ID.
- [ ] Distinguish confirmed publications, deliveries and distinct instances.
- [ ] Show measured throughput/offset lag and offered requests, never inferred energy/utilization.
- [ ] Wait for full event-level verification; do not equate count completion with integrity.
- [ ] Label previously completed larger sessions and screenshots as recorded.
- [ ] Stop a cancelled session cooperatively; check no workers remain.
- [ ] Preserve topics, SQLite history, Docker volume and all research artifacts.
''',
    'troubleshooting.md':'''# EcoSched demonstration troubleshooting

| Symptom | Action and honest interpretation |
|---|---|
| Broker unavailable | Start Docker Desktop, then `docker compose -f ARNAV_Task/docker-compose.yml up -d --wait`; run `python -m ARNAV_Task.kafka.admin --ensure-topic`. Do not recreate/delete unrelated containers or volumes. |
| Port 8501 in use | Check whether the existing EcoSched server is healthy and reuse it. Do not terminate an unknown process. |
| Workload unavailable / hash mismatch | Run `python -m ARNAV_Task.workload.prepare_replay --size 250`; follow Phase 3 restoration instructions. Never replace active inputs with historical or synthetic data. Offline research pages remain usable. |
| Start disabled / duplicate start rejected | Inspect the active session and controller status. Controller locking is authoritative across browsers. Do not launch duplicate producers. |
| Counters temporarily differ | Confirmed acknowledgements persist in batches and can trail consumption. Accepted deliveries include exact duplicates; distinct counts do not. Check timestamp freshness. |
| Throughput is unavailable | Historical sessions have no current throughput. Inspect actual recorded buckets; do not replace missing observations with zero. |
| Topic lag differs from session lag | Topic lag uses the observed broker end offset; session lag is bounded by the selected replay’s producer boundary. They describe different scopes. |
| Consumer/controller failure | Preserve the session/database/logs and use documented Phase 4 CLI recovery. Inspect status/errors before restarting. Never clear state simply to obtain a green indicator. |
| Full count but verification failed | Treat the replay as failed/incomplete. Inspect identity, sequence, manifest and conflict errors with `python -m ARNAV_Task.scripts.verify_replay --replay-id latest`. |
| Strict provenance check fails | Expected: three historical metadata links remain unresolved. Numerical consistency and exact recovered CSVs do not repair those historical bytes. |
| Publication source-freshness warning after documentation edits | Phase 6 retains its original README source fingerprint. Frozen output hashes remain valid; the final validator records documentation evolution separately from research lineage. Do not rewrite historical hashes. |
| Classroom infrastructure cannot recover quickly | Switch explicitly to recorded session receipts/screenshots and offline research results. Do not claim live activity. |

Cancellation is not verified completion. Use Stop/controller shutdown and inspect final status. At-least-once transport with idempotent SQLite persistence is not distributed exactly once or high availability.
''',
    'defense_preparation.md':'''# EcoSched defense preparation

Answers reflect active artifacts, not unimplemented plans. Presenter allocation remains provisional.

**What is the research novelty?** An isolated, explainable placement ablation: change CPU-oriented incremental-power scoring to CPU/memory balance-aware scoring while retaining the same LR/MMT controller, simulator, data and power assumptions. The contribution includes a defensible negative result, not a universal new scheduler.

**Why can memory-aware placement consume more energy?** It can prefer emptier already-powered hosts because the balance penalty outweighs the incremental-power advantage of busy hosts. Work spreads across more hosts that empty less readily. D5’s per-curve largest-workload on/work shares are {hpe_on_share:.2f}%, {huawei_on_share:.2f}% and {quanta_on_share:.2f}% of each curve’s net gap; fewer wakes offset some cost. The earlier “about 88%” pooled ratio is not one physical measurement.

**Why Alibaba data?** It supplies actual task requests, multiplicity, timestamps, machine capacities and eligible observed attempts. We preserve those relationships rather than generating favorable workloads. Completed/window filters and request-based modeling still limit production representativeness.

**Why SPECpower?** It provides measured whole-server load-to-watts points. We interpolate them as a surrogate sensitivity model. They are not calibrated Alibaba hardware, and modeled kWh is not an observed electricity bill.

**What makes comparisons fair?** Primary pairs match workload size, curve, fixed {hosts}-host pool, seed {seed}, controller, admission, runtime, migration/sleep model and stopping rule. Both scores enforce memory feasibility. Additional baselines have no consolidation controller, so their comparison has broader differences.

**Why {runs} rather than 54 experiments?** Four approved active policies × three sizes × three power curves. Historical additional policies are excluded from active conclusions, though their original code/results remain preserved.

**How is efficiency calculated?** Wh per completed individual instance = 1000 × modeled kWh / completed instances. A task group can contain many instances and is not the denominator.

**Why is pressure not an observed SLA?** It measures host-time above requested CPU/memory reservation thresholds. The model does not observe application deadlines or actual service failures.

**Why Kafka?** It demonstrates ordered, authentic workload transport and a separately verifiable monitoring pipeline for D6. It is not the core scheduling novelty and does not improve scheduler energy by itself.

**What happens to duplicates?** SQLite uniqueness and payload consistency checks count exact redelivery without inflating distinct instances. Conflicting identity/sequence payloads are errors that prevent successful verification. The established semantics are at least once with idempotent persistence.

**How does restart preserve counts?** Events/aggregates commit to SQLite before manual Kafka offset commits. Re-delivery after interruption is safe because persistence is idempotent. Full source-facing event verification, not counts alone, establishes completion.

**Is the live replay running the scheduler?** No. It transports arrivals and monitors offered requests, throughput, lag and integrity. Energy, active hosts, migrations and waiting on research pages come from earlier offline simulations.

**Can the original results be fully reproduced?** Exact active archive/member/prepared-output identities and independent raw-row validation are established; numerical results reconcile. Three historical metadata references remain unresolved and D6 did not rerun the complete scheduler matrix. Full historical lineage or fresh simulation replication is not claimed.

**What remains limited?** One selected window/pool, overlapping samples, complete-attempt filtering, no statistical replications, request-based utilization, surrogate power, assumed migration/sleep behavior, missing background/DAG dynamics, limited category observations and a single-broker laptop transport setup.

**What did each person implement?** Yaksh: historical D1 data/sampling handoff. Brave: event simulator, power and active raw/experiment integration. Rohan: documented D3 scheduling/controller modules, imported in Brave’s integration commit. Rushi: D5 accounting, observer, placement/skew analysis. Arnav: D6 artifact validation, dashboard, recovered-input verification, Kafka workers/controller/state, live monitoring, publication exports and final report/deck/runbook. Git authorship and implementation credit are explicitly separated.

**What was Arnav’s individual technical contribution?** A common numerically reconciled artifact layer; honest provenance diagnostics and exact input recovery; a professional eight-page offline/live dashboard; real ordered Kafka replay with durable idempotent SQLite state and event-level verification; reproducible publication assets; and this editable academic/demo package. Existing scheduling and preparation algorithms were reused rather than reimplemented. D6 work remains uncommitted.

**Did the proposed approach work?** It saved energy in {wins}/{pairs} primary cases, with {penalty_lo:.2f}–{penalty_hi:.2f}% penalties at the largest workload. Some performance metrics improved. The result identifies an energy/performance trade-off and a placement-scoring mechanism, not consistent energy savings or statistical significance.
'''}
    for name,template in docs.items():(output/name).write_text(e.text(template),encoding='utf-8')
    return sorted(docs)


if __name__=='__main__':print('Generated demonstration documents: '+', '.join(build()))
