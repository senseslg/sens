# 对话摘要：服务器硬盘清理建议

- 来源：[ChatGPT Shared Conversation](https://chatgpt.com/share/6a576418-463c-83ec-980b-9986551f2185)
- 页面标题：`服务器硬盘清理建议`
- 导入日期：`2026-07-15`
- 消息数量：`5`
- 关联范围：OTWMS UAT SSH、GCP 磁盘监控解释

## 最终摘要

用户遇到 OTWMS UAT SSH 登录失败，并怀疑 GCP 监控中显示的约 `5 GiB` 代表磁盘满载。终端实际错误为：

```text
Permission denied (publickey,gssapi-keyex,gssapi-with-mic)
```

监控截图显示 `sda2` 使用率约 `18%–20%`、已使用约 `4.7 GiB`，`sda1` 使用量约 `0.01 GiB`。因此当时磁盘并未满载；`5 GiB` 是已使用容量的坐标范围或显示值，不是磁盘总容量。

最终排查方向从“磁盘空间或 Java 导致 SSH 卡死”收敛为“SSH 用户名或公钥认证不匹配”。

## 已确认事实

- 目标环境是 `otwms-uat`，不是生产 `otwms-group-*` 实例。
- SSH 服务能够返回 publickey 拒绝，说明网络路径和 SSH 响应存在。
- UAT 磁盘监控在该快照时未显示空间满载。
- GCloud CLI 可能默认使用本机用户名 `lingang`，目标远程用户应显式写为 `senseslg`。

## 早期假设与最终结论

对话开始时曾考虑：

- 图表可能显示磁盘 I/O，而不是容量。
- Java Full GC 或 I/O 压力可能让 SSH 变慢。
- 其他分区可能已满。

这些是证据不足阶段的候选假设。看到终端错误和监控截图后，最终结论是：

- 磁盘没有满载。
- 当前 SSH 失败属于认证方向，应检查用户名、SSH Key、Metadata 和 OS Login。

## 后续动作

优先运行：

```bash
gcloud compute ssh senseslg@otwms-uat \
  --project=cambodian-express \
  --zone=asia-southeast1-a \
  --troubleshoot
```

然后根据诊断结果检查当前 GCloud 账号和本地 GCloud SSH Key。完整安全步骤见 [../SSH_TROUBLESHOOTING.md](../SSH_TROUBLESHOOTING.md)。

## 尚待确认

- `--troubleshoot` 的完整输出和最终修复结果。
- UAT 是否使用 OS Login。
- 现有 GCloud SSH Key 是否仍被其他实例依赖。

## 信息保护

原共享对话包含 UAT 外网地址。本摘要不复制该地址，因为完成长期排查记录并不需要保存它。
