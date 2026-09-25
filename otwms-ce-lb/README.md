# otwms-ce-lb

CE/WMS 在 GCP 上的入口、共享服务、源码/构建平台和管理后台部署记录，覆盖 `ce-lb`、`dev-lb`、`wms-db` 与 `wms-server`。

## 阅读顺序

1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：当前状态、风险和行动项。
2. [INFRASTRUCTURE_MAP.md](INFRASTRUCTURE_MAP.md)：域名、负载均衡、服务器、源码、构建与部署链路。
3. [SERVICE_INVENTORY.md](SERVICE_INVENTORY.md)：`ce-lb` 角色、域名路由和服务组件。
4. [WMS_DB_SERVER.md](WMS_DB_SERVER.md)：`wms-db`、XXL-JOB、Bitbucket、Jenkins 与共享服务。
5. [WMS_SERVER.md](WMS_SERVER.md)：CEWMS .NET 部署服务器。
   当前访问与故障状态以 [otwms-wms-server](../otwms-wms-server/README.md) 为准。
6. [SSL_INVENTORY.md](SSL_INVENTORY.md)：证书、域名和续期状态。
7. [INCIDENT_2026-08-17_WMS_SERVER_DISK_FULL.md](INCIDENT_2026-08-17_WMS_SERVER_DISK_FULL.md)：`wms-server` 磁盘满载事故。
8. [INCIDENT_2026-08-16_DOMAIN_PARKING.md](INCIDENT_2026-08-16_DOMAIN_PARKING.md)：官网被 GoDaddy 停放事故。
9. [RUNBOOK.md](RUNBOOK.md)：SSH 与只读巡检方法。

## 当前重点

- `wms-server` 已扩至 600 GB 并恢复服务；需确认 `/home/daniel` 历史大文件的保留要求，并建立容量告警。
- 明确 Bitbucket 仓库、Jenkins Job 与 CEWMS/OTWMS 部署目标的映射。
- 官网根域名、`www`、`cp` 已于 `2026-09-17` 续期，标准 HTTPS 正常；下次到期为 `2026-12-16`。
- Cron/Nginx 路径已修复；仍需清理其他过期证书项并为续期失败增加告警。
- `cp` 证书和后端已恢复，公网返回 HTTP 200；见 [故障记录](../otwms-wms-server/INCIDENT_2026-09-17_UNRESPONSIVE.md)。
- 处理仍在 Nginx 配置中但证书已经过期的历史域名。
- 核查 `systemd-journald` 长时间高 CPU 的原因和日志来源。
- 评估 1 核、约 1.8 GB 内存且无 Swap 的容量余量。
- 确认 MySQL `3306` 的实际网络暴露范围和访问控制。
- 确认 Nginx、MySQL 与 GCS Fuse 的启动方式和未验证业务依赖。
