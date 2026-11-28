# SPECpower model configuration

Separate measured SPECpower curves drive a CPU-request-based surrogate, with no RAM/core-count scaling. Raw watt-point arrays are retained.

| Power Curve | Role | Model | Result Id | Source | Hardware Available | Published | Sockets | Cores | Threads | Memory Gb | Watts | Mapping |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| hpe_dl360_gen9 | primary | HPE ProLiant DL360 Gen9 | 20151215-00708 | https://www.spec.org/power_ssj2008/results/res2016q1/power_ssj2008-20151215-00708.html | 2015-11 | 2016-01-07 | 2 | 36 | 72 | 64 | [45.0,83.7,101,118,133,145,162,188,218,248,276] | Same selected curve on every sampled host at requested CPU / source CPU capacity. No core-count or memory scaling. This is a surrogate sensitivity model, not Alibaba hardware calibration. |
| huawei_rh2288h_v3 | secondary | Huawei Fusion Server RH2288H V3 | 20150829-00703 | https://www.spec.org/power_ssj2008/results/res2015q3/power_ssj2008-20150829-00703.html | 2015-05 | 2015-09-25 | 2 | 36 | 72 | 64 | [44.8,83.2,96.6,110,125,141,160,183,208,237,266] | Same selected curve on every sampled host at requested CPU / source CPU capacity. No core-count or memory scaling. This is a surrogate sensitivity model, not Alibaba hardware calibration. |
| quanta_d51b_2u | third | QuantaGrid D51B-2U | 20141124-00679 | https://www.spec.org/power_ssj2008/results/res2014q4/power_ssj2008-20141124-00679.html | 2014-09 | 2014-12-10 | 2 | 36 | 72 | 64 | [49.6,88.0,104,120,137,148,169,190,217,245,272] | Same selected curve on every sampled host at requested CPU / source CPU capacity. No core-count or memory scaling. This is a surrogate sensitivity model, not Alibaba hardware calibration. |

Sources: `ecosched/power_curves.json`.
