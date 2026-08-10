# SENS Admin Portal

本地管理后台。

## 组成

- `backend/`：FastAPI + PyMySQL。
- `backend/static/`：React 页面和样式。
- `backend/templates/`：入口 HTML。

## 本地运行

```bash
uvicorn admin_portal.backend.main:app --reload --host 127.0.0.1 --port 8008
```

## 推荐脚本

先在已被 Git 忽略的 `.local-portal/env` 中设置本机凭据，并限制文件权限：

```bash
mkdir -p .local-portal
chmod 700 .local-portal
$EDITOR .local-portal/env
chmod 600 .local-portal/env
```

文件至少包含：

```bash
SENS_PORTAL_MYSQL_ROOT_PASSWORD='<local-only-secret>'
SENS_PORTAL_ADMIN_PASSWORD='<local-only-secret>'
SENS_PORTAL_SESSION_SECRET='<random-session-secret>'
```

然后运行：

```bash
./admin_portal/scripts/mysql-local.sh init
./admin_portal/scripts/portal-local.sh start
./admin_portal/scripts/portal-smoke.sh
./admin_portal/scripts/refresh-device-status.py
```

- `mysql-local.sh` 会把本地 MySQL 固定到 socket-only 模式，并初始化 `sens` 库和 `sens` 管理员。
- 当前默认 MySQL 版本是 8.4，socket 路径是 `/Users/lingang/sens/.local-mysql84/run/mysql.sock`。
- 旧版 MySQL 5.6 仍保留为独立实例，供迁移和回退使用。
- `portal-local.sh` 用 `127.0.0.1:8008` 启动后端，并通过 `/api/health` 自检。
- 本地重启使用 `./admin_portal/scripts/mysql-local.sh restart` 和 `./admin_portal/scripts/portal-local.sh restart`。
- MySQL 8.4 仍可由 launchd 托管；portal 进程则改为普通后台进程启动，避免重启时卡在 submit 等待。
- `portal-smoke.sh` 会做健康接口、登录、用户创建、密码重置、停用、删除和 dashboard 的完整验证。
- `refresh-device-status.py` 会重写根目录 `LOCAL_DEVICE_STATUS.md`。

## 数据库

- MySQL：本机 socket `/Users/lingang/sens/.local-mysql84/run/mysql.sock`
- 数据库：`sens`
- root 密码：由 `SENS_PORTAL_MYSQL_ROOT_PASSWORD` 提供，不写入仓库

## 默认登录

- 账号：`sens`
- 密码：由 `SENS_PORTAL_ADMIN_PASSWORD` 提供，不写入仓库

## 接口

- `/api/health`：无需登录的本机健康检查。
- `/api/login`：登录并创建会话。
- `/api/dashboard`：登录后查看本机与 `sens-server` 文档快照。
- `/api/users`：登录后查看和创建后台账号。
- `/api/users/{id}`：更新或删除后台账号。
- `/api/users/{id}/password`：重置后台账号密码。
