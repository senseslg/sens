# 2026-11-21 运单宽表签收状态未同步

TMS 已签收（`tms_shipment.SHIPMENT_STATUS=60`）的运单，在 `otwms.shipment_report` 里仍为 `W`（在库）或 `P`（派送失败）。用户反馈 10 单，全部确认属实。

## 状态映射（以源码为准）

[`ShipmentStatus`](otwms-backend/src/main/java/org/springblade/common/enums/ShipmentStatus.java)：60→`Y`，80（POD_RE）→`PR`，81（RETURNED）→`R`；20/30/40/50 的 tag 为空，再由 [`ShipmentReport.from`](otwms-backend/src/main/java/org/springblade/tms/entity/ShipmentReport.java) 按异常标记置 `P`、按当前位置置 `W`。`sens-workspace` 文档中“80=已签收（退件）/R”的说法与代码不符，80 在报表里应为 `PR`。

## 数据核对（只读）

- 近 30 天 TMS 已签收、报表未同步：44 单。复核时其中 7 单为刚签收、已被任务正常同步，实际卡住 **37 单**，最长落后约 16 天。
- 全量（不限 30 天）报表落后于 TMS 超过 2 小时：340 单，其中 TMS=60 的 322 单，**尚未修复**。
- 增量水位 `sys_config.SHIPMENT_LAST_SYNC_TIME` 与当前时间仅差数分钟，增量同步在推进。

## 已执行修复（用户授权）

- 2026-11-21：用户反馈的首单 `status_tag` W→Y。
- 2026-11-21：37 单 `status_tag`→`Y`、`status`→`60`；条件为 TMS 仍为 60 且报表仍为 W/P，事务内校验影响行数后提交。首次执行影响 37≠44，已回滚复核后再执行。
- 未改其他字段（派送时间、派送员/门店、异常、`last_change_time` 等）；修复后这些行离开非终态集合，不会再被任务自动刷新。

## 根因（已确认）

同步任务 [`TmsReportJob`](otwms-backend/src/main/java/org/springblade/tms/job/TmsReportJob.java)（handler `syncShipmentJobHandler`，实际**每 5 分钟**）：

- `build()` 把 TMS 最新备注（`tms_shipment_event.TRACKING_EVENT_DESC`，varchar(1000)）写入 `shipment_report.remark`（varchar(200)）；库为 `STRICT_TRANS_TABLES`，超长报错。
- `doSync` 按 1,000 单 BATCH upsert，一条超长即整批提交失败；异常被吞，任务仍 `handleCode=200`。增量段同样整批丢失且水位照常前进。
- 非终态补偿每次顺序相同，含超长备注的页永远失败，同页运单永不更新。
- 证据：2026-11-21 17:20/17:25/17:30 三次执行日志，每次约 35 批中 15~18 批 `Error sync`（`DefaultSqlSession.commit`），第 1–9 批成功；只读核对非终态集合 34 页，超长备注只出现在第 10 页起的 18 页，与落后运单所在页一致。前 9 页（N）无备注超长、无落后。
- 已排除：异常原因码为空、门店类型、状态码不在枚举、订单号大小写。
- `e.printStackTrace()` 写入 stderr 管道，读取端（启动脚本服务）已退出，异常消息不可见；XXL 日志只有调用栈。
- 订单取消流程（`OtwmsOrderServiceImpl` 调 `build()` 后写宽表）同样受超长备注影响。

## 开发

- Jira：[CE-2644](https://issue.cambodianexpress.com/browse/CE-2644)（故障，OTWMS后端，经办人 sens）。
- 分支：公司仓库 `fix/CE-2644-shipment-report-sync`，基于 `origin/master` `34fbc46c1`；本地 worktree `otwms-server/otwms-backend-CE-2644/`（父仓库已忽略）。
- 改动一（`77bfff787`，已推送）：`build()` 末尾按列长截断文本字段（按 code point）；`build()` 纳入异常处理；批量失败回退逐条写入并记录运单号与根因消息；补偿段改为按状态逐个、以运单号游标分页。
- 改动二（`8683492d3`，已推送）：增量水位在窗口内无晚于水位的更新时，跳到 `min(LAST_UPDATE_DATE) > 水位`（`TmsShipmentMapper.getNextUpdateTime`，走 `IDX_UPDATE_TIME`，EXPLAIN 为 optimized away）；不依赖应用与库的时钟/时区，不会跳过任何更新。
- 验证：截断逻辑独立单测通过；MP 3.1.x 链式 `gt(boolean,…)`/`last` 经 javadoc 核对存在。完整 Maven 编译仍缺私有/外部依赖，需 Jenkins 或 UAT 构建验证。

## 下一步

- [x] 提交 `77bfff787` 推送；PR #3094 合入 `qa`；Jenkins UAT #496 检出该合并并 BUILD SUCCESS（完整编译通过）。
- [x] UAT 业务验证（改动一，用户授权造样本）：在 N 状态第一页选两单，A 的最新 99 事件描述改为 260 字（含中文）标记，B 的宽表备注改为过期标记；20:20 任务后 A 宽表备注 = 标记前 200 字，B 恢复为 TMS 值，即含超长备注的批次整批写入成功。随后恢复 A 的事件描述，20:25 宽表复原。变更前值备份在会话临时目录。（更正：先前“UAT 任务未运行”判断有误，任务在运行。）
- [ ] 待办（等用户安排时间）：重启 `otwms-uat` 修复 SSH。重启前只读核对 `gs://cambodian-express/packages/uat/BladeX.jar` 更新时间与最新 UAT 构建一致；重启后验证密钥同步与 SSH 登录、应用启动及同步任务恢复；不行再经启动时修复访客代理（另行确认）。
- [ ] 改动二（增量水位卡死）：已推送 → 用户合入 `qa` → Jenkins UAT → 核对 UAT 水位从 `2026-08-31 13:43:30` 开始前进。生产若 TMS 停更超 1 天同样会卡死。
- [ ] 验收通过后按 [工作流](DEV_RELEASE_WORKFLOW.md) 合并功能分支到 `master`、生产部署，并做 24 h/48 h 复查。
- [ ] 发布后看任务日志：无整批 `Error sync`，逐条失败（如有）有运单号和原因。
- [ ] 发布后按日期参数重跑同步（需授权）或等补偿段自动刷新，复核 TMS=60 而宽表非 Y 归零（含剩余 322 单）。
- [ ] 可选：`getShipmentRemark` / `setExceptionInfo` 的 `Collectors.toMap` 遇空值会 NPE，目前未发现数据触发，未纳入本次改动。
- [ ] 可选：增量水位重叠读取以覆盖晚提交事务，本次未发现证据，未改。
