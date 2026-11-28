# Supported resource-skew outcomes

Only primary policies have category outcomes: 48 observed rows plus six explicit absent-category rows. Missing outcomes remain empty, never artificial zeros. CPU-heavy means (CPU / median host CPU) / (memory / median host memory) > 2; memory-heavy means this ratio < 0.5; otherwise balanced.

| Power Curve | Workload Groups | Policy | Task Type | Instances | Mean Wait S (seconds) | P95 Wait S (seconds) | Delayed Pct | Placed On Asleep Or Waking Server Pct | Migrated Pct (percent) | Observation Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hpe_dl360_gen9 | 250 | lr_mmt | balanced | 15217 | 8.52218 | 10 | 85.3125 | 85.3125 | 1.7809 | Observed |
| hpe_dl360_gen9 | 250 | lr_mmt | memory_heavy | 1317 | 7.25133 | 10 | 72.5133 | 72.5133 | 0.303721 | Observed |
| hpe_dl360_gen9 | 250 | lr_mmt | cpu_heavy | — | — | — | — | — | — | No observations |
| hpe_dl360_gen9 | 250 | lr_mmt_memory | balanced | 15217 | 8.47408 | 10 | 84.8262 | 84.8262 | 1.7349 | Observed |
| hpe_dl360_gen9 | 250 | lr_mmt_memory | memory_heavy | 1317 | 7.60061 | 10 | 76.0061 | 76.0061 | 0.911162 | Observed |
| hpe_dl360_gen9 | 250 | lr_mmt_memory | cpu_heavy | — | — | — | — | — | — | No observations |
| huawei_rh2288h_v3 | 250 | lr_mmt | balanced | 15217 | 8.52218 | 10 | 85.3125 | 85.3125 | 1.95176 | Observed |
| huawei_rh2288h_v3 | 250 | lr_mmt | memory_heavy | 1317 | 7.25133 | 10 | 72.5133 | 72.5133 | 0.759301 | Observed |
| huawei_rh2288h_v3 | 250 | lr_mmt | cpu_heavy | — | — | — | — | — | — | No observations |
| huawei_rh2288h_v3 | 250 | lr_mmt_memory | balanced | 15217 | 8.47408 | 10 | 84.8262 | 84.8262 | 1.7349 | Observed |
| huawei_rh2288h_v3 | 250 | lr_mmt_memory | memory_heavy | 1317 | 7.60061 | 10 | 76.0061 | 76.0061 | 0.911162 | Observed |
| huawei_rh2288h_v3 | 250 | lr_mmt_memory | cpu_heavy | — | — | — | — | — | — | No observations |
| quanta_d51b_2u | 250 | lr_mmt | balanced | 15217 | 8.52218 | 10 | 85.3125 | 85.3125 | 1.7809 | Observed |
| quanta_d51b_2u | 250 | lr_mmt | memory_heavy | 1317 | 7.25133 | 10 | 72.5133 | 72.5133 | 0.303721 | Observed |
| quanta_d51b_2u | 250 | lr_mmt | cpu_heavy | — | — | — | — | — | — | No observations |
| quanta_d51b_2u | 250 | lr_mmt_memory | balanced | 15217 | 8.47408 | 10 | 84.8262 | 84.8262 | 1.7349 | Observed |
| quanta_d51b_2u | 250 | lr_mmt_memory | memory_heavy | 1317 | 7.60061 | 10 | 76.0061 | 76.0061 | 0.911162 | Observed |
| quanta_d51b_2u | 250 | lr_mmt_memory | cpu_heavy | — | — | — | — | — | — | No observations |
| hpe_dl360_gen9 | 1000 | lr_mmt | balanced | 52062 | 5.4383 | 10 | 54.9115 | 54.9115 | 2.03795 | Observed |
| hpe_dl360_gen9 | 1000 | lr_mmt | memory_heavy | 16297 | 6.46892 | 10 | 64.7052 | 64.7052 | 3.42394 | Observed |
| hpe_dl360_gen9 | 1000 | lr_mmt | cpu_heavy | 98 | 1.02041 | 10 | 10.2041 | 10.2041 | 15.3061 | Observed |
| hpe_dl360_gen9 | 1000 | lr_mmt_memory | balanced | 52062 | 4.90767 | 10 | 49.7234 | 49.7234 | 1.8574 | Observed |
| hpe_dl360_gen9 | 1000 | lr_mmt_memory | memory_heavy | 16297 | 5.71627 | 10 | 57.2007 | 57.2007 | 3.08646 | Observed |
| hpe_dl360_gen9 | 1000 | lr_mmt_memory | cpu_heavy | 98 | 1.02041 | 10 | 10.2041 | 10.2041 | 12.2449 | Observed |
| huawei_rh2288h_v3 | 1000 | lr_mmt | balanced | 52062 | 5.06095 | 10 | 51.0756 | 51.0756 | 2.18201 | Observed |
| huawei_rh2288h_v3 | 1000 | lr_mmt | memory_heavy | 16297 | 6.283 | 10 | 62.8459 | 62.8459 | 3.63257 | Observed |
| huawei_rh2288h_v3 | 1000 | lr_mmt | cpu_heavy | 98 | 1.02041 | 10 | 10.2041 | 10.2041 | 18.3673 | Observed |
| huawei_rh2288h_v3 | 1000 | lr_mmt_memory | balanced | 52062 | 4.87597 | 10 | 49.4065 | 49.4065 | 1.79401 | Observed |
| huawei_rh2288h_v3 | 1000 | lr_mmt_memory | memory_heavy | 16297 | 5.65491 | 10 | 56.5871 | 56.5871 | 3.04964 | Observed |
| huawei_rh2288h_v3 | 1000 | lr_mmt_memory | cpu_heavy | 98 | 1.02041 | 10 | 10.2041 | 10.2041 | 12.2449 | Observed |
| quanta_d51b_2u | 1000 | lr_mmt | balanced | 52062 | 5.44082 | 10 | 54.9345 | 54.9345 | 1.85356 | Observed |
| quanta_d51b_2u | 1000 | lr_mmt | memory_heavy | 16297 | 6.46217 | 10 | 64.6377 | 64.6377 | 3.43622 | Observed |
| quanta_d51b_2u | 1000 | lr_mmt | cpu_heavy | 98 | 1.02041 | 10 | 10.2041 | 10.2041 | 15.3061 | Observed |
| quanta_d51b_2u | 1000 | lr_mmt_memory | balanced | 52062 | 4.92029 | 10 | 49.8483 | 49.8483 | 1.82475 | Observed |
| quanta_d51b_2u | 1000 | lr_mmt_memory | memory_heavy | 16297 | 5.70706 | 10 | 57.1087 | 57.1087 | 3.111 | Observed |
| quanta_d51b_2u | 1000 | lr_mmt_memory | cpu_heavy | 98 | 1.02041 | 10 | 10.2041 | 10.2041 | 12.2449 | Observed |
| hpe_dl360_gen9 | 4000 | lr_mmt | balanced | 303807 | 53.3306 | 112 | 52.7891 | 36.2283 | 1.43381 | Observed |
| hpe_dl360_gen9 | 4000 | lr_mmt | memory_heavy | 73730 | 67.3391 | 523 | 41.8093 | 31.3482 | 4.37814 | Observed |
| hpe_dl360_gen9 | 4000 | lr_mmt | cpu_heavy | 748 | 53.7204 | 8 | 12.7005 | 7.8877 | 13.6364 | Observed |
| hpe_dl360_gen9 | 4000 | lr_mmt_memory | balanced | 303807 | 51.7812 | 110 | 38.4784 | 22.1769 | 1.40813 | Observed |
| hpe_dl360_gen9 | 4000 | lr_mmt_memory | memory_heavy | 73730 | 65.5592 | 521 | 25.2285 | 14.8244 | 3.86546 | Observed |
| hpe_dl360_gen9 | 4000 | lr_mmt_memory | cpu_heavy | 748 | 53.492 | 7 | 11.7647 | 6.95187 | 11.4973 | Observed |
| huawei_rh2288h_v3 | 4000 | lr_mmt | balanced | 303807 | 52.8955 | 110 | 48.1016 | 31.5928 | 1.73663 | Observed |
| huawei_rh2288h_v3 | 4000 | lr_mmt | memory_heavy | 73730 | 66.7035 | 523 | 35.3628 | 24.9152 | 5.06442 | Observed |
| huawei_rh2288h_v3 | 4000 | lr_mmt | cpu_heavy | 748 | 53.6511 | 8 | 12.1658 | 7.35294 | 11.8984 | Observed |
| huawei_rh2288h_v3 | 4000 | lr_mmt_memory | balanced | 303807 | 51.8723 | 110 | 39.0537 | 22.7305 | 1.39069 | Observed |
| huawei_rh2288h_v3 | 4000 | lr_mmt_memory | memory_heavy | 73730 | 65.6282 | 523 | 25.4211 | 14.998 | 3.75424 | Observed |
| huawei_rh2288h_v3 | 4000 | lr_mmt_memory | cpu_heavy | 748 | 53.512 | 7 | 11.3636 | 6.5508 | 12.7005 | Observed |
| quanta_d51b_2u | 4000 | lr_mmt | balanced | 303807 | 53.2729 | 112 | 52.3336 | 35.7872 | 1.32189 | Observed |
| quanta_d51b_2u | 4000 | lr_mmt | memory_heavy | 73730 | 67.2147 | 523 | 40.7446 | 30.2835 | 4.35644 | Observed |
| quanta_d51b_2u | 4000 | lr_mmt | cpu_heavy | 748 | 53.7072 | 8 | 12.2995 | 7.48663 | 13.7701 | Observed |
| quanta_d51b_2u | 4000 | lr_mmt_memory | balanced | 303807 | 51.7756 | 110 | 38.4711 | 22.1552 | 1.42492 | Observed |
| quanta_d51b_2u | 4000 | lr_mmt_memory | memory_heavy | 73730 | 65.6313 | 522 | 26.0789 | 15.6571 | 3.70134 | Observed |
| quanta_d51b_2u | 4000 | lr_mmt_memory | cpu_heavy | 748 | 53.3382 | 3 | 9.35829 | 4.54545 | 9.75936 | Observed |

Sources: `RUSHI_Task/reports/outcomes_by_task_type.csv`.
