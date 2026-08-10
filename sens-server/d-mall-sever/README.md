# D-Mall Server Operations

`ce-ssr-app`（D-Mall 管理后台）生产服务器的本地连接和日常运维入口。
本目录可由其他项目直接调用，但不保存私钥、密码、Token、数据库凭据或
`.env` 内容。

## 快速使用

```bash
# 交互式登录
/Users/lingang/sens/sens-server/d-mall-sever/connect.sh

# 执行一条只读远程命令
/Users/lingang/sens/sens-server/d-mall-sever/connect.sh 'hostname && uptime'

# 查看服务器、资源、项目和进程状态（只读）
/Users/lingang/sens/sens-server/d-mall-sever/status.sh

# 标准健康检查，正常退出码为 0，异常为 2（只读）
/Users/lingang/sens/sens-server/d-mall-sever/health-check.sh

# 日常巡检：状态 + 健康检查（只读）
/Users/lingang/sens/sens-server/d-mall-sever/daily-check.sh

# 查看最近日志（只读）
/Users/lingang/sens/sens-server/d-mall-sever/logs.sh both 80

# 明确指定 Git commit 后部署（有变更，会二次确认）
/Users/lingang/sens/sens-server/d-mall-sever/deploy.sh <commit-sha>
```

## 文件说明

- `SERVER_INFO.md`：经实际连接核验的服务器、应用、端口、版本和维护边界。
- `NGINX_SSL_RUNBOOK.md`：新增域名、复用通配符证书、安装 Nginx 站点及排查
  错误证书的标准流程。
- `connect.sh`：统一 SSH 参数，支持交互登录或远程命令。
- `status.sh`：采集系统资源、Git 状态、端口、应用进程和 Nginx 状态。
- `health-check.sh`：检查资源阈值、端口、Nginx 和内外 HTTP 入口。
- `daily-check.sh`：一次运行状态采集和标准健康检查。
- `logs.sh`：读取前端或后端日志尾部，不清理日志。
- `deploy.sh`：调用服务端 `deploy.sh`，要求明确目标并在完成后独立验收。
- `ssh_config.example`：可选 SSH 别名示例，不会修改用户 SSH 配置。

## 可配置项

脚本默认值与当前生产服务器一致，也可以在其他项目中通过环境变量覆盖：

```bash
DMALL_SSH_HOST=47.83.1.157
DMALL_SSH_USER=sens
DMALL_SSH_KEY=/Users/lingang/.ssh/id_ed25519_d_mall
DMALL_PROJECT_DIR=/home/sens/ce-ssr-app
```

健康检查阈值可按需覆盖：

```bash
DISK_WARN_PERCENT=90 MEMORY_WARN_PERCENT=8 \
  /Users/lingang/sens/sens-server/d-mall-sever/health-check.sh
```

## 安全边界

- 私钥只保存在 `/Users/lingang/.ssh/id_ed25519_d_mall`，不得复制到本目录或 Git。
- `status.sh`、`health-check.sh`、`daily-check.sh` 和 `logs.sh` 是只读工具。
- `deploy.sh` 会更新服务器代码、安装依赖、重建和重启应用，并 reload Nginx。
- 部署、回滚、配置修改、数据库写入、Cron 修改、日志删除、软件安装、防火墙
  变更均需要明确授权。
- 日志可能含业务数据，读取和分享时应保持最小范围。
- 不采集 `.env`、完整进程命令行、数据库连接串、Token 或证书私钥。
- SSH 主机指纹异常时先核实服务器是否重装，不得直接关闭主机密钥校验。
