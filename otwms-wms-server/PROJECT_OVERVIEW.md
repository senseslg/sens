# WMS Server Overview

## 目标与范围

维护 GCP `wms-server` 的访问方式、CEWMS 与 `cp` 后端服务边界、容量风险和故障恢复记录。生产检查默认只读；重启、扩容、清理和配置修改需明确授权。

## 当前状态（2026-09-18，容量优化后）

| 项目 | 已确认状态 |
|---|---|
| 实例 | `cambodian-express` / `asia-southeast1-a`，`e2-small`、CentOS 7，无公网 IP；通过 IAP SSH 可登录 |
| 根分区 | 600 GB XFS，约 35 GB 已用、**566 GB 可用（6%）**；inode 约 1% 已用 |
| 内存 | 约 1.8 GB；**已配置 2 GB Swap**（`/swapfile`，持久化到 `/etc/fstab`） |
| 服务 | `cewms.service` + `cp.service` 均 active；80/90 端口正常 |
| 恢复点 | 快照 `wms-server-pre-reset-20260917` 为 `READY` |
| 日志清理 | cron `/etc/cron.d/disk-maintenance`：每 6 小时检查磁盘，每日 03:00 删除超 30 天应用日志，磁盘 ≥80% 写 syslog + 发 root 邮件 |

2026-09-18 容量优化：删除废弃 `spider.log`（406 GB）、2021 年旧 SQL 备份（56 GB）及历史日志（约 7 GB），共释放约 469 GB。同步完成：
- `/usr/local/bin/disk-maintenance.sh` — 日志清理 + 磁盘告警脚本
- `/etc/cron.d/disk-maintenance` — 定时触发
- 2 GB Swap（`/swapfile`）避免内存不足时 OOM

## 剩余风险与下一步

- [x] 历史大文件（`spider.log`、旧 SQL 备份）已清理（2026-09-18）。
- [x] 磁盘空间告警已建立（`disk-maintenance` cron，≥80% 触发）。
- [x] Swap 已配置，OOM 风险降低。
- [ ] 核实 90 端口服务名称（`cp.service`）与持久化依赖，确定快照保留周期。
- [ ] 规划 CentOS 7 迁移（EOL 已过）。
- [ ] 验证磁盘告警邮件能否实际送达（postfix/root 邮箱）。

登录和只读检查步骤见 [RUNBOOK.md](RUNBOOK.md)，服务边界见 [SERVICE_INVENTORY.md](SERVICE_INVENTORY.md)。
