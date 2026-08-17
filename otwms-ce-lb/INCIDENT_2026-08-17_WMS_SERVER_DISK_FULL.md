# Incident: WMS Server Disk Full

## 当前结论

`wms-server` 的 500 GB 根分区已 100% 满载，主要由 `/home/daniel` 下数个历史大文件占用；同时 `script/` 的大量文件和目录造成 inode 压力。未发现 deleted file handle，journal 与 `/var/log` 不是主要容量来源。

## 证据快照

| 路径 | 约占用 | 状态 |
|---|---:|---|
| `/home/daniel/spider.log` | 405 GiB | 最大占用；属主 `daniel`，最后修改 `2026-08-14 07:29 +07`，检查时未被进程打开 |
| `/home/daniel/tms_backup_20210803.sql` | 55 GiB | 2021 年历史数据库备份；删除前必须确认备份策略和可恢复副本 |
| `/home/daniel/sql.zip` | 5.2 GiB | 2021 年压缩文件；内容与保留要求待确认 |
| `/home/daniel/x.log` | 1.3 GiB | 2023 年日志；产生源待确认 |
| `/home/daniel/script` | 1.5 GiB | 约 129,344 个文件、25,871 个目录，是 inode 压力来源之一 |
| `/usr/local/cewms` | 3.1 GiB | CEWMS 发布目录，不是容量主因 |
| systemd journal | 约 92 MiB | 不是容量主因 |
| `/var/log` | 约 279 MiB | 不是容量主因 |

## 影响信号

- 根分区可用空间仅约 20 KB，inode 可用约 20K。
- `cewms.service` 显示 active，但本机 HTTP 返回空响应。
- 最近 7 天出现 56 次 `No space left on device`。
- 最近 24 小时约有 196 行错误关键词信号。

## 安全处置顺序

以下是建议，不代表已获授权执行：

1. 确认 `spider.log`、SQL 备份和压缩包的业务负责人、保留要求与外部备份。
2. 先准备可恢复副本，再决定删除、归档或截断；不要直接删除数据库备份。
3. 如果处理日志，先再次确认文件没有被进程持有，并记录处理前后空间。
4. 清理后验证 `df -h`、`df -i`、`cewms.service`、本机 HTTP 和关键业务入口。
5. 为日志、备份与 `script/` 任务增加轮转、保留期、容量/inode 告警和定期验证。
6. 评估扩容或迁移，避免继续依赖单个 500 GB 根分区。

## 操作边界

本次仅执行只读检查，未删除、截断、压缩、移动文件，也未重启 CEWMS。任何清理必须获得明确授权并准备回滚与恢复验证。
