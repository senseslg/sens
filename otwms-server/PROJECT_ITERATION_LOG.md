# 项目迭代记录

- 2026-11-28 — CE-2646：本土件（`CCSL-LOCAL`）在订单列表待分配页签不显示。原因是 10-28 `06449cf94` 为推送去重把 `CCSL_LOCAL` 加入共用 `ignoreSource`（同时用于待分配页签、计数、未分配提醒）；页面默认只查当天也会让旧单看不到。分支 `fix/CE-2646-ccsl-local-assign-tabs`（基于 master `54cf8310d`），提交 `7271c918f` 只从 `ignoreSource` 移除 `CCSL_LOCAL`，推送去重不变。PR #3096 合入 qa `097cfc592`，UAT #500 构建成功；UAT 接口只读验收（09-01~11-28）：待取件 45 单全为 CCSL-LOCAL、计数 45；待分配快递员 4 单（自建 3、GOODY-SHOP 1），库中 3 单 CCSL 仍排除；待分配门店计数 0（库中 CCSL 82、CCAF 1 仍排除）。均与库一致，通过。推送去重代码未改，未实测。PR #3097 合并 master `977d0d505`，生产 #202（11-28 19:32）部署，实例 `otwms-group-rqzr`；生产接口核对用户反馈的本土单已出现在待分配快递员页签与计数，与库一致。CE-2646 已关闭（完成）。CE-2644 已于本日关闭（生产核对未同步 0 单）。

- 2026-11-25 — CE-2641：J&T 字段名应为 `expressTypeCode`（`productType` 被忽略）；改名 `be45d4ffe`，UAT #499 构建成功，TC 单被 J&T 测试环境拒（B094，对方确认为其环境问题）。合入 master `54cf8310d`，02:17 生产部署 #201，测试单推 TC 下单成功，见 [CE-2641 记录](FEATURE_2026-11-24_CE-2641_WHJT02_JT_PUSH.md)。

- 2026-11-24 — CE-2641 WHJT02 推 J&T：按登录门店识别，重量 >10.1 时 productType 推空，COD 取整到百位；UAT 验收通过。CE-2644 编译修复 `4c1cb9616`（UAT #497→#498）。两者合入 master `02f3315ed`，15:49 生产部署 #200 成功，见 [CE-2641 记录](FEATURE_2026-11-24_CE-2641_WHJT02_JT_PUSH.md)。

- 2026-11-21 — 运单宽表签收状态未同步：修复 38 单（首单+近 30 天 37 单），全量仍有 322 单待定；根因确认为 remark 超长致整批写入失败，已建 CE-2644 与修复分支（未推送），见 [事件记录](INCIDENT_2026-11-21_SHIPMENT_REPORT_STATUS_SYNC.md)。

- 2026-11-19 — 新增待办：`tms_tracking_event` 只按 `OBJECT_NO` 查询会全表扫描约 6,500 万行，需排查源码与查询说明，见 [下一步](PROJECT_OVERVIEW.md#下一步)。

- 2026-11-17 — 实现佣金 SQL 汇总本地分支，MyBatis 隔离验证及独立 UAT 五组只读金额对照通过；全量构建缺私有依赖，未推送或部署，见 [实现与核对](INCIDENT_2026-11-17_COURIER_LATENCY_AND_DISK.md#实现与公司-uat-只读核对)。

- 2026-11-17 — 佣金查询本机 MySQL 合成数据试验通过金额与边界对照；SQL 聚合是主要收益，联合索引仍待代表性 UAT 验证，见 [试验记录](INCIDENT_2026-11-17_COURIER_LATENCY_AND_DISK.md#佣金查询隔离试验)。

- 2026-11-17 — 定位快递员佣金请求约 20 秒与同窗慢 SQL 相符；获准清理 OTWMS stdout，根盘由 96.6% 降至 16.7%，未重启，见 [排查与恢复](INCIDENT_2026-11-17_COURIER_LATENCY_AND_DISK.md)。

- 2026-11-16 — 记录 TMS 超时、OTWMS 扫描变慢及共享库订单更新等锁证据，见 [排查记录](INCIDENT_2026-11-16_TMS_OTWMS_SCAN_TIMEOUT.md)。

- 2026-11-04 — 按 Anytype 本土物流需求完成 PR #3064 跨系统只读审查，记录 8 项风险、数据佐证与待验证边界；详见 [审查报告](REVIEW_2026-11-04_LOCAL_PARCEL_RELEASE.md)，未改业务代码或生产数据。
