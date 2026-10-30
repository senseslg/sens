# Jira 时区与业务影响评估（2026-10-23）

## 当前结论

Jira 返回 UTC 是当前服务层的正常时间表示，不是后台金边展示设置延迟生效。展示时区与 JVM 时区相互独立，不会因修改后台设置而自动同步。已核对的账号有效时区均与金边时间一致；不需要为改变 REST 返回偏移而修改 JVM 或重启 Jira。本次仅检查与更新记录，未修改 Jira 配置或业务数据。

## 实测证据

- `serverInfo.serverTime`：`2026-10-23T13:57:16.494+0000`，同一时刻金边为 `2026-10-23 20:57:16 +0700`；按请求前后本机时间估算仅差约 0.11 秒，不是服务时钟慢 7 小时。
- longmh、BRIAN、yuth、huzw、tsw、mark、milf 有效时区均为 `Asia/Phnom_Penh`；sens 为 `Asia/Bangkok`，与金边同为 UTC+7。
- CELSHOP-930 的 API 创建时间 `2026-10-05T10:23:35.000+0000` 对应金边 `2026-10-05 17:23:35`；到期日仍为 `2026-10-06`，抽样未见日期改变。
- Jira 容器启动时间仍为 2024-06-05，本次没有重启。启动脚本未发现显式 `-Duser.timezone` 参数；Java 诊断工具本次无法附加到 Jira 进程，未直接读到 `user.timezone`；因此不把 REST 的 UTC 偏移当作已经直接确认 JVM 属性。
- 管理配置 API 未直接返回全局默认时区值，最近 100 条审计未找到时区变更明细；账号的有效时区已验证，不将其混写为全局配置值已直接读到。
- 本机 Jira 服务 18 项隔离测试通过，包括 UTC 与金边边界换算、日期格式、截断及防重；代码明确读取 Jira 账号时区构造 JQL，再转换为报表指定时区。

## 业务影响

| 范围 | 评估与边界 |
|---|---|
| 创建、解决、评论等时间 | 正确换算改变显示，不应手工将原数据再加 7 小时；UTC 与 +07 可以表示同一个时刻 |
| 到期日等纯日期 | 没有小时含义；已抽样验证 CELSHOP-930 日期未变。自定义插件仍需按实际实现验证 |
| JQL 日/月筛选 | 按账号配置时区解释无偏移日期边界；原来 GMT 的账号改为金边后，午夜附近结果可能不同，这是统计日界线调整，不是数据丢失 |
| 本机周报/月报 | 默认金边、明确半开区间并逐条核对解决日期；已具备时区转换，不应额外对 CSV 时间加 7 小时。历史九月导出使用的 sens 原本也是 UTC+7 |
| 通知及自定义插件 | 界面与格式化后的通知时间可受用户/默认时区影响；插件或脚本如果采用 JVM 默认时区，需单独核实，不能笼统承诺全部不受影响 |
| 定时任务 | 未改 Jira JVM，不能因本轮展示设置就断言所有任务执行时刻改变；若未来改 JVM，必须先盘点定时任务、订阅、插件的时区来源，依赖默认时区的 Cron 可能改变实际执行时刻 |
| 外部接口 | 保留 `Z`、`+0000`、`+0700` 或 Unix 时间戳并正确解析；去掉偏移后当本地时间使用的旧脚本可能出现 7 小时误差 |
| 已调整的 Bitbucket | JVM 已改金边，日志及依赖默认时区的插件/内部定时任务需留意；时区设置本身不重写 Git 提交的原始时间，参见专门记录。未修改 Jenkins/XXL-JOB 配置 |

当前建议保留现有 Jira 服务层时间配置和用户层金边设置，接受接口继续以 UTC 表示时间。只有遇到确实使用 JVM 默认时区且不能配置的功能异常，或明确要求日志统一金边时，再按备份、定时任务盘点、维护重启和接口验收流程调整服务层时区。

依据：[Jira 7.12 日期与时区模型](https://docs.atlassian.com/software/jira/docs/api/7.12.0/com/atlassian/jira/datetime/package-summary.html)、[Atlassian Scheduler 默认时区约定](https://docs.atlassian.com/atlassian-scheduler/1.8.7/apidocs/com/atlassian/scheduler/core/spi/SchedulerServiceConfiguration.html)、[Jira JVM 时区设置](https://support.atlassian.com/jira/kb/set-the-timezone-for-the-java-environment-for-jira-data-center/)。
