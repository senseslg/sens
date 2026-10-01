# TMS 服务器基础信息

整理日期：`2026-10-01`。依据既有调查记录整理，资源与发布信息为历史快照，不代表实时健康状态。

## 定位与访问

| 项目 | 已确认信息 |
|---|---|
| Google Cloud 项目 | `cambodian-express` |
| Compute Engine 实例 | `tms-instance-template-20251103-082933`（实例名称，不是模板操作目标） |
| 可用区 | `asia-southeast1-a` |
| 业务入口 | `https://tms.cambodianexpress.com/login` |
| 内网端点 | 当次调查为 `10.148.0.116:8080` |
| 入口链路 | URL map `tms-lb` → `tms-neg-backend` → `tms-neg` → Tomcat |
| 健康检查 | `check-8080`，仅 TCP/8080；HEALTHY 不保证 HTTP 可用 |
| 应用目录 | `/home/daniel/apache-tomcat-8.5.50` |
| 部署脚本 | `/home/daniel/deploy.sh` |
| 运行属主 | 已观察到 Java/Tomcat 为 root，由 Jenkins 部署脚本启动 |

SSH 入口（连接成功不代表有管理员权限）：

```bash
gcloud compute ssh "tms-instance-template-20251103-082933" --zone "asia-southeast1-a" --project "cambodian-express"
```

## 资源与依赖快照

- 内存：`2026-10-01 09:09–09:14` 总量 32011 MiB、available 12913 MiB；未见本次整机内存耗尽。
- 根盘：`2026-09-30` 约 100 GB，使用约 68%，余约 33 GB；不是 Cloud SQL 数据盘。
- JVM：既有配置 `-Xms24g -Xmx24g`，实例无 swap；历史 OOM 风险仍需独立治理。
- Java FD：`2026-10-01 09:14` 软/硬上限均为 4096；未取得实际 FD 数量，不能据此确认耗尽。
- Redis：托管实例 `tms-redis`，`2026-09-30` 为 Redis 5.0 / 1 GiB / READY。
- 数据库：共享 Cloud SQL `tms-db`，见 [容量审查](../google-cloud/TMS_DB_CAPACITY_REVIEW_2026-09-28.md)。数据库容量与 VM 根盘分开判断。
- OS 版本、Compute machine type 和精确 Java 版本：本信息表未核实，不根据名称推断。

## 源码与发布

- Bitbucket `TMS/tms-server`：`https://code.cambodianexpress.com/scm/tms/tms-server.git`；本目录只保存文档，未克隆此源码。
- Jenkins：`wms-db` 上的 `TMS / prod / tms-prod`，产物经 `gs://cambodian-express/ROOT.war` 中转后部署到本实例。
- 详细链路和历史构建证据见 [SOURCE_DEPLOYMENT_MAP.md](SOURCE_DEPLOYMENT_MAP.md)。历史构建 #456 不代表当前版本。
- OTWMS 后端、`wms-db` 上的 XXL-JOB 管理后台和 `ce-lb` 官网源站均不是本 Tomcat 实例；共享入口或跨系统调用不等于同一服务器。

## 当前访问障碍与故障索引

Google 身份 `senseslg@gmail.com` 已核实有项目 Owner，OS Login 管理员检查也通过；但 SSH 用户 `senseslg_gmail_com` 实际命中本地 UID 1021，与云端 POSIX UID 643791315 同名冲突。当前会话没有可用的免密 sudo，无法读取受限 Tomcat 日志或管理 root Java。不要通过索取 Google 密码、猜测本地密码或直接改 UID 来处理。

- [当前间歇超时事件](INCIDENT_2026-09-30_INTERMITTENT_TIMEOUT.md)：根因未确认，TMS 未完成修复验收。
- [历史 OOM 与恢复](INCIDENT_2026-09-17_OOM_AND_RECOVERY.md)：不是本次已确诊为 OOM 的证据。
- [操作规范](RUNBOOK.md)：重启、权限调整、发布和限额变更须分别核对授权、影响与回滚。
