# 2026-10-16 OTWMS 磁盘再次满载

## 结论与状态

同一实例再次被无界 stdout 日志撑满。用户要求排查并处理后，保留并验证最近 50 MiB，再原位截断 `/root/otwms-backend.log`，释放约 39.9 GiB。根盘恢复至 19.8%，写入与 HTTP 正常；未重启 Java、未清理业务或 `/tmp` 文件。导出/打印仍需用户验收，永久治理未完成。时间均为 UTC+7。

## 现场与止血

| 项目 | 15:11 故障 | 15:13 复验 |
|---|---|---|
| 实例 | `otwms-group-1h76`，`asia-southeast1-a` | 同一实例，组内唯一成员 |
| 根盘 | 约 49.8 GiB，100%，仅余 20 KiB | 19.8%，约 39.9 GiB 可用 |
| inode | 98.1%，余 6,704 | 1.3%，余约 2,576 万 |
| 应用日志实际占用 | 42,879,340,544 B（39.9 GiB） | 约 15 MiB，并继续增长 |
| 应用日志逻辑长度 | 约 78.8 GiB | 仍约 78.8 GiB，为旧偏移形成的稀疏文件 |
| Java | PID 2442，RSS 约 13.2 GiB | PID 不变；本机 HTTP 200；临时写入/fsync/回读通过 |
| `/tmp` | 273,193 文件，逻辑约 3.13 GiB | 未清空 |

15:12:44 保存尾部至独立 `/run` 文件系统，gzip 解压逐字节验证后才截断；迁至 `/root/otwms-backend-tail-20261016T151244+0700.log.gz` 再验 SHA-256。压缩后 4,864,210 B、权限 `600`；旧日志较早部分已永久丢弃。尾部原始数据 SHA-256：`8f92c516b1a53c2983f31ff673aebae9e02f50d1f558d7f9f08876c9e2b5730f`。

inode 百分比下降源于 XFS 可用容量恢复后 inode 总量增加，**不是删除临时文件**。Java 仍持有 1,124 个已删除临时文件，约 310 MiB；未通过重启回收。

## 根因证据

- Java stdout 仍指向该文件，非 `O_APPEND`；10-03 截断后又实际累积约 39.9 GiB。不能以稀疏文件逻辑长度判断磁盘占用。
- 当前启动参数仍包含 `logging.level.org.springframework = DEBUG`；恢复后 2 MiB 尾部统计 DEBUG 1,454、INFO 429、WARN 87。短样本增长约 40 KiB/s，不能当作恒定日增长预测。
- `/etc/logrotate.d` 没有 OTWMS/BladeX 对应项。JAR 内虽然有 `logback-prod.xml` 和 RollingFileAppender，但 stdout 文件仍未受控；XML 存在不证明被加载，也不证明 stdout 有轮转。
- 生产 JAR 缺少修复新增的 `WorkbookResources.class` 及 `JobConfig` 的 `log-retention-days` 字符串，不能认为 10-03 分支修复已在本实例生效。JAR SHA-256：`d3a630f4f6fb90cdace66e67a53966a32cb87c59e592b0e2f419741ff9a7441f`；未确证 Git 提交。
- 实例组仍引用 `otwms-instance-template-20250509-20250602-144152`，50 GB 根盘与启动方式未固化治理。
- `/tmp` 约 27 万文件、POI 约 1.45 GiB，且存在超过 7 天的日期目录，是次要持续风险；未授权扩大临时文件清理范围。

## 后续与复用

后续只读发布核查：远程修复提交 `a5cc1f94e` 未合并进最新 `master` `5b5af4ae2`；Jenkins 当前可读取的最近生产构建为 09-22 的成功 `#193`，工作区 JAR 与本实例 SHA-256 完全一致。确认上次修复未进入当前生产；发布映射见 [源码部署记录](SOURCE_DEPLOYMENT_MAP.md)。未触发构建/发布。

先按 [发布计划](FOLLOW_UP_PLAN.md) 完成公司构建/业务回归，再经授权 Jenkins 发布，移除 DEBUG 覆盖、确保有效日志 XML 和有界 stdout，最终固化模板并启用容量告警。本次没有部署、改启动参数、安装定时清理或修改数据库。

沿用 [只读巡检](scripts/check_disk_pressure.py)，新增 [手动止血脚本](scripts/recover_application_log.py)：默认 dry-run；执行须显式 `--execute`，核对主机、常规文件与 Java stdout inode、至少 10 GiB 实际日志、独立证据文件系统，验证尾部后才截断。不作为自动定期删除。已验证实际执行、默认只读及本地/远端生成代码语法；无需重复创建独立 Codex Skill。
