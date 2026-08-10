# google-otwms

OTWMS 在 Google Cloud Platform 上的运维记录子项目，主要沉淀实例访问、磁盘巡检、事故结论和自动化工具规划。

## 阅读顺序

1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：环境背景、已知状态和维护边界。
2. [RUNBOOK.md](RUNBOOK.md)：生产/UAT SSH、实例发现和只读巡检步骤。
3. [SSH_TROUBLESHOOTING.md](SSH_TROUBLESHOOTING.md)：区分认证、网络、磁盘与应用问题。
4. [INCIDENT_LOG.md](INCIDENT_LOG.md)：磁盘空间与 SSH 事故、处理经过和结论。
5. [ROADMAP.md](ROADMAP.md)：Python 巡检工具现状与后续规划。
6. [`conversations/`](conversations/)：从共享对话提炼的可追溯摘要。

## 当前快照

- 来源更新时间：`2026-07-15`
- GCP Project：`cambodian-express`
- Zone：`asia-southeast1-a`
- 生产实例快照：`otwms-group-5dbm`
- UAT 实例：`otwms-uat`
- 当前重点：稳定巡检磁盘、Java 进程、日志增长和 deleted file handle。

> 生产环境使用 Managed Instance Group，实例名可能因重建而变化。任何操作前都应重新查询实例，不把上述实例名当作永久地址。
