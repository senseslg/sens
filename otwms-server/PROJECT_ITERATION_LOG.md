# 项目迭代记录

- 2026-11-21 — 运单宽表签收状态未同步：修复 38 单（首单+近 30 天 37 单），全量仍有 322 单待定；根因确认为 remark 超长致整批写入失败，已建 CE-2644 与修复分支（未推送），见 [事件记录](INCIDENT_2026-11-21_SHIPMENT_REPORT_STATUS_SYNC.md)。

- 2026-11-19 — 新增待办：`tms_tracking_event` 只按 `OBJECT_NO` 查询会全表扫描约 6,500 万行，需排查源码与查询说明，见 [下一步](PROJECT_OVERVIEW.md#下一步)。

- 2026-11-17 — 实现佣金 SQL 汇总本地分支，MyBatis 隔离验证及独立 UAT 五组只读金额对照通过；全量构建缺私有依赖，未推送或部署，见 [实现与核对](INCIDENT_2026-11-17_COURIER_LATENCY_AND_DISK.md#实现与公司-uat-只读核对)。

- 2026-11-17 — 佣金查询本机 MySQL 合成数据试验通过金额与边界对照；SQL 聚合是主要收益，联合索引仍待代表性 UAT 验证，见 [试验记录](INCIDENT_2026-11-17_COURIER_LATENCY_AND_DISK.md#佣金查询隔离试验)。

- 2026-11-17 — 定位快递员佣金请求约 20 秒与同窗慢 SQL 相符；获准清理 OTWMS stdout，根盘由 96.6% 降至 16.7%，未重启，见 [排查与恢复](INCIDENT_2026-11-17_COURIER_LATENCY_AND_DISK.md)。

- 2026-11-16 — 记录 TMS 超时、OTWMS 扫描变慢及共享库订单更新等锁证据，见 [排查记录](INCIDENT_2026-11-16_TMS_OTWMS_SCAN_TIMEOUT.md)。

- 2026-11-04 — 按 Anytype 本土物流需求完成 PR #3064 跨系统只读审查，记录 8 项风险、数据佐证与待验证边界；详见 [审查报告](REVIEW_2026-11-04_LOCAL_PARCEL_RELEASE.md)，未改业务代码或生产数据。
