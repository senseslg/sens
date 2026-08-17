# 2026-08-17 日账单任务查询超时

## 结论

任务 13 失败不是 XXL-JOB 调度或网络故障，而是 8,209 个 shipment code 的单次 `IN` 查询超过 MySQL range optimizer 的 8 MiB 内存上限，执行计划从索引范围查询退化为约 3,560 万行全表扫描，最终被 10 分钟语句上限中断。

## 事件信息

| 项目 | 值 |
|---|---|
| XXL-JOB 任务 | `13`，日账单生成任务 |
| Handler | `dailyBillJobHandler` |
| 参数 | `rerun:2026-08-15` |
| 开始 | `2026-08-17 08:13:46` |
| 失败 | `2026-08-17 08:23:47` |
| 执行器 | `otwms-group-cq0l:9999` |
| 日志 ID | `52821320` |
| 失败方法 | `TmsShipmentRevenueCostServiceImpl.getShipmentRevenueCosts()` |

## 关键证据

- 调度后台成功向执行器下发任务并收到 HTTP 200；XXL-JOB 的任务超时为 `0`。
- SQL 对 `tms_uat.tms_shipment_revenue_cost` 使用 8,209 个占位参数。
- 表约 3,560 万行，约 11.9 GB 数据和 11.1 GB 索引；`shipment_code` 已有可用索引。
- 8,000 个虚构值的只读 `EXPLAIN` 使用 `range` 和 `IDX_UNION`；8,209 个值变为 `ALL`、`key=NULL`。
- `SHOW WARNINGS` 返回 3170：`range_optimizer_max_mem_size=8388608` 被超过，未进行 range optimization。
- Cloud SQL 的全局和会话 `max_execution_time` 均为 600,000 ms，和实际约 10 分钟运行时间吻合。

## 根因链

```text
日账单重跑获得 8,209 个 shipment code
  → 单次 MyBatis IN 查询
  → range optimizer 超过 8 MiB
  → 放弃范围优化和 shipment_code 索引
  → 全表扫描约 3,560 万行
  → 600,000 ms 后数据库中断查询
  → SQLException 3024
  → InvocationTargetException 包装后回传 XXL-JOB
```

## 恢复建议

1. 先确认 `2026-08-15` 是否存在部分账单或明细，以及重跑删除逻辑的事务边界。
2. 将 shipment code 去重后按 500～1,000 个分批查询并合并。
3. 用超过本次规模的数据验证每批执行计划和总耗时。
4. 经 Jenkins 构建、发布验证后再重跑。
5. 重跑后核对数量、金额和重复记录。

提高 optimizer 内存或查询超时只能作为临时措施，可能扩大数据库资源影响，不作为首选永久修复。

## 当前状态

- 根因和源码位置已确认。
- 未修改代码、数据库参数、索引、任务或生产服务。
- 修复、发布和重跑待授权执行。
