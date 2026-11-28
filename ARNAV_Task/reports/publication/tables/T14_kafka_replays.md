# Complete replay and event-level verification results

Fast and timed runs are explicitly separate. Session durations are controller lifecycle measurements, not isolated verifier time or scheduler benchmark time.

| Mode | Size | Replay Id | Speed | Distinct Instances | Groups | Elapsed Wall S (seconds) | Average Instances Per S (distinct instances/second) | Complete | Integrity Passed | Invalid | Sequence Gaps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Phase 4 fast | 250 | 72306d47-074a-492f-8ece-334195b12df6 | 0 | 16534 | 250 | 3.93423 | 4,202.6 | True | True | 0 | 0 |
| Phase 4 fast | 1000 | 9a097df0-12be-4651-9007-35242d78aa8a | 0 | 68457 | 1000 | 11.3928 | 6,008.79 | True | True | 0 | 0 |
| Phase 4 fast | 4000 | 1f2aee4c-4323-43a4-a6a6-2b3acebf4e20 | 0 | 378285 | 4000 | 54.6003 | 6,928.26 | True | True | 0 | 0 |
| Phase 5 browser timed | 250 | 49dc2730-14b9-48a1-b05b-d2c3eb290b38 | 600 | 16534 | 250 | 72.6981 | 227.434 | True | True | 0 | 0 |

Sources: `ARNAV_Task/reports/phase4_verification.json`, `ARNAV_Task/reports/phase5_verification.json`.
