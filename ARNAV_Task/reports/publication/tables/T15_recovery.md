# Duplicate delivery and interruption recovery

Exact duplicates increase accepted deliveries without increasing unique-instance counts. Consumer restart resumes from durable offsets after SQLite persistence.

| Test | Replay Id | Consumed Deliveries | Distinct Instances | Duplicate Deliveries | Invalid Messages | Sequence Gaps | Passed | Persisted Before Restart | Offset Before Restart |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| duplicate_redelivery | 72306d47-074a-492f-8ece-334195b12df6 | 33068 | 16534 | 16534 | 0 | 0 | True | — | — |
| consumer_restart | fc186769-43ea-4e89-b10d-e560f1f0e0ac | 16534 | 16534 | 0 | 0 | 0 | True | 317 | 1406930 |

Sources: `ARNAV_Task/reports/phase4_verification.json`.
