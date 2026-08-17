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
| 生产分支 | `master` |
| Jenkins Job | `otwms / prod / otwms-backend` |
| Jenkins 工作区 | `/home/daniel/containers/jenkins/jenkins/workspace/otwms/prod/otwms-backend` |
| 生产实例 | `otwms-group-cq0l`，`asia-southeast1-a` |
| 生产产物 | `/root/BladeX.jar` |
| XXL-JOB 执行器 | OTWMS 应用进程，端口 `9999` |
| 业务数据库 | Cloud SQL `tms-db`；相关 schema 为 `tms_uat` |

完整证据和当前 Git/JAR 快照见 [SOURCE_DEPLOYMENT_MAP.md](SOURCE_DEPLOYMENT_MAP.md)。实例名可能随实例组替换而变化，定位时应以执行器内网地址反查当前实例，不能永久依赖本次名称。

## 当前问题

2026-08-17 手动执行任务 13“日账单生成任务”，参数为 `rerun:2026-08-15`。任务向 `tms_shipment_revenue_cost` 一次传入 8,209 个 shipment code，超过 MySQL `range_optimizer_max_mem_size=8 MiB`，优化器放弃范围索引并扫描约 3,560 万行；查询在 `max_execution_time=600000 ms` 后被中断。

详细证据见 [INCIDENT_2026-08-17_DAILY_BILL_QUERY_TIMEOUT.md](INCIDENT_2026-08-17_DAILY_BILL_QUERY_TIMEOUT.md)。

## 建议方案

- 在 `TmsShipmentRevenueCostServiceImpl.getShipmentRevenueCosts(Set<String>)` 中去重并按 500～1,000 个 shipment code 分批查询，再合并结果。
- 分批修改应覆盖相同职责的重载方法或抽取共享私有方法，避免另一入口重复出现同类问题。
- 提高 MySQL optimizer 内存或语句超时时间仅作为受控应急方案，不替代代码修复。

以上是技术建议，尚未实施或发布。

## 风险与边界

- `DailyBillJob.rerun()` 会先删除已有账单再重新执行；修改或重跑前必须核对事务边界、部分写入和幂等性。
- Jenkins 工作区是构建副本，不是直接编辑位置；正式修改必须提交 Bitbucket。
- `tms_uat` 是 schema 名，本次连接实际位于生产 Cloud SQL `tms-db`，不能因名称误判为 UAT。
- 数据库和服务器检查默认只读；不输出连接凭据或原始业务参数。

## 下一步

- [ ] 在正式源码分支实现并测试分批查询。
- [ ] 核对 `2026-08-15` 是否存在部分账单或残留明细。
- [ ] 验证 500～1,000 条批次持续使用 `range` 计划。
- [ ] 经 Jenkins 构建、受控部署和校验后重跑任务 13。
- [ ] 重跑后核对账单数量、金额和重复数据。

最近更新：`2026-08-17`
