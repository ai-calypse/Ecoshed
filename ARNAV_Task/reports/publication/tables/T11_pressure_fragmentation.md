# Reservation pressure, fragmentation and stranded capacity

Reservation pressure is a modeled overload/SLA proxy, not application SLA violations. Stranded capacity has time-integrated units.

| Workload Groups | Power Curve | Policy | Overload Host Time Fraction (fraction) | Mean Fragmentation Index (fraction) | Cpu Stranded By Memory Core Seconds (core-seconds) | Memory Stranded By Cpu Unit Seconds (normalized-unit-seconds) | Source Individual Summary |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 250 | hpe_dl360_gen9 | first_fit | 0.00432473 | 0.000331744 | 62,721.5 | 38.1493 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_250/hpe_dl360_gen9/first_fit/summary.json |
| 250 | hpe_dl360_gen9 | best_fit | 0.004426 | 0.000331771 | 74,615.5 | 38.1507 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_250/hpe_dl360_gen9/best_fit/summary.json |
| 250 | hpe_dl360_gen9 | lr_mmt | 0.00372961 | 0.000235558 | 70,352.8 | 38.1507 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_250/hpe_dl360_gen9/lr_mmt/summary.json |
| 250 | hpe_dl360_gen9 | lr_mmt_memory | 0.00317959 | 0.000209345 | 36,037.5 | 65.4128 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_250/hpe_dl360_gen9/lr_mmt_memory/summary.json |
| 250 | huawei_rh2288h_v3 | first_fit | 0.00432473 | 0.000331744 | 62,721.5 | 38.1493 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_250/huawei_rh2288h_v3/first_fit/summary.json |
| 250 | huawei_rh2288h_v3 | best_fit | 0.004426 | 0.000331771 | 74,615.5 | 38.1507 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_250/huawei_rh2288h_v3/best_fit/summary.json |
| 250 | huawei_rh2288h_v3 | lr_mmt | 0.00372491 | 0.000235548 | 69,847.8 | 38.1507 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_250/huawei_rh2288h_v3/lr_mmt/summary.json |
| 250 | huawei_rh2288h_v3 | lr_mmt_memory | 0.00317923 | 0.000209345 | 36,037.5 | 65.4128 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_250/huawei_rh2288h_v3/lr_mmt_memory/summary.json |
| 250 | quanta_d51b_2u | first_fit | 0.00432473 | 0.000331744 | 62,721.5 | 38.1493 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_250/quanta_d51b_2u/first_fit/summary.json |
| 250 | quanta_d51b_2u | best_fit | 0.004426 | 0.000331771 | 74,615.5 | 38.1507 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_250/quanta_d51b_2u/best_fit/summary.json |
| 250 | quanta_d51b_2u | lr_mmt | 0.00373105 | 0.000235752 | 70,352.8 | 38.1507 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_250/quanta_d51b_2u/lr_mmt/summary.json |
| 250 | quanta_d51b_2u | lr_mmt_memory | 0.00317996 | 0.000209345 | 36,037.5 | 65.7602 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_250/quanta_d51b_2u/lr_mmt_memory/summary.json |
| 1000 | hpe_dl360_gen9 | first_fit | 0.0211791 | 0.00374727 | 1.29182e+06 | 73.7465 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_1000/hpe_dl360_gen9/first_fit/summary.json |
| 1000 | hpe_dl360_gen9 | best_fit | 0.0213874 | 0.00399932 | 1.33266e+06 | 70.9254 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_1000/hpe_dl360_gen9/best_fit/summary.json |
| 1000 | hpe_dl360_gen9 | lr_mmt | 0.0182618 | 0.0031575 | 1.18068e+06 | 74.2181 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_1000/hpe_dl360_gen9/lr_mmt/summary.json |
| 1000 | hpe_dl360_gen9 | lr_mmt_memory | 0.0144211 | 0.0030322 | 857,536 | 166.22 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_1000/hpe_dl360_gen9/lr_mmt_memory/summary.json |
| 1000 | huawei_rh2288h_v3 | first_fit | 0.0211791 | 0.00374727 | 1.29182e+06 | 73.7465 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_1000/huawei_rh2288h_v3/first_fit/summary.json |
| 1000 | huawei_rh2288h_v3 | best_fit | 0.0213874 | 0.00399932 | 1.33266e+06 | 70.9254 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_1000/huawei_rh2288h_v3/best_fit/summary.json |
| 1000 | huawei_rh2288h_v3 | lr_mmt | 0.0178216 | 0.00252425 | 1.14954e+06 | 120.866 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_1000/huawei_rh2288h_v3/lr_mmt/summary.json |
| 1000 | huawei_rh2288h_v3 | lr_mmt_memory | 0.0145488 | 0.0043596 | 868,047 | 159.185 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_1000/huawei_rh2288h_v3/lr_mmt_memory/summary.json |
| 1000 | quanta_d51b_2u | first_fit | 0.0211791 | 0.00374727 | 1.29182e+06 | 73.7465 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_1000/quanta_d51b_2u/first_fit/summary.json |
| 1000 | quanta_d51b_2u | best_fit | 0.0213874 | 0.00399932 | 1.33266e+06 | 70.9254 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_1000/quanta_d51b_2u/best_fit/summary.json |
| 1000 | quanta_d51b_2u | lr_mmt | 0.0181046 | 0.00314507 | 1.17184e+06 | 84.9581 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_1000/quanta_d51b_2u/lr_mmt/summary.json |
| 1000 | quanta_d51b_2u | lr_mmt_memory | 0.0145335 | 0.00294611 | 863,873 | 165.64 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_1000/quanta_d51b_2u/lr_mmt_memory/summary.json |
| 4000 | hpe_dl360_gen9 | first_fit | 0.196246 | 0.0236728 | 1.89952e+07 | 969.691 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_4000/hpe_dl360_gen9/first_fit/summary.json |
| 4000 | hpe_dl360_gen9 | best_fit | 0.198003 | 0.0215404 | 1.91787e+07 | 830.493 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_4000/hpe_dl360_gen9/best_fit/summary.json |
| 4000 | hpe_dl360_gen9 | lr_mmt | 0.184662 | 0.0198375 | 1.82202e+07 | 756.817 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_4000/hpe_dl360_gen9/lr_mmt/summary.json |
| 4000 | hpe_dl360_gen9 | lr_mmt_memory | 0.140692 | 0.00861464 | 1.50914e+07 | 454.52 | RAW_Alibaba/reports/runs/hpe_dl360_gen9/workload_4000/hpe_dl360_gen9/lr_mmt_memory/summary.json |
| 4000 | huawei_rh2288h_v3 | first_fit | 0.196246 | 0.0236728 | 1.89952e+07 | 969.691 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_4000/huawei_rh2288h_v3/first_fit/summary.json |
| 4000 | huawei_rh2288h_v3 | best_fit | 0.198003 | 0.0215404 | 1.91787e+07 | 830.493 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_4000/huawei_rh2288h_v3/best_fit/summary.json |
| 4000 | huawei_rh2288h_v3 | lr_mmt | 0.172556 | 0.0159108 | 1.73958e+07 | 820.348 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_4000/huawei_rh2288h_v3/lr_mmt/summary.json |
| 4000 | huawei_rh2288h_v3 | lr_mmt_memory | 0.140201 | 0.0111635 | 1.5091e+07 | 492.088 | RAW_Alibaba/reports/runs/huawei_rh2288h_v3/workload_4000/huawei_rh2288h_v3/lr_mmt_memory/summary.json |
| 4000 | quanta_d51b_2u | first_fit | 0.196246 | 0.0236728 | 1.89952e+07 | 969.691 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_4000/quanta_d51b_2u/first_fit/summary.json |
| 4000 | quanta_d51b_2u | best_fit | 0.198003 | 0.0215404 | 1.91787e+07 | 830.493 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_4000/quanta_d51b_2u/best_fit/summary.json |
| 4000 | quanta_d51b_2u | lr_mmt | 0.178692 | 0.0192618 | 1.77878e+07 | 805.835 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_4000/quanta_d51b_2u/lr_mmt/summary.json |
| 4000 | quanta_d51b_2u | lr_mmt_memory | 0.141207 | 0.0100375 | 1.51604e+07 | 433.145 | RAW_Alibaba/reports/runs/quanta_d51b_2u/workload_4000/quanta_d51b_2u/lr_mmt_memory/summary.json |

Sources: `BASELINE_Comparison/reports/summaries.json`.
