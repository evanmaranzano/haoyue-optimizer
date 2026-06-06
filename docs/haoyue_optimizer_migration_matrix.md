# 皓月定制优化工具迁移矩阵

| Legacy ID | 旧分类 | 旧风险 | 新状态 | 新预设 | 新风险 | 新 ID | 决策原因 |
|---|---|---:|---|---|---|---|---|
| gamedvr | 游戏 | LOW | planned | gaming | green | disable_gamedvr | 旧版低风险游戏录制项，副作用明确，可检测、可回滚，适合迁移。 |
| gamedvr_policy | 游戏 | LOW | merged | gaming | green | disable_gamedvr | 旧版项目与其他项目标一致，适合合并到单个新版优化项统一审计。 |
| fse | 游戏 | LOW | migrated | gaming | green | force_fse | 旧版项目边界清晰，副作用可描述，可作为新版独立优化项落位。 |
| gamemode | 游戏 | LOW | planned | gaming | green | enable_gamemode | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| hags | 游戏 | LOW | migrated | gaming | green | enable_hags | 旧版项目边界清晰，副作用可描述，可作为新版独立优化项落位。 |
| vrr | 游戏 | LOW | migrated | gaming | green | disable_vrr | 旧版项目边界清晰，副作用可描述，可作为新版独立优化项落位。 |
| mmcss_games | 游戏 | LOW | migrated | gaming | green | gaming_mmcss_games | 旧版项目边界清晰，副作用可描述，可作为新版独立优化项落位。 |
| net_throttle | 网络 | LOW | experimental | experimental | red | disable_net_throttle | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| tcp_nodelay | 网络 | LOW | experimental | experimental | red | disable_tcp_nodelay | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| dns_priority | 网络 | LOW | experimental | experimental | red | disable_dns_priority | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| dns_negative | 网络 | LOW | experimental | experimental | red | disable_dns_negative | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| qos_bw | 网络 | LOW | experimental | experimental | red | disable_qos_bw | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| qos_nla | 网络 | LOW | experimental | experimental | red | disable_qos_nla | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| net_mem | 网络 | LOW | experimental | experimental | red | disable_net_mem | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| kb_opt | 键鼠 | LOW | planned | safe | green | disable_kb_opt | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| mouse_opt | 键鼠 | LOW | planned | safe | green | disable_mouse_opt | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| sticky_keys | 键鼠 | LOW | planned | safe | green | disable_sticky_keys | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| toggle_keys | 键鼠 | LOW | planned | safe | green | disable_toggle_keys | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| access_all | 键鼠 | LOW | planned | safe | green | disable_access_all | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| ssd_opt | 磁盘 | LOW | planned | safe | green | disable_ssd_opt | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| bg_apps | 系统 | LOW | planned | privacy | green | disable_background_apps | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| transparency | 系统 | LOW | planned | safe | green | disable_transparency | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| setting_sync | 系统 | LOW | planned | privacy | green | disable_setting_sync | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| content_del | 系统 | LOW | planned | privacy | green | disable_content_delivery | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| tracking | 系统 | LOW | merged | privacy | green | disable_basic_telemetry | 旧版项目与其他项目标一致，适合合并到单个新版优化项统一审计。 |
| driver_search | 系统 | LOW | planned | privacy | green | disable_driver_search | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| telemetry | 系统 | LOW | planned | privacy | green | disable_basic_telemetry | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| svchost_thresh | 系统 | LOW | planned | safe | green | disable_svchost_thresh | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| file_alloc | 系统 | LOW | planned | safe | green | disable_file_alloc | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| admin_share | 系统 | LOW | planned | safe | green | disable_admin_share | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| autorun | 系统 | LOW | planned | safe | green | disable_autorun | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| explorer_restart | 系统 | LOW | planned | safe | green | disable_explorer_restart | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| map_download | 系统 | LOW | planned | safe | green | disable_map_download | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| feeds | 系统 | LOW | merged | privacy | green | disable_content_delivery | 旧版项目与其他项目标一致，适合合并到单个新版优化项统一审计。 |
| soft_landing | 系统 | LOW | merged | privacy | green | disable_content_delivery | 旧版项目与其他项目标一致，适合合并到单个新版优化项统一审计。 |
| wu_pause | 系统 | LOW | planned | privacy | green | extend_wu_pause_limit | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| mapsbroker | 服务 | LOW | planned | safe | green | disable_maps_broker | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| svc_safe | 服务 | LOW | planned | safe | green | disable_safe_services | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| wifi_power | 电源 | LOW | experimental | experimental | red | disable_wifi_power | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| cpu_unpark | 电源 | LOW | experimental | experimental | red | disable_cpu_unpark | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| unlock_ppm | 电源 | LOW | experimental | experimental | red | disable_unlock_ppm | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| energy_veto | 电源 | LOW | experimental | experimental | red | disable_energy_veto | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| win32_pri | 调度 | LOW | experimental | experimental | red | disable_win32_pri | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| low_latency2 | 调度 | LOW | experimental | experimental | red | disable_low_latency2 | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| dns_flush | 清理 | LOW | deprecated | experimental | red | - | 旧版为一次性命令或破坏性清理动作，不适合纳入新版可审计、可回滚预设。 |
| temp_clean | 清理 | LOW | deprecated | experimental | red | - | 旧版为一次性命令或破坏性清理动作，不适合纳入新版可审计、可回滚预设。 |
| gaming_boost | 电源 | MEDIUM | experimental | experimental | red | disable_gaming_boost | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| gaming_preset | 电源 | MEDIUM | experimental | experimental | red | disable_gaming_preset | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| power_perf | 电源 | MEDIUM | experimental | experimental | red | disable_power_perf | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| laptop_ac | 电源 | MEDIUM | experimental | experimental | red | disable_laptop_ac | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| laptop_bat | 电源 | MEDIUM | experimental | experimental | red | disable_laptop_bat | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| gpu_preempt | GPU | MEDIUM | experimental | experimental | red | disable_gpu_preempt | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| superfetch | 磁盘 | MEDIUM | experimental | experimental | red | disable_superfetch | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| large_cache | 内存 | MEDIUM | experimental | experimental | red | disable_large_cache | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| disable_mmcss | 服务 | MEDIUM | experimental | experimental | red | disable_disable_mmcss | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| disk_no_sleep | 磁盘 | MEDIUM | experimental | experimental | red | disable_disk_no_sleep | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| low_latency3 | 调度 | MEDIUM | experimental | experimental | red | disable_low_latency3 | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| wu_cache | 清理 | MEDIUM | deprecated | experimental | red | - | 旧版为一次性命令或破坏性清理动作，不适合纳入新版可审计、可回滚预设。 |
| telemetry_full | 系统 | MEDIUM | planned | privacy | red | privacy_disable_compat_tasks | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| audio_no_excl | 音频 | LOW | migrated | safe | green | disable_audio_exclusive | 旧版项目边界清晰，副作用可描述，可作为新版独立优化项落位。 |
| startup_delay | 启动 | LOW | planned | safe | green | disable_startup_delay | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| boot_timeout | 启动 | LOW | deprecated | experimental | red | - | 旧版为一次性命令或破坏性清理动作，不适合纳入新版可审计、可回滚预设。 |
| fse_global | 显示 | LOW | migrated | safe | green | disable_fullscreen_optimizations | 旧版项目边界清晰，副作用可描述，可作为新版独立优化项落位。 |
| anim_disable | 显示 | LOW | planned | safe | green | disable_anim_disable | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| usb_suspend_dis | 电源 | LOW | migrated | safe | green | gaming_usb_suspend_off | 旧版项目边界清晰，副作用可描述，可作为新版独立优化项落位。 |
| nic_nagle | 网络 | LOW | experimental | experimental | red | disable_nic_nagle | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| nic_lso_disable | 网络 | LOW | experimental | experimental | red | disable_nic_lso_disable | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| disable_prefetch | 磁盘 | LOW | planned | safe | green | disable_disable_prefetch | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| disable_bg_tasks | 系统 | LOW | planned | privacy | green | disable_disable_bg_tasks | 旧版项目已纳入迁移矩阵，但具体动作仍需逐项复核后再实现。 |
| disable_mem_compress | 内存 | MEDIUM | experimental | experimental | red | disable_disable_mem_compress | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| timer_res | 调度 | MEDIUM | experimental | experimental | red | experimental_timer_resolution_advisory | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| gpu_msi_mode | GPU | MEDIUM | experimental | experimental | red | experimental_gpu_msi_advisory | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
| nic_rss_opt | 网络 | MEDIUM | experimental | experimental | red | experimental_nic_rss_opt | 旧版项目涉及硬件、调度或系统级行为，需先保留在 experimental 或 advisory 路径。 |
