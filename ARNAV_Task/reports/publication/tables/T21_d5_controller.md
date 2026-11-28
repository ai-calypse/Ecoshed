# D5 controller diagnostics

Existing D5 analysis, restricted to the active study. Energy change in D5 means candidate minus baseline; positive indicates a penalty, unlike energy reduction.

| Power Curve | Workload Groups | Policy | Consolidation Migrations | Evacuated Host Plans | Evacuations Over Budget | Evacuations Rolled Back | Fallback Host Checks | Lr Host Checks | Overload Migrations | Overloaded Host Ticks | Ticks | Unplaced Overload Candidates |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hpe_dl360_gen9 | 250 | lr_mmt | 80 | 22 | 0 | 13 | 576 | 8704 | 195 | 39 | 145 | 0 |
| hpe_dl360_gen9 | 250 | lr_mmt_memory | 76 | 23 | 0 | 13 | 576 | 8704 | 200 | 35 | 145 | 0 |
| hpe_dl360_gen9 | 1000 | lr_mmt | 583 | 87 | 0 | 15 | 576 | 8704 | 1051 | 176 | 145 | 0 |
| hpe_dl360_gen9 | 1000 | lr_mmt_memory | 531 | 107 | 0 | 12 | 576 | 8704 | 951 | 141 | 145 | 0 |
| hpe_dl360_gen9 | 4000 | lr_mmt | 2524 | 464 | 1 | 2 | 576 | 8704 | 5171 | 1827 | 145 | 20895 |
| hpe_dl360_gen9 | 4000 | lr_mmt_memory | 4871 | 931 | 17 | 2 | 576 | 8704 | 2351 | 1377 | 145 | 21178 |
| huawei_rh2288h_v3 | 250 | lr_mmt | 112 | 26 | 0 | 13 | 576 | 8704 | 195 | 39 | 145 | 0 |
| huawei_rh2288h_v3 | 250 | lr_mmt_memory | 76 | 23 | 0 | 13 | 576 | 8704 | 200 | 35 | 145 | 0 |
| huawei_rh2288h_v3 | 1000 | lr_mmt | 711 | 103 | 0 | 12 | 576 | 8704 | 1035 | 174 | 145 | 0 |
| huawei_rh2288h_v3 | 1000 | lr_mmt_memory | 503 | 105 | 0 | 12 | 576 | 8704 | 940 | 140 | 145 | 0 |
| huawei_rh2288h_v3 | 4000 | lr_mmt | 4588 | 725 | 22 | 3 | 576 | 8704 | 4515 | 1707 | 145 | 20694 |
| huawei_rh2288h_v3 | 4000 | lr_mmt_memory | 4807 | 915 | 5 | 2 | 576 | 8704 | 2288 | 1352 | 145 | 21063 |
| quanta_d51b_2u | 250 | lr_mmt | 80 | 22 | 0 | 13 | 576 | 8704 | 195 | 39 | 145 | 0 |
| quanta_d51b_2u | 250 | lr_mmt_memory | 76 | 23 | 0 | 13 | 576 | 8704 | 200 | 35 | 145 | 0 |
| quanta_d51b_2u | 1000 | lr_mmt | 490 | 80 | 0 | 15 | 576 | 8704 | 1050 | 176 | 145 | 0 |
| quanta_d51b_2u | 1000 | lr_mmt_memory | 545 | 106 | 0 | 13 | 576 | 8704 | 924 | 139 | 145 | 0 |
| quanta_d51b_2u | 4000 | lr_mmt | 2420 | 460 | 0 | 1 | 576 | 8704 | 4917 | 1785 | 145 | 20659 |
| quanta_d51b_2u | 4000 | lr_mmt_memory | 4790 | 930 | 11 | 2 | 576 | 8704 | 2348 | 1376 | 145 | 21198 |

Sources: `RUSHI_Task/reports/controller_diagnostics.csv`.
