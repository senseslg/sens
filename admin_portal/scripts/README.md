# Admin Portal Scripts

这些脚本把本次搭建中最容易重复踩坑的步骤固定下来。

## 脚本

- `mysql-local.sh`：启动、停止、重启本地 socket-only MySQL 8.4，执行 `sens` 库初始化和管理员账号种子。
- `mysql56-local.sh`：保留的本地 MySQL 5.6 管理脚本，用于迁移、排查和回退。
- `portal-local.sh`：启动、停止、重启、检查本地 FastAPI 后台。
- `portal-smoke.sh`：一次性执行 MySQL 初始化、后台启动、健康检查、登录、账号 CRUD 和 dashboard 验证。
- `refresh-device-status.py`：根据当前采集结果重写根目录 `LOCAL_DEVICE_STATUS.md`。

## 常用流程

```bash
./admin_portal/scripts/mysql-local.sh init
./admin_portal/scripts/portal-local.sh start
./admin_portal/scripts/portal-smoke.sh
./admin_portal/scripts/refresh-device-status.py
```

日常重启：

```bash
./admin_portal/scripts/mysql-local.sh restart
./admin_portal/scripts/portal-local.sh restart
```

## 约定

- MySQL root 密码：必须通过 `SENS_PORTAL_MYSQL_ROOT_PASSWORD` 或 `.local-portal/env` 提供
- 默认后台账号：`sens`
- 后台密码：必须通过 `SENS_PORTAL_ADMIN_PASSWORD` 或 `.local-portal/env` 提供
- 会话密钥：必须通过 `SENS_PORTAL_SESSION_SECRET` 或 `.local-portal/env` 提供
- 默认后台端口：`127.0.0.1:8008`
- 默认 MySQL socket：`/Users/lingang/sens/.local-mysql84/run/mysql.sock`
- 旧版 MySQL 5.6 socket：`/Users/lingang/sens/.local-mysql/run/mysql.sock`
- macOS 下 MySQL 8.4 可继续通过 launchd 托管；portal 使用普通后台进程启动和健康探测。
- MySQL 8.4 日志：`.local-mysql84/log/mysqld.log`
- 旧版 MySQL 5.6 日志：`.local-mysql/log/mysqld.log`
- 后台日志：`.local-portal/log/uvicorn.log`
