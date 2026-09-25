# 2026-09-21 OTWMS 导出与打印失效

## 当前结论

`Report > Daily Report` 导出和 `Order > Order List > Print` 同时失效的直接原因是生产实例 `otwms-group-1ktm` 根文件系统容量与 inode 均已耗尽。已在不重启 Java 的情况下保留日志尾部证据并原位截断超大日志，根盘恢复到 22%、inode 恢复到 2%，本机 HTTP 返回 200；业务已恢复。

## 证据快照（2026-09-21 11:06，UTC+7）

| 项目 | 结果 |
|---|---|
| 根分区 | XFS 50 GB，已用 50 GB，可用约 20 KB，100% |
| inode | 约 341K，已用 340K，仅余 222，100% |
| 最大文件 | `/root/otwms-backend.log` 约 42.2 GB，由 Java 标准输出持续写入 |
| `/tmp` | 约 5.0 GB、269,915 个文件 |
| Excel 临时文件 | `/tmp/poifiles` 约 2.45 GB；存在约 235 MB 的 `poi-sxssf-sheet*.xml` |
| 按日任务日志 | `/tmp/2026-09-11` 至 `09-20` 每日约 25,800 个 `.log`，单日约 235–257 MB |
| 系统日志 | rsyslog 明确持续报 `No space left on device` |
| 应用状态 | Java、8080 和 9999 仍运行；公网首页 200，不代表文件生成功能可用 |

当日上午应用日志记录了 `DailyReportExportVO` 导出错误。源码中 Daily Report 使用 Apache POI `SXSSFWorkbook`，会创建磁盘临时 XML；Order Print 调用 `/otwms/order/order-print` 并由后端实时渲染 PDF。容量或 inode 任一耗尽都足以导致这些路径失败。

## 占用原因

- `BladeX.jar` 的标准输出直接连接 `/root/otwms-backend.log`；未发现匹配 OTWMS/BladeX 日志的 logrotate 配置。
- Java 启动参数启用了 Spring DEBUG 日志，生产日志包含高频、体积很大的请求/结果内容，使单文件持续增长。
- XXL-JOB 执行日志按日期留在 `/tmp/YYYY-MM-DD/`，造成约 27 万文件并耗尽 inode。源码设置 `setLogRetentionDays(1)`，但 `xxl-job-core 2.3.1` 的清理线程对 `<3` 直接返回，因此该配置实际关闭了清理。
- `ExportController` 写出 `SXSSFWorkbook` 后没有调用 `dispose()`；POI 4.1.0 的 `close()` 也不会删除流式 Sheet 临时 XML，导致 `/tmp/poifiles` 残留。
- 系统已有每日 `systemd-tmpfiles-clean`，通用 `/tmp` 保留期为 10 天；它不能表达 XXL-JOB/POI 的业务保留和打开文件保护，不能作为唯一清理机制。
- 托管实例组使用的区域实例模板 `otwms-instance-template-20250509-20250602-144152` 仍配置 50 GB 启动盘；只扩当前实例磁盘不能解决实例重建后的容量配置。

## 已执行恢复（2026-09-21 11:15，UTC+7）

- 紧急处理前一次 `lsof` 检查未列出 `/tmp` 打开文件；恢复后的 `/proc/<pid>/fd` 深入检查证明该结果不完整，因此后续清理不能只依赖单一工具。
- 将应用日志最近 50 MB 压缩保存在 `/root/otwms-backend-tail-20260921T1115.log.gz`，权限设为 `600`。
- 对仍由 Java 持有的 `/root/otwms-backend.log` 原位截断，没有删除文件、重启进程或修改 JAR。
- 根盘由 100% 降至 22%，inode 由 100% 降至 2%；`/tmp` 写入测试及 `127.0.0.1:8080` HTTP 200 均通过。
- 截断后 Java 文件描述符仍保留旧偏移，当前日志逻辑大小约 42.2 GB、实际占用约 33 MB，是稀疏文件；后续 Jenkins 受控重启可重置偏移。
- 未删除 XXL-JOB 历史日志或 POI 临时文件，避免在已有空间恢复后继续扩大生产变更范围。

恢复后复查发现 Java 仍持有 466 个已从目录删除的 Undertow 上传临时文件（实际约 130 MB）和 2 个正在使用的 POI 文件（约 9.8 MB）。这说明不能用“目录中看不到”代替打开文件检查，也不能直接清空 `/tmp`。应用日志在 10 秒内新增约 304 KB，当前速率仍可能每天增长数 GB。

## 长期方案

1. **代码修复：** `JobConfig` 保留期改为至少 3 天，建议 7 天；`ExportController` 在 `finally` 中对 `SXSSFWorkbook` 执行 `dispose()` 并关闭 workbook。
2. **日志治理：** 将生产 Spring 日志降到 INFO，避免记录完整业务结果；在 Jenkins 受控重启后配置并验证日志轮转、压缩和保留期。当前非 append 文件描述符下不能只依赖 `copytruncate`。
3. **兜底清理：** 保留现有 `systemd-tmpfiles` 10 天策略；如需更短周期，只清理超过保留期的精确日期目录和超过 24 小时、且未被打开的 POI 临时文件，并通过 `/proc/<pid>/fd` 或等效方式跳过打开文件。先确认审计保留期，不使用无边界递归删除。
4. **监控：** 使用 [`scripts/check_disk_pressure.py`](scripts/check_disk_pressure.py) 同时监控容量、inode、日志实际占用、临时文件数和本机 HTTP，建议 80% 告警、95% 严重告警。
5. **持久扩容：** 新建更大启动盘的实例模板并滚动更新托管实例组，保留旧模板作为回滚点。

代码、轮转、定时清理、模板和实例替换均应走独立变更与验收；本次只完成紧急日志止血。

## 其他安全风险

Java 完整启动参数中存在明文生产凭据，本机普通用户可通过进程列表读取。应单独安排凭据轮换，并迁移至权限受控的环境文件或 Secret Manager；本记录不保存任何凭据值。
