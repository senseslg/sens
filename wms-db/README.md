# wms-db

GCP `wms-db` 的独立运维子项目。该实例是 CE/WMS 的共享平台，集中承载 Jira、Bitbucket、Jenkins、XXL-JOB、YApi、Nexus、数据库和 SQL 审核工具。

## 阅读顺序

1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：当前状态、范围、风险和待办。
2. [SERVICE_INVENTORY.md](SERVICE_INVENTORY.md)：域名、端口与容器清单。
3. [INFRASTRUCTURE_MAP.md](INFRASTRUCTURE_MAP.md)：公网入口与服务链路。
4. [RUNBOOK.md](RUNBOOK.md)：IAP 登录和只读巡检方法。
5. [JIRA_REQUIREMENTS.md](JIRA_REQUIREMENTS.md)：Jira 接入约定、认证和工具选择。
6. [jira-service/README.md](jira-service/README.md)：本机 Python 需求服务；功能评估与操作说明由该子项目维护。

`2026-10-03`：实例、Nginx 和主要容器均在运行；`issue`、`code`、`yapi`、`jenkins` 的入口均已核实。500 GB 根盘使用约 56%，内存余量约 12 GB。当前主要风险是服务高度集中、CentOS 7 生命周期、无 Swap、旧版或 `latest` 容器镜像，以及备份恢复体系尚未完整确认。

Jira 本体实测为 Server 7.12.0。本机 `jira-service` 已验证 API 建单、查询及 CSV；关闭/不做尚未实测提交，后台全域 CSV 格式仍待对齐。该服务未部署到 GCP，未改变共享服务器基线。
