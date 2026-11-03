# 2026-10-31 OTWMS 磁盘满载检查与恢复

## 结论

16:56–16:57（UTC+7）确认根盘和 inode 再次满载。用户随后授权先清理，16:58 保留日志尾部并原位截断 stdout，根盘恢复至 30.6%，可用约 34.6 GiB；临时写入与 HTTP 通过。未重启、未清理 `/tmp`/业务文件、未部署或操作数据库。永久治理仍未完成。

## 实时证据

| 项目 | 结果 |
|---|---|
| 实例/区域 | `otwms-group-fql0`，`asia-southeast1-a`，RUNNING，实例组当前无操作 |
| 模板 | `otwms-instance-template-20250509-20250602-144152`，成员版本时间 10-20 |
| 根盘 | 约 49.8 GiB，100%，余 20 KiB |
| inode | 100%（四舍五入），356,552 个中仅余 171 |
| `/root/otwms-backend.log` | 实际约 34.6 GiB，非稀疏大空洞导致的误报；stdout 非 append |
| `/tmp` | 277,818 文件，逻辑约 8.31 GiB；包含下列 POI 文件，不能重复相加 |
| `/tmp/poifiles` | 45 文件，逻辑约 6.65 GiB；其中 35 个超过 24 小时，约 5.92 GiB |
| Java | PID 2395，RSS 约 13.0 GiB；本次采样无打开的 POI 文件，但不据此直接授权删除 |
| 已删除但仍打开的临时文件 | 832 个，实际约 186 MiB；不是主要占用 |
| HTTP | 本机首页 200；不能替代导出/打印写入验收 |

## 原因与下一步

- 启动参数仍覆盖 `logging.level.org.springframework=DEBUG`；1 MiB 尾部统计 DEBUG 1,878、INFO 544、WARN 240、ERROR 17，出现 6 次空间不足错误。未输出或保存原始业务日志。
- `/etc/logrotate.d` 无 OTWMS/BladeX 对应项；当前 JAR 缺少 `WorkbookResources.class` 和保留期配置标记。JAR mtime 为 10-20，不能把此前实例的 JAR 哈希/构建号当成这台的新版本依据；本次未重新查 Git/Jenkins。
- 存在 10-20 至 10-23 的超 7 天 XXL-JOB 日期目录，旧配置/资源释放风险仍在；首要容量来源仍是应用日志。
- 止血已按 [Runbook](RUNBOOK.md) 完成；POI/其他临时文件仍未删除，必须另核对归属、打开状态和保留规则，禁止直接清空 `/tmp`。
- 永久治理仍需 Jenkins 发布、移除 DEBUG 覆盖、有界 stdout/有效日志配置、实例模板固化与告警。见 [后续计划](FOLLOW_UP_PLAN.md)。

复用评估：现有 `scripts/check_disk_pressure.py` 已覆盖本次检查，无需新增重复 Skill/脚本。此前事件见 [10-16](INCIDENT_2026-10-16_DISK_FULL_RECURRENCE.md)。

## 16:58–17:00 恢复验收

- `recover_application_log.py --execute` 核对主机及 Java stdout inode，先在独立 `/run` 保存并验证尾部 50 MiB，再原位截断。丢弃较早日志，不能靠代码回退恢复。
- 证据：`/root/otwms-backend-tail-20261031T165843+0700.log.gz`，4,983,546 B，权限 `600`；尾部原始数据 SHA-256 `14041ca120eab80dc817bf1db65c6883409a3dc8c3e2377ebd43979c4eb4855e`，迁移后再次核验通过。
- 根盘从 100% 降至 30.6%，余 37,113,556,992 B（约 34.6 GiB）；inode 从仅余 171 恢复至约 2,575 万（1.4% 使用率），源于 XFS 可用空间恢复，不是删除了临时文件。
- Java PID 2395 不变，HTTP 200，独立 `/tmp` 测试文件的写入/fsync/回读通过，测试文件随后删除。报表导出/打印仍需用户业务验收。
- 日志实际降至约 2.4 MiB，旧偏移令逻辑长度仍约 34.6 GiB；短采样增长约 22 KiB/s，不能当作恒定日增长率。`/tmp` 及 POI 占用仍在。

## 永久治理核查与执行顺序

1. 远程最新 master 为 `7f8b78df7`（10-20 PR #3040）；10-03 修复 `a5cc1f94e` 仍只在 `codex/fix-disk-pressure-retention`，未合并。最新 master 仍设置任务日志保留 1 天。准备实施时同步最新 master 的业务变化，再完整构建、QA 和评审；本次只 fetch，未改分支或推送。
2. Jenkins 当前可读取最近生产构建为 `#195`，10-20 20:27:28（UTC+7）成功，配置构建 `*/master`；不可再将 #193 当成当前最近构建。本次未比对 #195 产物哈希，不推定精确运行提交。
3. 分开治理 stdout 与 Logback：修改实际启动入口，移除强制 DEBUG，让必要 stdout 有界；确认修复后的日志 XML 确实加载，不能只发布 XML 就认为 stdout 会轮转。Jenkins Job 内联 shell 未找到 DEBUG/stdout 标记；模板 startup-script 明确提到 `otwms-backend.log`，但未检出直接的 Spring DEBUG 字符串，具体参数来源仍需定位。
4. 模板仍为 50 GB，清理策略/启动修复须固化到新模板和发布链路，保留旧 JAR/配置/模板回退点；不要只修当前实例。磁盘/inode 80%/95% 告警与日志增长监控仍需接入。
5. 经独立确认后用 Jenkins 受控发布，验收导出/打印、取消导出临时文件释放、任务日志超期清理、日志轮转及实例替换后配置保留。POI 35 个超 24 小时文件约 5.92 GiB，可另行核对后讨论清理，不自动扩大本次范围。
