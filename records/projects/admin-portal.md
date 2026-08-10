# Admin Portal

## 当前状态

- 已在本仓库内完成本地管理后台初版，并在本机验证可运行。
- 后端：`FastAPI` + `PyMySQL`。
- 前端：浏览器端 `React`，由本地 HTML 模板挂载。
- 数据库：本机 MySQL 8.4，库名 `sens`；root 密码只保存在已忽略的本地环境文件中。
- 默认登录账号：`sens`；密码通过本地环境变量提供，不写入仓库。
- 已接入 `sens.admin_users` 用户管理表，支持登录、创建账号、修改显示名称、启停账号、重置密码和删除账号。
- 设备记录：根目录 `LOCAL_DEVICE_STATUS.md` 已建立，可由脚本刷新。
- 当前首页先展示本机信息和健康状况，再展示 `sens-server` 下各子目录对应的服务端设备信息、基础健康检查、健康摘要和文档摘录。

## 已解决问题

- 本机 MySQL 默认 socket `/tmp/mysql.sock` 不可直接稳定连接。
- 旧版 MySQL 5.6 和新装 MySQL 8.4 可以在本机共存，但必须分开数据目录、socket 和启动脚本。
- 后台初次启动时，数据库初始化、用户种子和服务加载顺序需要固定，否则会出现登录和 dashboard 失败。
- 用户管理必须围绕 MySQL 的 `sens.admin_users` 持久化表实现，不能只在前端做临时态，且删除/停用需要保护当前登录账号和最后一个可用账号。
- portal 的本地重启不再依赖 `launchctl submit`，改为 `nohup` 后台进程 + 健康检查，避免重启过程卡住。

## 已固化脚本

- `admin_portal/scripts/mysql-local.sh`
- `admin_portal/scripts/mysql56-local.sh`
- `admin_portal/scripts/portal-local.sh`
- `admin_portal/scripts/portal-smoke.sh`
- `admin_portal/scripts/refresh-device-status.py`
- `admin_portal/scripts/portal-smoke.sh` 现已覆盖账号 CRUD 闭环。

## 下一步

- 如需长期使用，把这套脚本接入本机启动习惯。
- 如需实时巡检 `sens-server` 目录，可再单独打开 `SENS_PORTAL_ENABLE_REMOTE_CHECKS=1`。
