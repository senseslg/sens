# Google OTWMS Overview

## 目标

- 维护 OTWMS 在 GCP 上的生产与 UAT 访问方式。
- 及时识别磁盘、日志、Java 进程和 deleted file handle 风险。
- 把已验证的故障现象、处理方式和恢复验证步骤沉淀下来。
- 逐步将人工巡检发展为可判断、可控且有验证闭环的工具。

## 环境

| 环境 | GCP Project | Zone | 实例 |
|---|---|---|---|
| Production | `cambodian-express` | `asia-southeast1-a` | Managed Instance Group 中名称为 `otwms-group-*` 的活动实例 |
| UAT | `cambodian-express` | `asia-southeast1-a` | `otwms-uat` |

SSH 用户为 `senseslg`。本地 GCloud CLI SSH 已于来源记录更新时恢复，新 SSH Key 已生效且无 passphrase；仓库不保存私钥内容。

## 生产实例特性

- 生产实例由 Managed Instance Group 管理。
- 来源快照中的实例名是 `otwms-group-5dbm`，但实例重建后名称可能变化。
- 登录前应动态查询当前 `otwms-group-*` 活动实例。

## 2026-07-15 状态快照

以下仅代表来源文档在 `2026-07-15` 的检查结果，不代表实时状态：

- 磁盘容量：`50G`
- 已占用：约 `6.7G`
- Java：正常运行
- Deleted file handle：未发现
- Docker：未使用

## 已知主要风险

### 日志增长导致磁盘压力

来源记录识别到的主要日志：

- `/home/daniel/bladex.log`：事故时约 `1.9G`
- `/home/daniel/nohup.out`：事故时约 `300M`

Java 持续写入日志可能造成磁盘压力。如果日志已删除或截断但进程仍持有文件句柄，空间可能不会立即释放，需要同时检查 deleted file handle。

### 实例名变化

固定保存某个 `otwms-group-*` 实例名会在 MIG 重建后失效。自动化脚本和人工操作都应先发现实例，再连接。

### UAT 默认 SSH 用户错误

GCloud CLI 可能默认使用本机用户 `lingang`，而 OTWMS UAT 应显式使用 `senseslg@otwms-uat`。

共享对话中的 UAT 快照还确认：`Permission denied (publickey,...)` 是认证失败，不是磁盘满载；对应监控显示 `sda2` 使用率约 `18%–20%`、已使用约 `4.7 GiB`。详细排查见 `SSH_TROUBLESHOOTING.md`。

## 运维边界

- 默认先执行只读巡检。
- `kill Java`、截断日志、重启应用等会影响生产服务的动作，必须在明确授权和恢复计划下执行。
- 修复后必须重新验证磁盘、Java、deleted file handle 和应用状态。
- 本仓库不保存 SSH 私钥、凭证或其他敏感配置。
