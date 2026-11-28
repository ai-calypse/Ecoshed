# Dataset characteristics

Active raw-derived Alibaba v2017 package. Individual observed durations support offline simulation; arrival replay events do not expose future durations.

| Characteristic | Value |
| --- | --- |
| Dataset | fresh_user_archive_alibaba_v2017 |
| Source | https://github.com/alibaba/clusterdata/tree/master/cluster-trace-v2017 |
| Archive bytes | 243321159 |
| Archive SHA-256 | b7efe9dc9caa75352de41b9ac34b329602cde3414fd7cab87c1d21a9a9871d66 |
| Sampling seed | 2026 |
| Host pool | 64 |
| Logical arrival window (s) | 43200 |
| Runtime model | individual_observed_completed_first_attempt_duration_complete_groups_only |
| Arrival model | task_create_time_release_for_all_declared_instances |
| Raw rows independently verified | True |
| Exact prepared outputs recovered | True |

Sources: `RAW_Alibaba/prepared/manifest.json`, `RAW_Alibaba/config.json`, `ARNAV_Task/reports/phase3_verification.json`.
