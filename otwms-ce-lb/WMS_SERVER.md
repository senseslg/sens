# WMS Server

## 当前结论

`wms-server` 是 CEWMS .NET 管理后台的部署服务器，不是源码工作区。`cewms.service` 仍在运行，但根磁盘已 100% 满载、inode 使用率 97%，本机 HTTP 返回空响应，并出现持续的磁盘空间与应用错误信号，需要优先处置。

## 2026-08-17 只读基线

| 项目 | 状态 |
|---|---|
| GCP | `cambodian-express` / `asia-southeast1-a` / `wms-server` |
| SSH | 用户 `lingang`；无外部 IP，通过 IAP 登录 |
| OS | CentOS Linux 7，kernel `3.10.0-1160.83.1.el7.x86_64` |
| 资源 | 2 vCPU、约 1.8 GB 内存、无 Swap |
| 磁盘 | 500 GB XFS，100% 使用，仅剩约 20 KB |
| inode | 97% 使用 |
| 运行时间 | 约 1262 天 |
| 系统状态 | `degraded` |

## CEWMS 部署

- systemd 单元：`cewms.service`。
- 工作目录：`/usr/local/cewms/prod/publish`。
- 启动入口：`dotnet CE.WMS.Web.dll`。
- 环境：`ASPNETCORE_ENVIRONMENT=Prod`，监听 `0.0.0.0:80`。
- 服务用户：`root`。
- .NET Core：Host `3.1.32`；同时安装 2.2/3.1 SDK 与 Runtime。
- 发布目录约 3.1 GB，包含 DLL、PDB 和配置/静态资源；未发现 `.git`、`.sln`、`.csproj` 或 `.cs` 文件。
- 服务自 `2026-08-14 07:30 +07` 处于 active，systemd 最近结果为 `success`，但本机 HTTP 检查得到空响应。

## 源码位置判断

`wms-server` 保存的是编译后发布产物，不是源代码。源码更可能由 `wms-db` 上的 Bitbucket 管理，再由 Jenkins 构建/发布；具体仓库与 `CE.WMS.Web.dll` 的对应关系仍待通过 Bitbucket/Jenkins 元数据确认。

## 当前风险

- 根磁盘和 inode 同时接近耗尽，应用无法可靠写入日志、临时文件或业务数据。
- 最近 7 天 CEWMS journal 中统计到 56 次 `No space left on device`。
- 最近 24 小时统计到约 196 行 error/fail/exception/fatal 信号；未复制原始业务日志。
- 应用使用已经停止常规支持的 CentOS 7 与 .NET Core 3.1，并以 root 身份运行。
- 服务器连续运行超过三年且无 Swap，恢复和迁移需要先验证备份与回滚。

磁盘证据和安全处置顺序见 [INCIDENT_2026-08-17_WMS_SERVER_DISK_FULL.md](INCIDENT_2026-08-17_WMS_SERVER_DISK_FULL.md)。

最近验证：`2026-08-17`，仅执行只读检查。
