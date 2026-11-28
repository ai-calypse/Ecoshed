# Fixed simulator and sampling configuration

Fixed simulation assumptions. Memory-unit conversion and independent per-transfer bandwidth are modeling assumptions, not Alibaba measurements.

| Parameter | Value |
| --- | --- |
| source | user_downloaded_alibaba_v2017_archive |
| source_repository | https://github.com/alibaba/clusterdata/tree/master/cluster-trace-v2017 |
| window_start_s | 0 |
| window_end_s | 43200 |
| host_count | 64 |
| workload_group_counts | [250,1000,4000] |
| seed | 2026 |
| arrival_bin_s | 900 |
| cpu_request_divisor | 100 |
| runtime_model | individual_observed_completed_first_attempt_duration_complete_groups_only |
| arrival_model | task_create_time_release_for_all_declared_instances |
| background_online_load | False |
| replay_failures | False |
| arrival_window_s | 43200 |
| idle_timeout_s | 60 |
| sleep_watts | 5 |
| wake_latency_s | 10 |
| wake_energy_j | 0 |
| control_interval_s | 300 |
| overload_threshold | 0.9 |
| memory_unit_bytes | 68719476736 |
| migration_bandwidth_bytes_s | 1.25e+08 |
| migration_extra_watts | 0 |
| history_length | 10 |
| safety_factor | 1.2 |
| fallback_threshold | 0.9 |
| underload_threshold | 0.3 |
| memory_balance_weight | 0.25 |
| cooldown_s | 600 |
| max_migrations_per_tick | 256 |

Sources: `RAW_Alibaba/config.json`, `ROHAN_Task/config/default.json`.
