# Office Server Baseline

- 检查时间：`2026-08-08 18:24 +07`
- 检查方式：通过 Tailscale SSH 只读采集
- 结论：SSH Key 登录已验证可用；主机运行正常、磁盘空间充足，但防火墙、FileVault 和备份均未启用，远程桌面服务对所有接口监听。

## 资产摘要

| 项目 | 当前值 |
|---|---|
| 设备 | Apple iMac `iMac21,1` |
| 芯片 | Apple M1，8 核 |
| 内存 | 8 GB |
| 系统 | macOS 26.3，Build `25D125` |
| 架构 | arm64 |
| 主机名 | `ceaidevis-iMac.local` |
| 系统盘 | 460 GiB；Data 卷已用约 51 GiB，可用约 385 GiB |
| 连续运行 | 检查时约 4 小时 |

## 网络与远程访问

- 主要局域网接口：`en1`，地址为 `192.168.0.x`，网关为 `192.168.0.1`。
- Tailscale：`1.102.2`，本机地址为 `100.116.3.x`，当前配置为可提供 Exit Node。
- SSH：TCP `22` 同时监听 IPv4 和 IPv6。
- 屏幕共享：TCP `5900` 对所有接口监听。
- Apple Remote Desktop：TCP `3283` 对所有接口监听。
- 另有 TCP `88` 和若干动态端口监听，服务归属尚未完整核对。

## SSH Key 状态

- 登录账号：`ceaidevi`，属于本机 `admin` 和 SSH 访问组。
- 公钥文件：`~/.ssh/authorized_keys`，权限 `600`。
- SSH 目录：`~/.ssh`，权限 `700`。
- 当前授权公钥：1 个。
- 已使用本机 `~/.ssh/id_ed25519`，在显式禁用密码和键盘交互认证后完成登录验证。
- 未修改服务器密码认证策略；在确认密钥备份和应急访问方案前，不建议直接关闭密码认证。

## 软件与运行状态

- 已安装：Tailscale、Codex、ChatGPT、Visual Studio Code、Ollama、Chrome、Telegram 等。
- 命令行基线：Python `3.9.6`、Git `2.50.1`。
- 未在当前 PATH 中发现 Homebrew、Docker、Podman、Node.js、MySQL 或 PostgreSQL。
- 检查时主要交互应用和 Tailscale 正常运行，未发现明显的 CPU 或磁盘容量压力。

## 安全与可恢复性

| 检查项 | 状态 | 判断 |
|---|---|---|
| macOS 应用防火墙 | 关闭 | 需确认暴露服务后启用 |
| 防火墙隐身模式 | 关闭 | 可与防火墙一并评估 |
| Gatekeeper | 开启 | 正常 |
| FileVault | 关闭 | 设备遗失或磁盘被取走时存在数据风险 |
| Time Machine | 未配置目标 | 当前缺少已验证的系统备份 |
| 自动重启 | `autorestart 0` | 断电恢复后可能不会自动开机 |
| 系统睡眠 | 接电时 `sleep 0` | 适合常驻服务器 |
| 网络唤醒 | 开启 | 适合远程访问 |

## 建议顺序

1. 确认这台 iMac 的服务用途、数据重要性和远程访问范围。
2. 配置并完成一次 Time Machine 或其他备份恢复验证。
3. 盘点 TCP `88`、`5900`、`3283` 和动态监听端口，关闭不需要的共享服务。
4. 评估启用 macOS 防火墙和 FileVault；FileVault 启用前必须保存恢复密钥并确认无人值守重启影响。
5. 若要求断电后自动恢复服务，评估启用 `autorestart` 并进行断电恢复测试。
6. 确认 SSH Key 已有安全备份和备用管理员访问后，再决定是否关闭密码认证。

## 边界

- 本次未使用 `sudo`，未修改防火墙、FileVault、共享服务、电源或备份设置。
- 网络地址已脱敏；未记录密码、私钥、完整公钥或 Tailscale 账户细节。
- 当前结论是检查时间点快照，不代表持续监控结果。
