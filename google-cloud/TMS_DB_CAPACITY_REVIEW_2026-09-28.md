# 2026-09-28 `tms-db` 容量与业务数据审查

## 结论

`cambodian-express` 的 Cloud SQL `tms-db` 已用约 **1,186 GiB / 1,253 GiB（94.7%）**，近 30 天净增长约 15.65 GiB，期间自动扩容 25 GiB。最大压力是 `tms_uat.sys_if_invoke_inbound`：物理表空间 **714.46 GiB**，约占实例已用磁盘 60%；其 `information_schema.TABLES` 数据与索引合计仅约 **238.38 GiB**。两种口径相差约 476 GiB，可能包含历史删除/更新后的空闲页、LOB 分配或统计口径差异；**不能把差额直接当成可回收量**。

本次仅做只读诊断，没有修改实例、SQL、表结构或数据。

## 证据快照

采集时间约 `2026-09-28 09:34`（UTC+7）。来源：Cloud SQL 实例配置、Cloud Monitoring `database/disk/*`、MySQL `information_schema.TABLES` / `INNODB_TABLESPACES`，以及本地 OTWMS 源码。GiB 为二进制单位；InnoDB `TABLE_ROWS` 为估算值。

| 项目 | 结果 |
|---|---:|
| 已分配 / 实际已用 / 可用 | 1,253 / 约 1,186 / 约 66 GiB |
| 已用分类 | Data 约 1,173 GiB；Binlog 约 10.3 GiB；临时文件接近 0 |
| 近 30 天 | 已用增加约 15.65 GiB；容量自动增加 25 GiB |
| 表级数据+索引 | `tms_uat` 448.71 GiB；`otwms` 90.92 GiB；`tms_archive` 约 0.15 GiB |
| 实例保护 | 自动扩容开启、无上限；单区；自动备份 7 份，事务日志保留 7 天 |

| 表 | 物理表空间 | 表级数据+索引 | 业务判断 |
|---|---:|---:|---|
| `tms_uat.sys_if_invoke_inbound` | 714.46 GiB | 238.38 GiB | 接口请求/响应审计，优先治理 |
| `tms_uat.tms_shipment_event` | 85.95 GiB | 43.91 GiB | 运单事件，不能按日志直接删除 |
| `otwms.station_letter` | 44.38 GiB | 2.55 GiB | 站内信已按约 7 天清理，优先验证表空间回收 |
| `tms_uat.tms_shipment_revenue_cost` | 33.77 GiB | 21.46 GiB | 费用与结算依赖 |
| `tms_uat.tms_tracking_event` | 33.25 GiB | 18.82 GiB | 轨迹与客服追溯依赖 |
| `otwms.external_interface_log` | 15.52 GiB | 14.55 GiB | OTWMS 接口审计 |
| `otwms.shipment_report` | 16.80 GiB | 16.19 GiB | 导出/报表读取的派生表 |

`sys_if_invoke_inbound` 的时间跨度为 2022-09 至今，最近 1/7/30 天分别约 11,766 / 66,674 / 291,608 条。最近 1,000 条中，`regionTree` 接口 155 条响应合计约 57.9 MiB；其最近 100 条响应内容完全相同，单条约 382 KiB。样本说明成功响应重复存储明显，**不代表全表都按这个比例增长**。

`otwms.external_interface_log` 最近 1/7/30 天分别约 23,093 / 143,185 / 543,221 条。本地 [ExternalAspectConfig.java](../otwms-server/otwms-backend/src/main/java/org/springblade/otwms/business/order/external/aop/ExternalAspectConfig.java) 把完整请求、响应及 `Authorization` 写入日志表；应将脱敏与保留期一并评审。

`station_letter` 的 [清理任务](../otwms-server/otwms-backend/src/main/java/org/springblade/otwms/business/announcement/job/AnnouncementAutoClearJob.java) 默认删除 7 天前的站内信；当前最早记录为 2026-09-22，30 天前记录为 0。现有删除已在发挥作用，但物理文件仍达 44.38 GiB；无需先增加删除规则。

## 优先方案

1. **先守住容量：** 建立已用量、余量、增长速率与自动扩容告警；核对备份可恢复性。当前约 66 GiB 余量不足以安全尝试 714 GiB 大表原地重建。Cloud SQL 官方建议监控 `database/disk/bytes_used_by_data_type`、`bytes_used` 和 `utilization`。见 [Google Cloud 高磁盘使用说明](https://docs.cloud.google.com/sql/docs/mysql/high-disk-usage)。
2. **停止无效增长：** 在 TMS 源码定位 `sys_if_invoke_inbound` 写入点，成功且大体重复的响应优先记录接口、状态、耗时、报文大小与哈希；确需保留原文的异常或争议记录按受控期限单独保存。先做业务/审计保留期评审，避免影响排错与追责。OTWMS 同步脱敏 `Authorization`，限制成功日志中的原始报文体积。
3. **分级归档：** 接口日志可讨论短于运单/财务记录的在线保留期；站内信已有约 7 天清理，先核对其物理回收。运单事件、轨迹、费用、COD 和账单需依据终态、结算完成、退款/争议窗口及报表追溯要求设计归档。`tms_archive` 当前仅约 0.15 GiB，且位于同一实例；仅把数据搬到此 schema 不会降低实例磁盘用量。归档介质应另行评估。历史候选表 `daily_bill_item_bk` 约 3.48 GiB、`tms_shipment_revenue_cost_lt_2024` 约 6.34 GiB，应先验证是否仍被代码或审计使用。
4. **回收物理空间：** 在恢复演练通过的克隆环境中对候选表验证重建后的实际大小、耗时、锁和所需临时空间，再选择受控在线重建、迁移到新实例或其他方案。删除旧行本身不保证 `.ibd` 缩小；MySQL 官方说明在线 DDL 重建还会占用额外磁盘。[MySQL Online DDL 空间要求](https://dev.mysql.com/doc/refman/8.0/en/innodb-online-ddl-space-requirements.html)。
5. **之后再评估降本：** 当前 Cloud SQL 文档支持满足条件的实例执行存储缩容，但操作需要重启和停机，且有最低安全容量限制；是否适用于本实例需在清理、重建和容量缓冲核算后验证。[Google Cloud 存储缩容说明](https://docs.cloud.google.com/sql/docs/mysql/about-storage-shrink)。

## 其他可核对项

`otwms.shipment_report` 的 `idx_shipment_code` 与主键列相同；可结合查询画像评估移除冗余索引，但当前 9.61 GiB 是该表**所有**索引总量，不能把它当作此单一索引的节省额。报表表仍被 Daily Report 等路径读取，不宜直接删表或改为离线。

## 2026-09-28 两年保留评估

TMS `master` 提交 `6e323c6` 中，`body-booking` 和 `regionTree` 等入口使用 HAP `@HapInbound` 注解；抽查记录的字段为接口名、URL、方法、请求时间、来源、请求头/体、状态、耗时、响应和异常堆栈。业务源码没有直接引用表名，数据库也没有声明引用该表的外键；但 HAP 依赖内的日志页面或其他查询仍待核对，不能据此断言删除完全没有业务影响。

按数据库时间 `2026-09-28 09:50` 计算，`REQUEST_TIME < 2024-09-28 09:50` 命中 **12,111,823** 条；两年内 **6,530,411** 条，合计 **18,642,234** 条；时间为空的记录为 0。上述数量通过 `REQUEST_TIME` 索引精确统计；`information_schema.TABLE_ROWS` 约 970 万只是失准估算。边界附近旧记录抽样 1,000 条中，990 条状态为 `success`、10 条为 `failure`，不能外推为全表比例。

脱敏结构样本（不保存报文、IP、请求头或客户字段值）：

| 时间/接口 | 方法/状态 | 请求结构 | 响应大小 |
|---|---|---|---:|
| 2026-09-28 `external.order.body-booking` | POST / success | JSON，含订单号、商品、付款方式等字段；约 1.2 KiB | 79 B |
| 2026-09-28 `batchCreateException` | POST / success | JSON 数组；约 0.4 KiB | 16 B |
| 2024-09-28 `regionTree` | GET / success | 无请求体 | 约 382 KiB |

**判断：** 两年保留作为候选策略可行，但需先确认历史接口日志的审计、争议、故障追溯要求。若“不备份”指不另做一次专用备份，当前自动备份最近一次于 2026-09-27 成功，事务日志保留 7 天；应先验证恢复路径并接受超出恢复窗口后无法找回旧记录的后果。若指完全没有可恢复副本，不建议执行。

实施时应冻结明确截止时间，在克隆环境验证，再通过 `REQUEST_TIME` 索引小批量删除、限速、监控锁等待及 binlog/undo/磁盘变化，最后设置每日上限的定期任务。不可一次删除 1,211 万行；删除后 `.ibd` 文件也不会立即缩小，物理空间回收仍是独立变更。当前尚未删除任何记录或创建定时任务。

下一步需确认日志的业务/审计保留年限和 HAP 依赖中的读取用途，再在克隆环境验证批量删除及恢复路径，形成具体 SQL、定时任务、监控与回滚方案。

## 2026-09-28 两年清理执行记录（10:38 UTC+7）

用户确认该表可无额外表级备份地删除两年前日志，依赖 Cloud SQL 自动备份。操作前实时核实：`tms-db` 为 `RUNNABLE`，自动备份开启，最近一次 `2026-09-27 20:00 UTC` 启动的备份为 `SUCCESSFUL`，binlog/PITR 保留 7 天。恢复旧记录的实际方式是先将备份或删除前时间点恢复到**新实例**，再抽取所需数据；不能把自动备份理解成可以原地撤销单表删除。[Cloud SQL 恢复概述](https://docs.cloud.google.com/sql/docs/mysql/backup-recovery/restore)。

数据库会话为 UTC+7；`REQUEST_TIME` 是非空 `datetime`，索引 `SYS_IF_INVOKE_INBOUND_N3`；`EXPLAIN DELETE ... WHERE REQUEST_TIME < 截止时间 ORDER BY REQUEST_TIME LIMIT 100` 采用该索引的范围扫描。仅对 `tms_uat.sys_if_invoke_inbound` 执行分批删除，每批独立提交，`innodb_lock_wait_timeout=3`。执行脚本：[purge_tms_inbound_logs.py](scripts/purge_tms_inbound_logs.py)，默认 dry-run、每次最多 1 万条；使用 `--execute` 才会删除。

实际已提交：首次试删 100 条，其后 1 万、10 万、100 万、100 万条，共 **2,110,100 条**。最后一轮 100 万条用时约 375 秒。截止时间每轮由数据库的 `NOW() - INTERVAL 2 YEAR` 计算；`2026-09-28 10:38:21` 实测截止 `2024-09-28 10:38:21`，仍有 **10,001,944 条**超期，最早剩余记录时间 `2022-11-18 10:27:50`。因此**历史清理尚未完成，尚未实现全表仅保留两年**。

暂停原因：Cloud Monitoring 磁盘余量从约 66 GiB 降至约 60.5 GiB，已用增长主要是 binlog（约 10.5 → 15.3 GiB）；Data 仍约 1,173 GiB，说明分批删除没有使表空间文件缩小。CPU 约 27%，未发现长事务积压。继续一次性清理余下约千万条，可能使 binlog 继续增加数十 GiB，并接近自动扩容阈值；这会改变成本和容量风险。等待确定是接受当日继续清理与可能自动扩容，还是分多日限额清理并逐日监控。**没有创建定期删除事件或外部定时任务**。

安全复跑示例：先确认备份与 Cloud Monitoring 磁盘余量，再运行 `python3 google-cloud/scripts/purge_tms_inbound_logs.py` 只读预检；确认后以 `--execute --max-rows 500000 --batch-size 5000 --sleep 0.25` 执行有上限的一轮。`--cutoff` 可冻结更早边界，脚本拒绝比当前两年边界更新的截止时间。不要在不检查 binlog 增长和业务负载的情况下循环执行至完成。MySQL 事件调度器当前为 `ON`、连接账号具备 `EVENT` 权限，但自动任务仍待设计与授权。
