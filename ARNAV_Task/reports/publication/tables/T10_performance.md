# Hosts, migrations and waiting outcomes

P95 values are individual-run quantiles; no averaging across runs. Pause is accumulated instance-seconds, not elapsed experiment overhead.

| Workload Groups | Power Curve | Policy | Mean Active Hosts (hosts) | Peak Active Hosts (hosts) | Migrations (transfers) | Migration Pause Instance Seconds (instance-seconds) | Mean Wait S (seconds) | P95 Wait S (seconds) | Rejected Instances (instances) | Unfinished Instances (instances) | Source Individual Summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 250 | hpe_dl360_gen9 | first_fit | 1.21012 | 13 | 0 | 0 | 8.45428 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_250/hpe_dl360_gen9/first_fit/summary.json |
| 250 | hpe_dl360_gen9 | best_fit | 1.2184 | 14 | 0 | 0 | 8.4821 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_250/hpe_dl360_gen9/best_fit/summary.json |
| 250 | hpe_dl360_gen9 | lr_mmt | 1.23448 | 15 | 275 | 2,336.36 | 8.42095 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_250/hpe_dl360_gen9/lr_mmt/summary.json |
| 250 | hpe_dl360_gen9 | lr_mmt_memory | 1.19454 | 14 | 276 | 2,607.39 | 8.4045 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_250/hpe_dl360_gen9/lr_mmt_memory/summary.json |
| 250 | huawei_rh2288h_v3 | first_fit | 1.21012 | 13 | 0 | 0 | 8.45428 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_250/huawei_rh2288h_v3/first_fit/summary.json |
| 250 | huawei_rh2288h_v3 | best_fit | 1.2184 | 14 | 0 | 0 | 8.4821 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_250/huawei_rh2288h_v3/best_fit/summary.json |
| 250 | huawei_rh2288h_v3 | lr_mmt | 1.24996 | 15 | 307 | 2,462.41 | 8.42095 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_250/huawei_rh2288h_v3/lr_mmt/summary.json |
| 250 | huawei_rh2288h_v3 | lr_mmt_memory | 1.19454 | 14 | 276 | 2,607.39 | 8.4045 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_250/huawei_rh2288h_v3/lr_mmt_memory/summary.json |
| 250 | quanta_d51b_2u | first_fit | 1.21012 | 13 | 0 | 0 | 8.45428 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_250/quanta_d51b_2u/first_fit/summary.json |
| 250 | quanta_d51b_2u | best_fit | 1.2184 | 14 | 0 | 0 | 8.4821 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_250/quanta_d51b_2u/best_fit/summary.json |
| 250 | quanta_d51b_2u | lr_mmt | 1.23448 | 15 | 275 | 2,336.36 | 8.42095 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_250/quanta_d51b_2u/lr_mmt/summary.json |
| 250 | quanta_d51b_2u | lr_mmt_memory | 1.19449 | 14 | 276 | 2,607.39 | 8.4045 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_250/quanta_d51b_2u/lr_mmt_memory/summary.json |
| 1000 | hpe_dl360_gen9 | first_fit | 4.35488 | 34 | 0 | 0 | 5.66228 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_1000/hpe_dl360_gen9/first_fit/summary.json |
| 1000 | hpe_dl360_gen9 | best_fit | 4.37512 | 34 | 0 | 0 | 5.67645 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_1000/hpe_dl360_gen9/best_fit/summary.json |
| 1000 | hpe_dl360_gen9 | lr_mmt | 4.42319 | 34 | 1634 | 12,702.1 | 5.67733 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_1000/hpe_dl360_gen9/lr_mmt/summary.json |
| 1000 | hpe_dl360_gen9 | lr_mmt_memory | 4.72222 | 34 | 1482 | 11,493.3 | 5.0946 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_1000/hpe_dl360_gen9/lr_mmt_memory/summary.json |
| 1000 | huawei_rh2288h_v3 | first_fit | 4.35488 | 34 | 0 | 0 | 5.66228 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_1000/huawei_rh2288h_v3/first_fit/summary.json |
| 1000 | huawei_rh2288h_v3 | best_fit | 4.37512 | 34 | 0 | 0 | 5.67645 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_1000/huawei_rh2288h_v3/best_fit/summary.json |
| 1000 | huawei_rh2288h_v3 | lr_mmt | 4.65277 | 34 | 1746 | 13,030.5 | 5.34609 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_1000/huawei_rh2288h_v3/lr_mmt/summary.json |
| 1000 | huawei_rh2288h_v3 | lr_mmt_memory | 4.7154 | 34 | 1443 | 11,794 | 5.05589 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_1000/huawei_rh2288h_v3/lr_mmt_memory/summary.json |
| 1000 | quanta_d51b_2u | first_fit | 4.35488 | 34 | 0 | 0 | 5.66228 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_1000/quanta_d51b_2u/first_fit/summary.json |
| 1000 | quanta_d51b_2u | best_fit | 4.37512 | 34 | 0 | 0 | 5.67645 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_1000/quanta_d51b_2u/best_fit/summary.json |
| 1000 | quanta_d51b_2u | lr_mmt | 4.44013 | 34 | 1540 | 12,591.4 | 5.67764 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_1000/quanta_d51b_2u/lr_mmt/summary.json |
| 1000 | quanta_d51b_2u | lr_mmt_memory | 4.73743 | 34 | 1469 | 11,937 | 5.10201 | 10 | 0 | 0 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_1000/quanta_d51b_2u/lr_mmt_memory/summary.json |
| 4000 | hpe_dl360_gen9 | first_fit | 23.8671 | 64 | 0 | 0 | 55.9592 | 465 | 0 | 0 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_4000/hpe_dl360_gen9/first_fit/summary.json |
| 4000 | hpe_dl360_gen9 | best_fit | 23.9259 | 64 | 0 | 0 | 56.0278 | 465 | 0 | 0 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_4000/hpe_dl360_gen9/best_fit/summary.json |
| 4000 | hpe_dl360_gen9 | lr_mmt | 23.9685 | 64 | 7695 | 64,496.1 | 56.0617 | 466 | 0 | 0 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_4000/hpe_dl360_gen9/lr_mmt/summary.json |
| 4000 | hpe_dl360_gen9 | lr_mmt_memory | 32.6065 | 64 | 7222 | 53,022.2 | 54.47 | 465 | 0 | 0 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_4000/hpe_dl360_gen9/lr_mmt_memory/summary.json |
| 4000 | huawei_rh2288h_v3 | first_fit | 23.8671 | 64 | 0 | 0 | 55.9592 | 465 | 0 | 0 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_4000/huawei_rh2288h_v3/first_fit/summary.json |
| 4000 | huawei_rh2288h_v3 | best_fit | 23.9259 | 64 | 0 | 0 | 56.0278 | 465 | 0 | 0 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_4000/huawei_rh2288h_v3/best_fit/summary.json |
| 4000 | huawei_rh2288h_v3 | lr_mmt | 25.8588 | 64 | 9103 | 70,617.5 | 55.5883 | 466 | 0 | 0 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_4000/huawei_rh2288h_v3/lr_mmt/summary.json |
| 4000 | huawei_rh2288h_v3 | lr_mmt_memory | 32.4964 | 64 | 7095 | 51,170.5 | 54.5567 | 465 | 0 | 0 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_4000/huawei_rh2288h_v3/lr_mmt_memory/summary.json |
| 4000 | quanta_d51b_2u | first_fit | 23.8671 | 64 | 0 | 0 | 55.9592 | 465 | 0 | 0 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_4000/quanta_d51b_2u/first_fit/summary.json |
| 4000 | quanta_d51b_2u | best_fit | 23.9259 | 64 | 0 | 0 | 56.0278 | 465 | 0 | 0 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_4000/quanta_d51b_2u/best_fit/summary.json |
| 4000 | quanta_d51b_2u | lr_mmt | 24.1834 | 64 | 7337 | 63,153.2 | 55.9911 | 465 | 0 | 0 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_4000/quanta_d51b_2u/lr_mmt/summary.json |
| 4000 | quanta_d51b_2u | lr_mmt_memory | 32.5724 | 64 | 7138 | 52,007.8 | 54.4792 | 465 | 0 | 0 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_4000/quanta_d51b_2u/lr_mmt_memory/summary.json |

Sources: `BASELINE_Comparison/reports/summaries.json`.
