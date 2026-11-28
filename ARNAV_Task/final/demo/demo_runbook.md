# EcoSched classroom demonstration runbook

AMS 560 Big Data · Stony Brook University. Presenter assignment is provisional: Arnav operates the D6 system; teammates explain their modules. Adapt the suggested schedule after confirming the actual classroom time limit; none was found in the repository.

## Before class

Use the prepared laptop and existing validated active package. Connect power, check Docker Desktop, reserve a browser tab at 1440px or 1152px and avoid starting another replay. The active inputs are seed 2026, 64 hosts; historical seed-560 inputs must not be substituted. Keep the PDF deck and Phase 5 screenshots available offline.

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

1. **Overview (45 s):** show the 36-outcome matrix, four active policies, three sizes and three separate power curves. Explain that these pages contain previously executed offline scheduler simulations.
2. **Scheduler/energy comparison (45 s):** choose one matched condition, then the largest workload. Positive reduction means savings. The memory-aware variant wins 4/9 cases but incurs 10.96–14.56% largest-workload penalties. Do not switch to historical policies.
3. **D5 findings (45 s):** show powered-host time and energy decomposition. Explain the CPU/memory balance penalty and why fewer wakeups/migrations do not guarantee lower energy. Pressure is a modeled SLA proxy.
4. **Live page setup (20 s):** navigate to Live Workload Replay. Select **250 groups**, confirm **16,534 expected instances**, and choose **600×**. Show broker, topic, input identity and no active session.
5. **Start exactly once:** use the dashboard Start button. Note the replay ID. The external controller owns workers; browser refresh/navigation must not restart them.
6. **Monitor real transport (about 1–2 min):** show confirmed publication, accepted deliveries and distinct persisted instances as different counters. Explain wall-clock throughput, logical trace progression, offered CPU/normalized-memory arrival requests, and actual session/topic lag. This is not live scheduling, resource allocation, host utilization, energy or SLA measurement.
7. **Verify completion (20 s):** wait for the complete event-level verification receipt, not only a full progress bar. Confirm 16,534 distinct instances and 250 original groups, with no invalid events, gaps or conflicts.
8. **History (20 s):** select an actually retained completed 1,000- or 4,000-group session, label it recorded, inspect verification and download its summary. If runtime history is absent, use the frozen Phase 4/5 report explicitly as recorded evidence.

The actual Phase 5 browser-driven 600× session took **72.698 seconds**, averaging **227.43 distinct instances/s**. This is a recorded laptop observation, not a guaranteed classroom duration or scheduler benchmark. Leave slack for startup, UI switching, verification and interruptions.

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
