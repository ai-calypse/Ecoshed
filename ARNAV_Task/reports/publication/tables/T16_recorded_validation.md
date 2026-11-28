# Recorded validation and test coverage

Historical receipts are labeled by phase and not added together. Phase 6 totals, when present, use the frozen executed-test receipt; ordinary discovery skips broker tests which are counted only in the explicit integration run.

| Evidence | Check | Value |
| --- | --- | --- |
| Phase 4 recorded tests | Distinct passing tests | 248 |
| Phase 5 recorded tests | Distinct passing tests | 275 |
| Numerical reconciliation | Grouped artifact checks passed | 39 |
| Numerical reconciliation | Active experiment outcomes | 36 |
| Numerical reconciliation | Rejected instances | 0 |
| Numerical reconciliation | Unfinished instances | 0 |
| Phase 3 independent reconstruction | Raw-row validation passed | True |
| Phase 3 independent reconstruction | Hosts independently checked | 64 |
| Phase 6 executed regression | d6 ordinary passed | 213 |
| Phase 6 executed regression | new phase6 tests | 32 |
| Phase 6 executed regression | real kafka integration passed | 10 |
| Phase 6 executed regression | teammate passed | 84 |
| Phase 6 executed regression | total distinct passed | 307 |

Sources: `ARNAV_Task/reports/phase4_verification.json`, `ARNAV_Task/reports/phase5_verification.json`, `ARNAV_Task/reports/phase3_verification.json`, `ARNAV_Task/reports/artifact_validation.json`, `ARNAV_Task/reports/publication/test_results.json`.
