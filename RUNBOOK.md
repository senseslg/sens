# RUNBOOK

当前仓库在本机上已经验证过的操作记录。这里保存环境相关经验，不保存通用工作背景。

## Device Snapshot

- Snapshot date: `2026-07-22`
- Device: MacBook Pro (`MacBookPro18,3`)
- Chip: Apple M1 Pro
- CPU: 8 cores（6 performance + 2 efficiency）
- GPU: 14 cores，Metal supported
- Memory: 16 GB
- OS: macOS `26.2`，build `25C56`
- Kernel / Architecture: Darwin `25.2.0` / `arm64`
- Current session shell: `/bin/bash`
- Repo root: `/Users/lingang/sens`
- Git branch: `main`
- Remote: `git@github.com:senseslg/sens.git`

为避免长期记录暴露设备身份，本文件不保存主机名、序列号、Hardware UUID、Provisioning UDID、MAC 地址或 IP。

## Storage Snapshot

采集日期：`2026-07-22`

| Volume | Total | Used | Available | Usage |
|---|---:|---:|---:|---:|
| macOS Data volume | 约 494 GB | 约 395 GB | 约 60 GB | 87% |

APFS 的共享空间、系统卷和快照会使不同命令显示的容量略有差异。当前可用空间仍可工作，但已进入需要定期清理和监控的区间；大型 Flutter、Node、Docker、Xcode 或构建缓存可能继续快速占用磁盘。

## Development Toolchain Snapshot

采集日期：`2026-07-22`

| 工具 | 版本 / 状态 | 备注 |
|---|---|---|
| Git | `2.36.0` | `/usr/local/bin/git` |
| Node.js | `24.2.0` | 由 NVM 管理 |
| npm | `11.3.0` | 随当前 Node 环境提供 |
| Python | `3.11.1` | Framework 安装路径 |
| OpenJDK | `24.0.1` | 64-bit Server VM |
| Flutter | `3.41.7` stable | 安装于 Homebrew Cask 路径 |
| Dart | `3.11.5` | 随 Flutter SDK 提供 |
| Flutter DevTools | `2.54.2` | 随 Flutter SDK 提供 |
| CocoaPods | `1.16.2` | `/usr/local/bin/pod` |
| Google Cloud SDK | `460.0.0` | 包含 `bq 2.0.101`、`gsutil 5.27` |
| Docker CLI | `20.10.23` | 仅确认 CLI；Daemon 状态未检查 |
| Homebrew | `5.1.8` | `/usr/local/bin/brew` |
| Apple Command Line Tools | `26.4.1` | 已安装 |
| Xcode | 未安装完整应用 | `xcodebuild` 当前只指向 Command Line Tools |
| Android Studio | 已安装 | 版本待需要时确认 |
| Visual Studio Code | 已安装 | CLI `code` 当前不在 PATH |
| Android Debug Bridge | 未在 PATH | `adb` 命令当前不可用 |

Flutter 与 Dart 的版本来自已安装 SDK 的 `flutter.version.json`。在当前受限执行环境直接运行版本命令时，Flutter 尝试更新 SDK cache 下的 `engine.stamp` 并被权限阻止；这不等于本机正常终端中的 Flutter 不可用。

## Apple Silicon Homebrew

迁移日期：`2026-09-30`

- 默认前缀：`/opt/homebrew`；登录 shell 通过 `~/.bash_profile` 加载 `brew shellenv`。
- 原生环境已迁移原有 15 个直接 formula 和 Flutter cask；D2、Go、Git、MySQL 等均验证为 `arm64`。
- 原 Intel Homebrew 暂留在 `/usr/local` 作为短期回退，不再位于默认 PATH 前端。
- `brew doctor` 仅提示 Command Line Tools 可更新至 `26.6`，以及 `/usr/local/include/node/` 存在非 Homebrew 管理的旧头文件。
- 本仓库的 MySQL 8.4 默认路径已切换为 `/opt/homebrew/opt/mysql@8.4`；`.local-mysql84` 数据目录保持原位。

## 常用检查

```bash
git status --short --branch
git branch --show-current
git remote -v
```

## 更新记录后的检查

```bash
git diff --check
git status --short
git diff --stat
```

## CCSL 服务器重复检查

服务器地址在执行时传入，不写入仓库：

```bash
python3 new-ccsl-server/scripts/server_baseline.py --ssh-host <user>@<host>
python3 new-ccsl-server/scripts/verify_deployment.py --ssh-host <user>@<host>
```

需要保存或继续处理结构化结果时添加 `--json`。脚本说明、默认检查目标、退出码和安全边界见 [`new-ccsl-server/scripts/README.md`](new-ccsl-server/scripts/README.md)。

## Admin Portal 本地启动与修复

本仓库新增的 `admin_portal` 现在默认接入本地 MySQL 8.4，并保留旧版 5.6 作为独立实例以便迁移和回退。已经实际遇到并解决的问题包括：

- 默认的 `/tmp/mysql.sock` 不一定可用，项目统一使用 `.local-mysql84/run/mysql.sock`，旧版 5.6 仍保留为 `.local-mysql/run/mysql.sock`。
- MySQL 先启动、再建 `sens` 库和 `admin_users`、最后启动 FastAPI 后台，否则会出现登录或 dashboard 失败。
- 旧 `mysqld` 可能仍锁住 `ibdata1`，但对应 socket 文件已经丢失。此时进程看似存在，客户端仍会报 socket 不存在；必须先停止该项目数据目录对应的旧进程，再重启，不能删除数据文件。
- macOS 下 portal 进程改为普通后台进程启动，重启脚本依赖 `nohup` + 健康探测，不再依赖 `launchctl submit`。
- MySQL 5.6 中 `databases` 不适合作为未转义的查询别名；状态脚本统一使用 `database_count`。
- MySQL 重启不能依赖 `launchctl remove` 后立即重新提交。脚本对已托管实例使用 `launchctl kickstart -k`，避免 InnoDB 关闭阶段的 socket 竞争。

推荐的一次通过流程：

先在 Git 忽略的 `.local-portal/env` 中设置 `SENS_PORTAL_MYSQL_ROOT_PASSWORD`、`SENS_PORTAL_ADMIN_PASSWORD` 和 `SENS_PORTAL_SESSION_SECRET`，并将文件权限设为 `600`。

```bash
./admin_portal/scripts/mysql-local.sh init
./admin_portal/scripts/portal-local.sh start
./admin_portal/scripts/portal-smoke.sh
./admin_portal/scripts/refresh-device-status.py
```

日常状态和重启：

```bash
./admin_portal/scripts/mysql-local.sh status
./admin_portal/scripts/mysql-local.sh restart
./admin_portal/scripts/portal-local.sh status
./admin_portal/scripts/portal-local.sh restart
```

对应脚本职责：

- `mysql-local.sh`：启动、停止或重启本地 MySQL，初始化 `sens` 库、重设 root 密码、种子 `sens` 管理员。
- `portal-local.sh`：启动、停止或重启 `uvicorn`，并调用 `/api/health` 验证后台是否就绪。
- `portal-smoke.sh`：一次性验证健康接口、登录、账号 CRUD 和 dashboard。
- `refresh-device-status.py`：把当前本机快照写回根目录 `LOCAL_DEVICE_STATUS.md`。

## Admin Portal 用户管理

- 后台账号表是 `sens.admin_users`，包含 `username`、`display_name`、`password_salt`、`password_hash`、`is_active`、`last_login_at`、`created_at` 和 `updated_at`。
- 登录账号默认是 `sens`，密码由本机环境文件提供，不写入仓库。
- 用户管理接口支持创建、修改显示名称与启停状态、重置密码和删除账号。
- 删除和停用当前登录账号会被阻止；删除最后一个可用账号也会被阻止。
- `sens-server` 的服务卡片现在会从 `SERVER_INFO.md` 结构化提取设备信息，优先展示 SSH、主机名、系统、内核、架构、CPU、内存和公开入口。
- 当前项目已经在本机 MySQL 8.4 上验证通过，后台登录后首页优先展示本机状态，再展示 `sens-server` 下各服务端目录的健康信息。
- 后台健康信息在登录、手动刷新和页面重新加载时更新；默认来源是 `sens-server` 文档快照，开启 `SENS_PORTAL_ENABLE_REMOTE_CHECKS=1` 后会额外运行各目录脚本。
- 如果用户管理相关请求失败，优先检查 `/api/users` 的 401/409/400 返回值，再看 `.local-portal/log/uvicorn.log`。

如果 `mysql-local.sh init` 失败，优先查看 `.local-mysql/log/mysqld.log`，不要先改后端代码。旧版 MySQL 常见故障是 socket 路径、端口占用和数据目录权限，而不是应用逻辑。

日志中出现 `Unable to lock ./ibdata1, error: 35` 时，先确认是否存在使用项目数据目录的旧进程：

```bash
ps aux | rg '[m]ysqld.*\.local-mysql'
lsof .local-mysql/data/ibdata1
lsof -nP -U | rg '.local-mysql/run/mysql.sock'
```

如果 `lsof` 显示进程持有 socket，但 `ls .local-mysql/run/mysql.sock` 不存在，这是已删除 socket 的残留实例。优先执行脚本重启；只有脚本无法识别旧的非托管进程时，才根据以上命令确认准确 PID 后正常 `kill <PID>`，不要使用 `kill -9`，也不要删除 `ibdata1`。

## 提交与推送

先查看变更范围，只暂存本次相关文件：

```bash
git status --short
git add <相关文件>
git diff --cached --stat
git commit -m "简短且具体的说明"
git push origin main
```

## 恢复工作上下文

1. 阅读 `PROJECT_READ_FIRST.md`。
2. 查看最近的 `PROJECT_ITERATION_LOG.md` 条目。
3. 打开本次工作对应的 `records/projects/` 文件。
4. 用 `git status --short --branch` 确认是否存在未完成修改。

## Notes

- 只记录在这台设备和当前仓库中实际验证过的命令。
- 环境变化后先更新 Device Snapshot，再更新相关命令。
- 如果 Git 写操作出现 `.git/index.lock` 或权限错误，确认没有其他 Git 进程后，再按当前执行环境的授权机制重试。
- 不在此文件记录密码、Token、私钥或生产连接凭证。
- 磁盘、工具版本和运行时状态是时间快照；环境升级后需要重新采集，不能永久当作当前事实。
