# EcoSched demonstration troubleshooting

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
