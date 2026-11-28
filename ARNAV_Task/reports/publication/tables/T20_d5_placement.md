# D5 placement decisions

Existing D5 analysis, restricted to the active study. Energy change in D5 means candidate minus baseline; positive indicates a penalty, unlike energy reduction.

| Power Curve | Workload Groups | Policy | Placements | To Sleeping Pct | To Waking Pct | To On Empty Pct | To On Running Pct | Mean Cpu Of Chosen Server After | Rules Disagree Pct | Disagreements Own Pick Less Loaded Pct | Other Rule Would Use Empty Server Instead Pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hpe_dl360_gen9 | 250 | lr_mmt | 16534 | 1.74791 | 82.5451 | 0.368937 | 15.3381 | 0.335615 | 5.92113 | 2.14505 | 2.68538 |
| hpe_dl360_gen9 | 250 | lr_mmt_memory | 16534 | 1.61485 | 82.5088 | 0.4899 | 15.3865 | 0.375709 | 4.2458 | 39.886 | 0 |
| hpe_dl360_gen9 | 1000 | lr_mmt | 68457 | 1.04445 | 56.1345 | 0.430927 | 42.3901 | 0.335227 | 26.3611 | 1.98936 | 13.4668 |
| hpe_dl360_gen9 | 1000 | lr_mmt_memory | 68457 | 0.879384 | 50.5675 | 0.942197 | 47.6109 | 0.346762 | 28.3214 | 59.3254 | 0.375418 |
| hpe_dl360_gen9 | 4000 | lr_mmt | 378285 | 0.512576 | 34.7085 | 0.208837 | 64.5701 | 0.419519 | 55.0048 | 16.7387 | 21.6028 |
| hpe_dl360_gen9 | 4000 | lr_mmt_memory | 378285 | 0.29105 | 20.4227 | 0.982857 | 78.3034 | 0.382311 | 68.0291 | 62.1153 | 0.0853854 |
| huawei_rh2288h_v3 | 250 | lr_mmt | 16534 | 1.74791 | 82.5451 | 0.411274 | 15.2958 | 0.334568 | 5.64897 | 2.89079 | 0.907221 |
| huawei_rh2288h_v3 | 250 | lr_mmt_memory | 16534 | 1.61485 | 82.5088 | 0.4899 | 15.3865 | 0.375712 | 4.45143 | 30.7065 | 0 |
| huawei_rh2288h_v3 | 1000 | lr_mmt | 68457 | 0.994785 | 52.8244 | 0.612063 | 45.5688 | 0.330003 | 28.7976 | 5.29066 | 5.85331 |
| huawei_rh2288h_v3 | 1000 | lr_mmt_memory | 68457 | 0.87062 | 50.1892 | 0.940737 | 47.9995 | 0.34707 | 28.802 | 33.854 | 0.356428 |
| huawei_rh2288h_v3 | 4000 | lr_mmt | 378285 | 0.434064 | 29.8093 | 0.454948 | 69.3017 | 0.40559 | 60.7304 | 23.6243 | 13.5628 |
| huawei_rh2288h_v3 | 4000 | lr_mmt_memory | 378285 | 0.294223 | 20.8972 | 0.967789 | 77.8408 | 0.381352 | 69.888 | 34.6639 | 0.0758687 |
| quanta_d51b_2u | 250 | lr_mmt | 16534 | 1.74791 | 82.5451 | 0.368937 | 15.3381 | 0.335709 | 5.90904 | 0.614125 | 2.66723 |
| quanta_d51b_2u | 250 | lr_mmt_memory | 16534 | 1.61485 | 82.5088 | 0.4899 | 15.3865 | 0.375717 | 4.30628 | 34.691 | 0 |
| quanta_d51b_2u | 1000 | lr_mmt | 68457 | 1.04299 | 56.1374 | 0.422163 | 42.3974 | 0.334316 | 26.3771 | 3.86 | 13.2098 |
| quanta_d51b_2u | 1000 | lr_mmt_memory | 68457 | 0.877923 | 50.642 | 0.940737 | 47.5393 | 0.346472 | 27.6816 | 44.2744 | 0.311144 |
| quanta_d51b_2u | 4000 | lr_mmt | 378285 | 0.503324 | 34.1552 | 0.208044 | 65.1334 | 0.414249 | 56.6147 | 22.8455 | 21.6472 |
| quanta_d51b_2u | 4000 | lr_mmt_memory | 378285 | 0.293694 | 20.5602 | 0.982064 | 78.1641 | 0.381269 | 68.5988 | 51.6129 | 0.045204 |

Sources: `RUSHI_Task/reports/placement_decisions.csv`.
