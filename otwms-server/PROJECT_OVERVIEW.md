# OTWMS Server Overview

## 目标与完成标准

- 维护 OTWMS Java 后端从 Bitbucket 源码到 Jenkins 构建、生产部署和 XXL-JOB 执行的可信映射。
- 故障定位能够落到具体任务、执行器、JAR、Git 提交、Java 类和数据访问方法。
- 发布前后可通过提交、构建产物校验值、进程和任务日志验证一致性。

## 当前稳定映射

| 层级 | 当前值 |
|---|---|
| 调度后台 | `wms-db` 上的 `xxl-job-admin`；只负责调度 |
| 源码仓库 | `OTWMS/otwms-backend` |
| 本地后端 | `otwms-server/otwms-backend/`（导读见 [SOURCE_CODE_GUIDE.md](SOURCE_CODE_GUIDE.md)） |
| 本地前端 | `otwms-server/otwms-frontend/` |
| UAT 前端 Jenkins Job | `otwms / uat / otwms-frontend-uat` |
| UAT 前端存储桶 | `gs://otwms-frontend-uat/` |
| 生产分支 | `master` |
| Jenkins Job | `otwms / prod / otwms-backend` |
| Jenkins 工作区 | `/home/daniel/containers/jenkins/jenkins/workspace/otwms/prod/otwms-backend` |
| 生产实例 | `otwms-group-1ktm`，`asia-southeast1-a`（实例组成员会变化） |
| 生产产物 | `/root/BladeX.jar` |
| XXL-JOB 执行器 | OTWMS 应用进程，端口 `9999` |
| 业务数据库 | Cloud SQL `tms-db`；相关 schema 为 `tms_uat` |

共享数据库的 2026-09-28 容量审查见 [`google-cloud` 记录](../google-cloud/TMS_DB_CAPACITY_REVIEW_2026-09-28.md)；OTWMS 接口日志的完整请求/响应与鉴权字段需要脱敏和保留期评审。

完整证据和当前 Git/JAR 快照见 [SOURCE_DEPLOYMENT_MAP.md](SOURCE_DEPLOYMENT_MAP.md)。实例名可能随实例组替换而变化，定位时应以执行器内网地址反查当前实例，不能永久依赖本次名称。

## 当前问题

2026-09-21，生产根分区和 inode 均达到 100%，导致 Daily Report 导出与 Order Print 失效。保留证据并原位截断 42.2 GB 应用日志后，容量/inode 恢复到 22%/2%，服务和业务恢复。根因还包括 XXL-JOB 的 1 天配置实际关闭清理，以及 POI workbook 未 `dispose()`；长期修复尚未发布。详见 [INCIDENT_2026-09-21_EXPORT_PRINT_DISK_FULL.md](INCIDENT_2026-09-21_EXPORT_PRINT_DISK_FULL.md)。

2026-08-17 手动执行任务 13“日账单生成任务”，参数为 `rerun:2026-08-15`。任务向 `tms_shipment_revenue_cost` 一次传入 8,209 个 shipment code，超过 MySQL `range_optimizer_max_mem_size=8 MiB`，优化器放弃范围索引并扫描约 3,560 万行；查询在 `max_execution_time=600000 ms` 后被中断。

详细证据见 [INCIDENT_2026-08-17_DAILY_BILL_QUERY_TIMEOUT.md](INCIDENT_2026-08-17_DAILY_BILL_QUERY_TIMEOUT.md)。

2026-08-22，`gs://otwms-frontend-uat/i18n/` 下 3 个翻译 JSON 因桶级 90 天 Lifecycle 进入软删除状态。对象已按明确 generation 恢复，文件数量、大小和 MD5 与删除前一致，三个公网 URL 均返回 HTTP 200。详细证据见 [INCIDENT_2026-08-22_UAT_I18N_LIFECYCLE_DELETE.md](INCIDENT_2026-08-22_UAT_I18N_LIFECYCLE_DELETE.md)。

2026-09-18，OTWMS 依赖的 TMS 服务恢复 HTTP 响应；App 业务页面仍待验证。OTWMS 影响见 [本项目记录](INCIDENT_2026-09-17_TMS_OUTAGE.md)，TMS 故障与发布事实见 [`tms-server`](../tms-server/INCIDENT_2026-09-17_OOM_AND_RECOVERY.md)。

## 建议方案

- 在 `TmsShipmentRevenueCostServiceImpl.getShipmentRevenueCosts(Set<String>)` 中去重并按 500～1,000 个 shipment code 分批查询，再合并结果。
- 分批修改应覆盖相同职责的重载方法或抽取共享私有方法，避免另一入口重复出现同类问题。
- 提高 MySQL optimizer 内存或语句超时时间仅作为受控应急方案，不替代代码修复。

分批查询已在 `codex/fix-daily-bill-revenue-cost-batching` 实现并通过 Java 8/Maven 单元测试，提交 `a77eb6e71` 已于 2026-08-17 经 PR #2976 合并到 `master`（按 500 个分批）。生产 JAR 是否包含该提交未核对，任务 13 尚未重跑。

## 源码现状（2026-10-01）

- 前后端源码已拉取到本目录，`master` 停在 2026-09-22（后端 `5ba65f13f`，前端 `4ec71efe6`）。结构与风险见 [SOURCE_CODE_GUIDE.md](SOURCE_CODE_GUIDE.md)。
- 09-21 事故的两项代码根因在 `master` 中**仍未修复**：`JobConfig` 仍为 `setLogRetentionDays(1)`，`ExportController` 仍未调用 `dispose()`。
- `application*.yml` 中有明文凭据，需要移出仓库并轮换。

## 风险与边界

- `DailyBillJob.rerun()` 会先删除已有账单再重新执行；修改或重跑前必须核对事务边界、部分写入和幂等性。
- Jenkins 工作区是构建副本，不是直接编辑位置；正式修改必须提交 Bitbucket。
- `tms_uat` 是 schema 名，本次连接实际位于生产 Cloud SQL `tms-db`，不能因名称误判为 UAT。
- 数据库和服务器检查默认只读；不输出连接凭据或原始业务参数。
- Cloud Storage Lifecycle 的 `age` 按对象创建时间计算，不代表 90 天“未访问”；静态业务文件不能使用未限定前缀的桶级删除规则。
- Cloud Audit Logs 不记录 Object Lifecycle Management 自动执行的变更。如需追踪 Lifecycle 删除，应另行配置 Cloud Storage usage logs。

## 下一步

- [x] 保留日志尾部证据并原位截断超大日志，复核容量、inode、Java 和本机 HTTP；业务已恢复。
- [ ] 修复 POI workbook 释放和 XXL-JOB 保留期，通过 Jenkins 发布并验证。
- [ ] 调整生产日志级别和启动输出方式，再配置轮转、压缩、保留期及容量/inode 告警。
- [ ] 通过新实例模板持久扩容 50 GB 启动盘，避免实例重建回到旧规格。
- [x] 在功能分支实现并测试分批查询，提交并推送远程。
- [x] 分批查询修复合并到 `master`（PR #2976，2026-08-17）。
- [ ] 核对当前生产 `/root/BladeX.jar` 对应的提交，确认是否已包含 PR #2976。
- [ ] 评估将 `application*.yml` 中的明文凭据迁到环境变量或 Secret Manager，并轮换已暴露的凭据。
- [ ] 核对 `2026-08-15` 是否存在部分账单或残留明细。
- [ ] 验证 500～1,000 条批次持续使用 `range` 计划。
- [ ] 经 Jenkins 构建、受控部署和校验后重跑任务 13。
- [ ] 重跑后核对账单数量、金额和重复数据。
- [x] 恢复 UAT 前端 `i18n/` 下 3 个翻译对象并验证公网 HTTP 200。
- [ ] 在 `2026-08-27` 硬删除前确认 `WOEvidence/` 的 5 个软删除对象和 `test.jpg` 是否需要恢复。
- [ ] 如需重新启用 Lifecycle，使用明确前缀/后缀和保留期，先在清单上验证命中范围。
- [ ] 如需审计 Lifecycle 自动删除，评估为该桶配置 Cloud Storage usage logs。

最近更新：`2026-10-01`
