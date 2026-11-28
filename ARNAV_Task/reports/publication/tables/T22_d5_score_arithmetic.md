# D5 placement score arithmetic

Existing D5 analysis, restricted to the active study. Energy change in D5 means candidate minus baseline; positive indicates a penalty, unlike energy reduction.

| Power Curve | Sleep Watts | Idle Watts | Full Watts | First Band Added Watts | Cheapest Band | Cheapest Band Added Watts | Memory Balance Weight | Wake Score Cost | Balance Gain Needed To Justify A Wakeup Pct Points | Median Task Cpu Fraction | Median Task Memory Fraction | Typical Busy Server Cpu | Typical Busy Server Memory | Power Score Advantage Of Busy Server | Balance Penalty Typical Busy Server | Balance Penalty Empty Server | Balance Advantage Over Power Advantage | Balance Gain Needed To Prefer Empty Server Pct Points |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hpe_dl360_gen9 | 5 | 45 | 276 | 38.7 | 40-50% | 12 | 0.25 | 0.17316 | 69.2641 | 0.0078125 | 0.0116743 | 0.297314 | 0.568904 | 0.00778285 | 0.0678975 | 0.000965455 | 8.59994 | 3.11314 |
| huawei_rh2288h_v3 | 5 | 44.8 | 266 | 38.4 | 10-20% | 13.4 | 0.25 | 0.179928 | 71.9711 | 0.0078125 | 0.0116743 | 0.249118 | 0.501488 | 0.00882968 | 0.0630924 | 0.000965455 | 7.03615 | 3.53187 |
| quanta_d51b_2u | 5 | 49.6 | 272 | 38.4 | 40-50% | 11 | 0.25 | 0.20054 | 80.2158 | 0.0078125 | 0.0116743 | 0.297421 | 0.568074 | 0.00763338 | 0.0676633 | 0.000965455 | 8.73766 | 3.05335 |

Sources: `RUSHI_Task/reports/placement_score_arithmetic.csv`.
