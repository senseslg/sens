# 2026-08-22 UAT 前端 i18n Lifecycle 删除

## 结论

`gs://otwms-frontend-uat/i18n/` 下 3 个翻译 JSON 被桶级 90 天 Object Lifecycle Management 删除并进入 7 天软删除保护。三者已按明确 generation 恢复；恢复后的 live 对象数量、大小和 MD5 与删除前一致，公网 URL 均返回 HTTP 200，业务已由使用方确认恢复。

根因具有高置信度：3 个对象创建于 `2026-05-23`，在约 90 天后的同一毫秒被删除；桶内创建于前一天的其他旧对象也在前一天的 Lifecycle 批次进入软删除。用户在故障后看到并移除了 90 天删除规则。Cloud Storage Lifecycle 的 `age` 按对象创建时间计算，不是按最后访问或“未操作”时间计算。

## 影响对象与恢复结果

| 对象 | 大小 | 原软删除 generation | 新 live generation | 校验 |
|---|---:|---:|---:|---|
| `i18n/ccsl/ccsl_translations.json` | 113,262 B | `1779523457325150` | `1787365376271256` | MD5 一致，HTTP 200 |
| `i18n/courier/courier_translations.json` | 39,997 B | `1779523586066947` | `1787365376377151` | MD5 一致，HTTP 200 |
| `i18n/franchisee/franchise_translations.json` | 48,204 B | `1779523378649277` | `1787365376382239` | MD5 一致，HTTP 200 |

合计 3 个对象、201,463 B。恢复产生新的 live generation；原软删除 generation 会继续保留至其 hard delete 时间，这是正常行为。

## 时间线

以下时间均为 Asia/Shanghai：

| 时间 | 事件 |
|---|---|
| `2026-08-22 01:45:07` | 3 个 i18n 对象在同一 Lifecycle 批次进入软删除 |
| `2026-08-22 10:00:09` | 90 天 Lifecycle 规则被人工移除；此操作发生在删除之后 |
| `2026-08-22 10:22:56` | 3 个明确 generation 恢复为新的 live 对象 |
| `2026-08-22 10:32` | 数量、大小、MD5、类型和公网 HTTP 200 验证通过 |

删除前的对象 hard delete 时间为 `2026-08-29 01:45:07`（对应 7 天软删除保护）。

## 根因证据

- 当前桶的 soft delete 保留期为 `604800` 秒，即 7 天。
- 3 个 i18n 对象创建于 `2026-05-23 16:02`～`16:06`，在约 90 天后同时被删除。
- `WOEvidence/` 下创建于 `2026-05-22` 的对象和 `test.jpg` 在 `2026-08-21` 先一轮进入软删除，同样符合按创建日期逐日清理的 Lifecycle 模式。
- Lifecycle 移除后的桶配置已不再包含删除规则，桶更新时间与人工移除审计记录一致。
- UAT 前端 Jenkins 部署命令是 `gsutil cp -r * gs://otwms-frontend-uat/`，不包含 `rm`、`rsync -d` 或桶清空操作。
- UAT 前端最近一次 Jenkins 构建为 `2026-08-12`，不在本次删除时段。

因此，人工删除或 Jenkins 部署导致本次删除的可能性很低，桶级 90 天 Lifecycle 是最符合全部时间与对象分布的原因。

## 审计限制

- 项目未启用 Cloud Storage Data Access Audit Logs。
- 即使启用，Google Cloud Audit Logs 也不跟踪 Object Lifecycle Management 自动执行的对象变更。
- 本次没有预先配置 Cloud Storage usage logs，因此无法取得 Lifecycle 自动删除请求的直接日志主体。
- 审计日志只能确认 Lifecycle 规则在删除之后被人工移除，不能还原被移除前规则的完整 JSON。

如需以后直接追踪 Lifecycle 或公共对象访问，应评估为该桶单独配置 Cloud Storage usage logs。

## 其他软删除对象

全桶检查还发现以下对象处于软删除状态，但不属于本次用户指定的 `i18n/` 恢复范围，因此未擅自恢复：

- `WOEvidence/`：5 个对象（包含目录标记），预计于 `2026-08-27 16:23` 至 `2026-08-28 01:58` 陆续 hard delete；
- `test.jpg`：1 个对象，预计于 `2026-08-28 01:58` hard delete。

是否恢复这些对象需要业务负责人在 hard delete 前确认。

## 后续防护

1. 保留当前 7 天 soft delete，定期验证恢复流程。
2. 静态前端业务桶不要使用未限定范围的桶级 `Delete + age` 规则。
3. 如需清理临时文件，使用明确前缀/后缀，并在启用前导出命中对象清单。
4. Lifecycle 规则变更需要记录负责人、目的、命中范围、保留期和回滚方式。
5. 为关键静态文件增加可用性监控，对 HTTP 404、对象数量突降和翻译加载失败告警。

## 官方参考

- [Cloud Storage Object Lifecycle Management](https://cloud.google.com/storage/docs/lifecycle)
- [Cloud Storage soft delete overview](https://cloud.google.com/storage/docs/soft-delete)
- [Cloud Audit Logs with Cloud Storage](https://cloud.google.com/storage/docs/audit-logging)
- [Cloud Storage usage logs](https://cloud.google.com/storage/docs/access-logs)
