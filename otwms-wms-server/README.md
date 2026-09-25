# otwms-wms-server

GCP `wms-server` 的访问、服务基线与故障记录。先看当前状态，再执行只读检查；生产恢复操作需要另行确认。

## 阅读顺序

1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：目标、当前状态和行动项。
2. [SERVICE_INVENTORY.md](SERVICE_INVENTORY.md)：实例与已知服务边界。
3. [INCIDENT_2026-09-17_UNRESPONSIVE.md](INCIDENT_2026-09-17_UNRESPONSIVE.md)：本次失联及 `cp` 超时证据。
4. [RUNBOOK.md](RUNBOOK.md)：登录、只读诊断与恢复验收。

`2026-09-18`：启动盘扩至 600 GB 后已恢复启动；IAP SSH、80/90 端口和公网 `cp` 入口均已验证。根分区约有 101 GB 可用；`/home/daniel` 历史大文件的保留要求待确认。详见 [事故记录](INCIDENT_2026-09-17_UNRESPONSIVE.md)。
