# OTWMS 磁盘与 inode 排查

## 适用场景

用于 OTWMS 导出、打印、任务日志或临时文件突然失败，且怀疑磁盘容量或 inode 耗尽时。默认只读，不输出 Java 完整命令行，避免泄露启动参数中的凭据。

## 固定检查顺序

1. 同时检查 `df -h` 和 `df -i`；任一接近 100% 都能造成写文件失败。
2. 区分文件逻辑大小与实际占用。被截断但仍由进程持有偏移的日志可能是稀疏文件，需同时看 `stat` 与 `du`。
3. 找出最大文件、最多文件的目录，并检查 Java 是否仍打开目标文件；已删除但仍打开的文件只会在文件描述符关闭后释放空间。
4. 分别核对应用日志、`/tmp/YYYY-MM-DD/` XXL-JOB 日志和 `/tmp/poifiles/` POI 临时文件。
5. 释放空间后复核容量、inode、Java 进程、端口和本机 HTTP；业务导出/打印仍需业务账号验收。

## 自动巡检

```bash
python3 otwms-server/scripts/check_disk_pressure.py \
  --project <project-id> \
  --zone <zone> \
  --instance <current-instance>
```

退出码：`0` 正常，`1` 有预警，`2` 容量/inode/HTTP 严重异常，`3` 采集失败。加 `--json` 可用于监控接入。实例组成员会变化，运行前必须查询当前实例，不能长期写死名称。

## 治理边界

- **应用日志：** 配置受控轮转并降低生产日志量；当前进程以非 append 方式持有日志，单纯 `copytruncate` 会留下稀疏文件，需在 Jenkins 受控重启后验证轮转方案。
- **XXL-JOB：** `xxl-job-core 2.3.1` 的保留天数小于 3 会关闭清理；配置至少 3 天，建议 7 天并走代码发布。
- **POI：** `SXSSFWorkbook.close()` 不删除临时 XML，必须在 `finally` 中调用 `dispose()`；服务器定期删除只适合作为兜底。
- **定期删除：** 系统已有 `/tmp` 10 天 `systemd-tmpfiles` 策略。更短周期只允许清理名称和年龄严格匹配、且未被进程打开的临时文件；业务日志保留期、审计需求和回退方式确认前，不安装通用递归删除任务。
- **容量：** 托管实例组应通过新实例模板扩大启动盘；只扩当前成员会在实例替换后丢失。

巡检新增 stdout append/旧偏移与日志增长采样；无 append 时截断仍会形成稀疏文件，不自动清理。XFS inode 总数随可用空间变化，恢复后百分比下降不代表临时文件已删除。

事故见 [2026-09-21 记录](../INCIDENT_2026-09-21_EXPORT_PRINT_DISK_FULL.md) 和 [2026-10-03 复发](../INCIDENT_2026-10-03_DISK_FULL_RECURRENCE.md)。修复专项验证使用 `scripts/verify_disk_fixes.py`，不替代整应用构建和生产验收。
