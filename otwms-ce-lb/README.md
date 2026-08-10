# otwms-ce-lb

`ce-lb` GCP 实例的访问、运行基线、风险与后续运维记录。

## 阅读顺序

1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：当前状态、风险和行动项。
2. [SSL_INVENTORY.md](SSL_INVENTORY.md)：证书、域名和续期状态。
3. [RUNBOOK.md](RUNBOOK.md)：SSH 与只读巡检方法。

## 当前重点

- 在 `2026-09-13` 前验证主域名、`www`、`cp` 的 Certbot 自动续期。
- 处理仍在 Nginx 配置中但证书已经过期的历史域名。
- 核查 `systemd-journald` 长时间高 CPU 的原因和日志来源。
- 评估 1 核、约 1.8 GB 内存且无 Swap 的容量余量。
- 确认 MySQL `3306` 的实际网络暴露范围和访问控制。
- 梳理 Nginx、PHP-FPM、MySQL 与 GCS Fuse 的业务关系和启动方式。
