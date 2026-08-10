# Incident Log

## 2026-07-15 快照：OTWMS UAT SSH 公钥认证失败

### 现象

```text
Permission denied (publickey,gssapi-keyex,gssapi-with-mic)
```

用户同时看到 GCP 磁盘图约 `5 GiB`，一度怀疑磁盘已满。

### 证据

- `sda2` 使用率约 `18%–20%`，已使用约 `4.7 GiB`。
- `sda1` 已使用约 `0.01 GiB`。
- SSH 服务返回认证拒绝，而不是连接超时或 `No space left on device`。

### 结论

- UAT 当时没有磁盘满载。
- `5 GiB` 表示已使用容量，不是磁盘总容量。
- 优先排查远程用户名、SSH Key、GCP SSH Metadata 和 OS Login。

### 状态

- 诊断方向已明确。
- 最终修复结果尚未从共享对话中确认。
- 详细记录见 [`conversations/server-disk-and-uat-ssh.md`](conversations/server-disk-and-uat-ssh.md)。

## 2026-07-15 前后：OTWMS 生产磁盘空间不足

> 来源摘要更新时间为 `2026-07-15`，未提供事故发生的精确时间，因此本记录不虚构具体时间点。

### 现象

- Google Troubleshoot 提示磁盘空间不足。
- 主要日志占用：
  - `/home/daniel/bladex.log`：约 `1.9G`
  - `/home/daniel/nohup.out`：约 `300M`

### 实际处理

同事执行了以下流程：

1. 终止 Java 进程。
2. 清理两个主要日志。
3. 重启应用。

### 已确认结果

- 磁盘空间恢复。
- 来源记录更新时，`50G` 磁盘总占用约 `6.7G`。
- Java 正常运行。
- 未发现 deleted file handle。
- 环境未使用 Docker。

### 分析

以下属于基于来源记录的分析：

- Java 持续写入日志是磁盘压力的重要来源。
- 终止 Java 后，进程持有的日志文件句柄被释放，有助于空间真正回收。
- 单纯清理日志不应替代对日志增长、轮转策略和 deleted file handle 的持续检查。

### 后续行动

- [ ] 确认 `bladex.log` 和 `nohup.out` 的日志轮转或保留策略。
- [ ] 使用巡检工具持续检查磁盘、Java、deleted file handle 和日志大小。
- [ ] 为巡检结果增加 `OK / WARNING / CRITICAL` 判定。
- [ ] 在开发自动修复前，明确生产授权、回滚和恢复验证要求。

### 安全提醒

`kill Java`、截断日志和重启应用均为高影响生产操作。未来只能在明确授权、确认目标进程并准备恢复验证后执行。
