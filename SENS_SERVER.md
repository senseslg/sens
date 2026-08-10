# sens-server 目录说明

`/Users/lingang/sens/sens-server` 是本机集中维护服务器连接资料、运行基线和运维脚本的目录，供 `/Users/lingang/sens` 下的项目及其他本地项目复用。

该目录只保存经过整理的连接元数据、公钥路径/指纹、脱敏服务器信息和审核过的脚本，不保存密码、私钥正文、Token、Cookie、数据库连接串、`.env` 内容或证书私钥。

## 目录结构

| 目录 | 用途 | 默认操作边界 |
|---|---|---|
| `sens-server/cs-online/` | Toucha 自建 Chatwoot 生产服务器；包含登录、快速状态、健康检查、磁盘/日志增长和日检留档脚本 | 只读 |
| `sens-server/mallgogo/` | Mallgogo 生产/UAT 应用服务器连接及健康检查 | 只读 |
| `sens-server/new-ccsl/` | New CCSL Java 生产/UAT 服务器连接、基线和健康检查 | 只读 |
| `sens-server/d-mall-sever/` | D-Mall / `ce-ssr-app` 生产服务器运维入口 | 状态/健康/日志脚本只读；`deploy.sh` 会修改生产环境 |
| `sens-server/new-ccsl-mixed-backup-20260731-01/` | 历史混合资料备份，同时保留 CCSL 与 CE SSR App 旧入口 | 仅用于追溯，不作为日常默认入口 |

各服务器目录中的 `README.md` 和 `SERVER_INFO.md` 是具体使用方式、服务器事实及风险边界的来源。

## 常用入口

### Chatwoot / cs-online

```bash
cd /Users/lingang/sens/sens-server/cs-online
./connect.sh
./server-status.sh
./health-check.sh
./disk-log-check.sh
./daily-check.sh
```

### Mallgogo

```bash
cd /Users/lingang/sens/sens-server/mallgogo
./connect.sh
./server-status.sh
./health-check.sh
```

### New CCSL

```bash
cd /Users/lingang/sens/sens-server/new-ccsl
./bin/connect.sh
./bin/server-status.sh
./bin/health-check.sh all
```

### D-Mall / ce-ssr-app

```bash
cd /Users/lingang/sens/sens-server/d-mall-sever
./connect.sh
./status.sh
./health-check.sh
./daily-check.sh
```

`d-mall-sever/deploy.sh` 是生产变更脚本，只有在目标 commit、备份、回滚和验收方式均明确且获得授权后才能执行。

## 安全与维护规则

- 所有服务器按生产环境处理，默认从只读检查开始。
- 重启、部署、回滚、配置修改、日志清理/轮转、数据库写入、Cron 修改、软件安装、防火墙或 SSH 策略变更均需明确授权。
- 私钥必须留在 `~/.ssh/`，不得复制进 `sens-server` 或 Git。
- 不输出完整 Java/Ruby 进程参数、原始业务日志或 secret-bearing 配置文件。
- 脚本发现异常时只报告，不应自动修复生产环境。
- 每次已验证的维护后，更新对应目录的 `SERVER_INFO.md` 和维护历史。
- 历史备份目录不应直接用于日常部署或服务器操作；先确认当前正式目录。

## 迁移记录

- **2026-07-31** — 将原 `/Users/lingang/sens-server` 整体移动到 `/Users/lingang/sens/sens-server`，并同步更新目录内及相关项目文档中的绝对路径。
