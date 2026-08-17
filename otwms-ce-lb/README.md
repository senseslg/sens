# otwms-ce-lb

CE/WMS 在 GCP 上的入口、共享服务、源码/构建平台和管理后台部署记录，覆盖 `ce-lb`、`dev-lb`、`wms-db` 与 `wms-server`。

## 阅读顺序

1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：当前状态、风险和行动项。
2. [INFRASTRUCTURE_MAP.md](INFRASTRUCTURE_MAP.md)：域名、负载均衡、服务器、源码、构建与部署链路。
3. [SERVICE_INVENTORY.md](SERVICE_INVENTORY.md)：`ce-lb` 角色、域名路由和服务组件。
4. [WMS_DB_SERVER.md](WMS_DB_SERVER.md)：`wms-db`、XXL-JOB、Bitbucket、Jenkins 与共享服务。
5. [WMS_SERVER.md](WMS_SERVER.md)：CEWMS .NET 部署服务器。
6. [SSL_INVENTORY.md](SSL_INVENTORY.md)：证书、域名和续期状态。
7. [INCIDENT_2026-08-17_WMS_SERVER_DISK_FULL.md](INCIDENT_2026-08-17_WMS_SERVER_DISK_FULL.md)：`wms-server` 磁盘满载事故。
8. [INCIDENT_2026-08-16_DOMAIN_PARKING.md](INCIDENT_2026-08-16_DOMAIN_PARKING.md)：官网被 GoDaddy 停放事故。
9. [RUNBOOK.md](RUNBOOK.md)：SSH 与只读巡检方法。

## 当前重点

- 优先处理 `wms-server` 根磁盘 100% 与 inode 97% 风险；任何清理前先确认备份和恢复路径。
- 明确 Bitbucket 仓库、Jenkins Job 与 CEWMS/OTWMS 部署目标的映射。
- 立即在 GoDaddy 续费域名；解除停放后核对官网与邮件相关 DNS，当前源站仍正常。
- 修复 Certbot 的 Cron/Nginx 路径问题，并在 `2026-09-13` 前验证主域名、`www`、`cp` 自动续期。
- 处理仍在 Nginx 配置中但证书已经过期的历史域名。
- 核查 `systemd-journald` 长时间高 CPU 的原因和日志来源。
- 评估 1 核、约 1.8 GB 内存且无 Swap 的容量余量。
- 确认 MySQL `3306` 的实际网络暴露范围和访问控制。
- 确认 Nginx、MySQL 与 GCS Fuse 的启动方式和未验证业务依赖。
