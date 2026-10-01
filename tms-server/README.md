# tms-server

`tms.cambodianexpress.com` 的入口、TMS Java/Tomcat 服务、Bitbucket 源码、Jenkins 构建发布和故障恢复记录。这里的 TMS 是独立系统，不是 `otwms-server/otwms-backend`，也不是 `wms-db` 上的 XXL-JOB 管理后台。

## 阅读顺序

1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：当前状态、系统边界和待办。
2. [SOURCE_DEPLOYMENT_MAP.md](SOURCE_DEPLOYMENT_MAP.md)：域名、负载均衡、实例、源码和发布链路。
3. [SERVER_INFO.md](SERVER_INFO.md)：服务器基础信息、SSH 入口、资源快照与权限障碍。
4. [INCIDENT_2026-09-30_INTERMITTENT_TIMEOUT.md](INCIDENT_2026-09-30_INTERMITTENT_TIMEOUT.md)：本次间歇超时、FD 和 CPU Idle 判断边界。
5. [INCIDENT_2026-09-17_OOM_AND_RECOVERY.md](INCIDENT_2026-09-17_OOM_AND_RECOVERY.md)：历史 OOM、Jenkins #456 与恢复证据。
6. [RUNBOOK.md](RUNBOOK.md)：只读定位、发布后验收和权限边界。
7. [reference/README.md](reference/README.md)：可复用的健康检查判断方法。

## 当前重点

- 2026-10-01 再次捕捉 TMS 本机 HTTP 超时，根因未确认，尚未完成修复；需要管理员诊断访问及故障线程栈。
- 2026-09-18 登录页曾恢复，仅为历史验收；历史 OOM 的内存增长根因尚未查明，不能直接套用于本次事件。
- Jenkins 的 `SUCCESS` 和现有 TCP 健康检查都不能单独证明应用已就绪。
- 此目录目前只保存文档；尚未克隆 `TMS/tms-server` 源码，不直接编辑 Jenkins 工作区或生产 WAR。

## 安全边界

默认只读。生产部署、重启、JVM 参数、负载均衡健康检查及权限变更，须先确定影响范围、回滚和验收，并取得明确授权。不保存凭证、完整连接串或业务数据。
