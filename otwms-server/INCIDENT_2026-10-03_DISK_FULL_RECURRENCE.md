# 2026-10-03 OTWMS 磁盘满载复发

## 结论与状态

与 09-21 同类复发：新实例仍使用 50 GB 根盘，未轮转的 DEBUG 标准输出日志占实际空间约 38.9 GiB，并伴随 XXL-JOB/POI 临时文件积累。用户授权后，保留日志尾部并原位截断，未重启、未删除临时/业务文件。**空间与写入能力已恢复，业务导出/打印待用户验收；长期根除尚未完成。** 时间为 UTC+7。

## 现场与恢复

| 项目 | 15:38 故障 | 15:41 恢复验收 |
|---|---|---|
| 实例 | `otwms-group-1h76`，`asia-southeast1-a` | 同一实例 |
| 根盘 | 100%，余 20 KiB | 22%，余约 38.9 GiB |
| inode | 99.9%，余 337 | 1.4%，余约 2575 万 |
| `/root/otwms-backend.log` | 实际 41,759,166,464 字节 | 实际约 1 MiB；逻辑仍约 38.9 GiB |
| `/tmp` | 275,543 文件，约 4.35 GiB | 未清空，仍有约 27.6 万文件 |
| POI | 27 文件，约 2.64 GiB；Java 正在打开 2 个 | 未删除 |
| Java | PID 2442 | PID 未变，本机 HTTP 200，`/tmp` 写入/fsync/回读通过 |

- `15:41:07` 保存最近 50 MiB 到独立 `/run` 文件系统，gzip 解压逐字节核验通过后截断原日志，再移至 `/root/otwms-backend-tail-20261003T154107.log.gz`，权限 `600`，压缩后 4,879,517 字节。较早日志已丢弃，仅此操作获授权。
- XFS 可用空间恢复后 inode 总数从约 35 万增长至约 2611 万，因此 inode 百分比下降；**不是删除了 27 万临时文件**。
- stdout FD flags `0100001`，无 `O_APPEND`；截断不重置 Java 的旧写偏移，随后形成稀疏文件。判断必须看 `st_blocks/du`，不能看逻辑长度判断磁盘又满。
- Java 仍持有 476 个已删除临时文件，实际约 132 MiB；未重启回收。生产 JAR 未发现可用 `git.properties`，当前提交仍未确证。

## 为什么复发

- 实例启动于 09-22，已替换上次 `otwms-group-1ktm`；实例组仍引用 `otwms-instance-template-20250509-20250602-144152`，未固化此前治理。
- 启动参数仍含 Spring DEBUG 覆盖；约 2 MiB 尾部统计 DEBUG 712、INFO 175、WARN 36、ERROR 3，包含 6 次空间不足错误；未输出原始业务日志。
- `/etc/logrotate.d` 没有应用日志轮转。`15:46` 短采样约 34 KiB/s，仅作瞬时参考，不能当作每日恒定增长率。
- 最新远程 `master` `5ba65f13f` 仍配置 XXL-JOB 保留 1 天；2.3.1 对少于 3 天直接关闭清理。日期目录从 09-22 延续至 10-03。
- 导出后仍未 dispose/close workbook；约 235 MB 的流式 XML 多次残留。系统 `/tmp` 10 天策略不能替代业务生命周期管理。

## 修复分支（已提交推送，未部署）

后端分支 `codex/fix-disk-pressure-retention`，开分支前执行 `git fetch origin master`，直接从当时最新 `origin/master` `5ba65f13f`（PR #3026）创建，不基于旧的日账单分支。用户授权后已提交并推送公司仓库，提交 `a5cc1f94e478058d79eae1851b8029d2a74afa2c`；相对该基线只有一个修复提交。远程哈希核对一致、后端工作区干净；未创建 PR、未合并、未触发生产构建或部署。此基线是当时最新生产分支源码，不是已确认的生产运行 JAR 版本。

- `JobConfig`：默认保留 7 天，可由 `xxl.job.log-retention-days` 配置，下限 3 天。
- `ExportController`：统一 finally 释放 workbook；只在成功取得信号量时释放，防止拒绝请求反而扩大并发上限。
- `WorkbookResources`：SXSSF dispose 后关闭，清理失败记告警、不覆盖原始异常；`ExportUtil` 覆盖两处普通创建表格异常路径。EasyPOI 批量构造在返回 workbook 前失败的路径仍需完整集成回归。
- `logback-prod.xml`：兼容 Logback 1.2.3 的大小/日期轮转，单文件 100 MB、7 天、归档总量 1 GB；主动文件另占空间。**仅修改资源文件不保证生效**，部署需确认 `logging.config` 并移除启动参数 DEBUG 覆盖。
- 专项回归通过：真实 POI 4.1.0 成功写出/中止导出临时文件清理；Logback 1.2.3 XML 启动；巡检异常分级。完整 Maven 编译因缺少旧私有 BladeX 等依赖及离线缓存来源问题未完成，不代表构建通过。

## 影响范围：并非只修改日志

| 范围 | 预期变化与验收边界 |
|---|---|
| XXL-JOB 执行日志 | 默认保留 7 天、下限 3 天；旧日志会被清理，历史执行日志查看受影响。未改任务调度或业务 handler；发布前确认保留期，并核对日期目录确实仅存任务日志 |
| 生产应用日志 | 文件名、轮转、压缩和保留上限变化，采集配置需匹配；运行配置未启用此 XML 或仍覆盖 DEBUG 时不能宣称日志治理已生效 |
| Excel 导出 | 成功/失败后释放 workbook 与 SXSSF 临时文件，覆盖使用公共 `/export` 的导出；未调整字段、查询、金额或输出业务内容，但需回归成功、失败、断连与大数据量导出 |
| 导出并发 | 仅取得许可的请求释放许可，恢复原有最多 10 个并发限制；繁忙时部分导出会被拒绝，用户可重试，不承诺无业务体验变化 |

没有修改订单/运单状态、账单计算、业务数据库写入、前端或 Order Print 的 PDF 逻辑；这些是源码变更范围结论，**不是整个系统绝不会受影响的保证**。共享后端发版仍需登录、订单查询、打印和执行器注册的冒烟检查。未改 schema，无本次数据库迁移；回退应用不能恢复已经清理的旧日志。

专项脚本只验证 POI 清理、Logback XML 和巡检分级，尚未验证完整 Controller 链路、信号量并发或生产日志轮转/清理实际效果。不得把“专项通过”写成“全量业务回归通过”。

## 尚需独立授权与验收

跟踪任务：[CE-2629 — OTWMS服务器日志满盘复发治理](https://issue.cambodianexpress.com/browse/CE-2629)，2026-10-03 经 API 创建，经办人 `sens`，状态开放；关联已解决的 CE-2626，跟踪长期治理与发布固化。本任务创建不代表生产变更获授权。

1. 修复分支已提交推送；下一步在公司构建环境完整构建与测试、评审合并。不直接编辑生产 JAR 或 Jenkins 工作区。
2. 经 Jenkins 同时上线资源释放、任务保留与有效日志配置，核对 JAR hash、进程、日志位置和 DEBUG 是否关闭；必要的 stdout 捕获必须另有有界保留，不能继续无界写当前文件。
3. 先验证正常导出、失败/取消导出、并发拒绝、打印和执行器注册，再观察 POI 文件释放、超过保留期的日志清理及连续日志增长。恢复首页不替代业务验收。
4. 将配置固化到实例模板/发布流程；容量扩展通过新模板实施，保留旧模板/JAR/启动配置。轮转及清理删除的旧日志无法靠代码回退恢复，须先确认审计保留期。
5. 设置容量/inode 80% 预警、95% 严重告警；没有安装定时删除或自动截断任务。禁止直接清空 `/tmp` 或误删正在使用的 POI 文件。

## 复用评估

增强既有 [只读巡检](scripts/check_disk_pressure.py)，增加 stdout append/偏移和日志增长采样，已在生产只读验收；新增 [本地专项回归脚本](scripts/verify_disk_fixes.py)，不连接数据库或 SSH。沿用根目录已有磁盘巡检流程，不另建重复 Skill，不生成未经长期验证的自动删除/修复任务。

依据：[XXL-JOB 2.3.1 清理源码](https://github.com/xuxueli/xxl-job/blob/2.3.1/xxl-job-core/src/main/java/com/xxl/job/core/thread/JobLogFileCleanThread.java)、[POI 4.1 SXSSFWorkbook](https://poi.apache.org/apidocs/4.1/org/apache/poi/xssf/streaming/SXSSFWorkbook.html)。历史事件见 [09-21 记录](INCIDENT_2026-09-21_EXPORT_PRINT_DISK_FULL.md)。
