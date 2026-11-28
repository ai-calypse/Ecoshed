# Workload groups and individual instances

Groups preserve original instance multiplicity. Skew counts are population counts, not category-specific performance outcomes.

| Groups With Variable Observed Runtime | Instance Resource Skew Counts | Instances | Task Groups |
| --- | --- | --- | --- |
| 128 | {"balanced":15217,"memory_heavy":1317} | 16534 | 250 |
| 527 | {"balanced":52062,"cpu_heavy":98,"memory_heavy":16297} | 68457 | 1000 |
| 2074 | {"balanced":303807,"cpu_heavy":748,"memory_heavy":73730} | 378285 | 4000 |

Sources: `RAW_Alibaba/prepared/manifest.json`.
