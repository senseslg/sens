# new-ccsl server access

`ce-ssr-app` 生产服务器的本地连接与日常运维入口。本目录不保存私钥、密码、Token、数据库凭据或 `.env` 内容。

## 快速使用

```bash
# 交互式登录
./connect.sh

# 执行一条远程命令
./connect.sh 'hostname && uptime'

# 查看服务器和应用状态（只读）
./status.sh

# 执行标准健康检查（只读）
./health-check.sh

# 查看最近日志（只读）
./logs.sh both 80

# 明确指定 Git ref 后部署（会要求输入 DEPLOY）
./deploy.sh c56e7c69d60c8cadd0f9be1276a77bf56a5e6837
```

macOS 也可以在 Finder 中双击 `connect.command` 打开 SSH 会话。

## 连接信息

| 项目 | 值 |
|---|---|
| SSH | `sens@47.83.1.157` |
| 默认密钥 | `~/.ssh/id_ed25519_d_mall` |
| 项目目录 | `/home/sens/ce-ssr-app` |
| 运维资料 | `/home/sens/md_file` |
| 公网入口 | `https://ce-ssr-app.ceccsl.com` |
| 前端 | Next.js，`127.0.0.1:3001` |
| 后端 | FastAPI/Uvicorn，`127.0.0.1:8001` |

私钥必须继续保存在 `~/.ssh/`，不要复制到本目录、Git 仓库或服务器。

脚本支持以下环境变量覆盖：

```bash
NEW_CCSL_SSH_HOST=47.83.1.157
NEW_CCSL_SSH_USER=sens
NEW_CCSL_SSH_KEY="$HOME/.ssh/id_ed25519_d_mall"
NEW_CCSL_PROJECT_DIR=/home/sens/ce-ssr-app
```

## 脚本说明

- `connect.sh`：统一 SSH 参数，保持长连接，支持交互登录或单条命令。
- `status.sh`：查看系统资源、Git/应用版本、监听端口、进程和 Nginx 状态。
- `health-check.sh`：检查磁盘、可用内存、Nginx、3001/8001 端口及三个 HTTP 入口；健康返回 `0`，异常返回 `2`。
- `logs.sh`：按需读取前端/后端日志尾部，不做清理或修改。
- `deploy.sh`：本地部署入口，必须明确指定 Git ref，部署前二次确认，部署后自动运行健康检查。
- `ssh_config.example`：可选 SSH 别名示例，不会自动修改 `~/.ssh/config`。
- `SERVER_INFO.md`：经实际核验的服务器拓扑、版本、回滚和维护边界。

健康检查默认在根分区使用率达到 85% 或可用内存低于 10% 时告警：

```bash
DISK_WARN_PERCENT=90 MEMORY_WARN_PERCENT=8 ./health-check.sh
```

## 部署与回滚

服务器上的 `/home/sens/ce-ssr-app/deploy.sh` 会记录部署前提交到 `.deploy_rollback_ref`。推荐使用精确提交号：

```bash
./deploy.sh <commit-sha>
```

若部署失败，先查看输出和 `.deploy_rollback_ref`，确认目标后再人工执行回滚，不能在未核对数据迁移或工作区状态时盲目回滚：

```bash
./connect.sh 'cd /home/sens/ce-ssr-app && cat .deploy_rollback_ref'
./deploy.sh <rollback-commit-sha>
```

## 安全边界

- `status.sh`、`health-check.sh`、`logs.sh` 只读；`deploy.sh` 会更新代码、安装依赖、重启应用并 reload Nginx。
- 部署、回滚、配置修改、数据库写入、Cron 修改、日志删除、软件安装和防火墙变更都需要明确授权。
- 日志可能包含业务数据，应缩小读取范围，避免复制到公开文档。
- 不读取或输出 `.env`、数据库密码、Token、证书私钥等敏感内容。
- 服务端 `deploy.sh` 使用 `git reset --hard` 对齐目标提交；服务器专用未跟踪文件应保持未跟踪，部署前仍应确认没有需要保留的受跟踪改动。
