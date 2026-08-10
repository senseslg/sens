# OTWMS SSH Troubleshooting

用于区分 SSH 认证失败、网络不可达、磁盘问题和应用进程问题。默认先执行只读诊断，不直接重启实例或覆盖密钥。

## 先根据错误分类

| 现象 | 更可能的方向 | 第一检查 |
|---|---|---|
| `Permission denied (publickey,...)` | 用户名、公钥、Metadata 或 OS Login 不匹配 | 显式指定远程用户并运行 `--troubleshoot` |
| `Connection timed out` | 网络、防火墙、实例或 SSH 服务不可达 | 实例状态、网络、Serial Port Output |
| `No space left on device` | 文件系统空间或 inode 不足 | `df -h`、`df -i`、日志与 deleted handle |
| 已登录但操作极慢 | CPU、磁盘 I/O、JVM GC 或应用压力 | CPU、I/O、Java 和系统负载 |

`Permission denied (publickey,...)` 表明网络已经到达 SSH 服务且服务器给出了认证响应；它不能证明应用正常，但通常不是“磁盘满导致完全无法连接”。

## UAT 推荐诊断

显式指定远程用户，避免 CLI 使用本机用户名：

```bash
gcloud compute ssh senseslg@otwms-uat \
  --project=cambodian-express \
  --zone=asia-southeast1-a \
  --troubleshoot
```

检查当前 GCloud 身份和本地 GCloud SSH 文件是否存在：

```bash
gcloud auth list
ls -lh ~/.ssh/google_compute_engine*
```

还需要核对：

- GCP Project 和 Zone 是否正确。
- 实例是否确实为 `otwms-uat`，而不是生产 MIG 实例。
- 远程用户名是否为 `senseslg`。
- 项目或实例 SSH Metadata 是否包含对应公钥。
- 是否启用了 OS Login，以及当前账号是否有相应权限。

## 关于覆盖 GCloud SSH Key

共享对话中曾建议使用 `--force-key-file-overwrite` 重新生成并上传 GCloud SSH Key。该参数可能替换本地 `google_compute_engine` 密钥文件，不应作为第一步直接执行。

执行前必须：

1. 查看 `--troubleshoot` 的明确结论。
2. 确认现有密钥是否仍被其他实例或流程使用。
3. 备份现有密钥文件。
4. 确认有权限更新目标项目或实例的 SSH 配置。

## 无法获得 SSH 响应时

如果错误不是 publickey 拒绝，而是超时或实例无响应，转到 Google Cloud Console 检查：

- VM Instance Status
- CPU 和 Memory
- Disk utilization / Disk usage
- Serial Port Output
- 必要时使用 Serial Console

Serial Console 不依赖普通 SSH 登录，可用于确认启动、磁盘或系统服务问题。使用前仍需遵守项目权限和生产操作边界。

## 正确理解磁盘监控

- `Disk Space Utilization` 是使用率，通常以百分比表示。
- `Disk Space Usage` 是已使用容量，不等于磁盘总容量。
- 图上显示 `4.7 GiB` 只能说明已使用约 `4.7 GiB`，不能单独得出磁盘总容量为 `5 GiB`。
- 必须同时查看百分比、挂载点和磁盘总容量。

共享对话中的 UAT 监控快照显示：

- `sda2` 使用率约 `18%–20%`，已使用约 `4.7 GiB`。
- `sda1` 使用率接近 `0%`，已使用约 `0.01 GiB`。

因此当时 UAT 并未磁盘满载，SSH 失败应优先按认证问题处理。
