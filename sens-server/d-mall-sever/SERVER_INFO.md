# D-Mall Server Information

以下信息于 2026-08-01 通过 SSH 实际核验。动态状态请以本目录脚本的实时输出
为准。

## SSH 连接

| 项目 | 当前值 |
|---|---|
| SSH 主机 | `47.83.1.157` |
| SSH 端口 | `22` |
| 登录用户 | `sens` |
| 本机私钥 | `/Users/lingang/.ssh/id_ed25519_d_mall`（仅引用，不复制） |
| 认证方式 | ED25519 公钥 |
| 远端主机名 | `iZj6chvghrh4wyxdsco1k3Z` |

标准登录：

```bash
ssh -i /Users/lingang/.ssh/id_ed25519_d_mall sens@47.83.1.157
```

推荐通过统一入口登录：

```bash
/Users/lingang/sens/sens-server/d-mall-sever/connect.sh
```

## 服务器基线

| 项目 | 已核验信息 |
|---|---|
| 操作系统 | Ubuntu 24.04 |
| 内核 | Linux 6.8.0-106-generic |
| 根分区 | 40 GiB；核验时使用 33% |
| 内存 | 3.4 GiB；核验时可用约 2.5 GiB |
| Swap | 未配置 |
| Node.js | v24.18.0 |
| Python | 3.12.3（项目 `venv`） |

服务器未配置 Swap。若出现持续内存压力、构建被 OOM kill 或异常重启，应先保存
日志和资源证据，再评估是否增加 Swap 或调整构建/进程配置。

## 应用拓扑

| 项目 | 当前值 |
|---|---|
| 项目目录 | `/home/sens/ce-ssr-app` |
| 运维资料 | `/home/sens/md_file` |
| Git 分支 | `main` |
| 核验版本 | v1.70.7 |
| 核验提交 | `c56e7c69d60c8cadd0f9be1276a77bf56a5e6837` |
| 前端 | Next.js 15.5.22，`127.0.0.1:3001` |
| 后端 | FastAPI/Uvicorn，`127.0.0.1:8001` |
| 公网入口 | `https://ce-ssr-app.ceccsl.com/` |
| 反向代理 | Nginx |

`3001` 和 `8001` 是本项目的生产监听端口。它们仅监听回环地址，由 Nginx
提供公网 HTTPS 入口。

同一服务器还运行 CCSL 管理后台原型：

| 项目 | 当前值 |
|---|---|
| 项目目录 | `/home/sens/ccsl-prototype` |
| Git 分支 | `main` |
| 核验版本 | v0.1.17 |
| 进程管理 | PM2，应用名 `ccsl-prototype` |
| 应用监听 | `127.0.0.1:3002` |
| 公网入口 | `https://ccsl-prototype.ceccsl.com/` |
| Nginx 站点 | `/etc/nginx/sites-available/ccsl-prototype.ceccsl.com` |
| 一键更新 | `/home/sens/deploy-ccsl-prototype.sh` |

该站点复用 `/home/sens/ssl/ceccsl.com/` 下覆盖 `*.ceccsl.com` 的 ECC/RSA
证书。2026-08-01 已验证 HTTP 301、HTTPS 登录页、健康接口和证书主机名均正常。
新增域名与 SSL 的标准步骤及故障排查见 `NGINX_SSL_RUNBOOK.md`。

## 部署与回滚

服务端部署脚本：

```bash
cd /home/sens/ce-ssr-app
bash ./deploy.sh <commit-sha>
```

本地安全入口：

```bash
/Users/lingang/sens/sens-server/d-mall-sever/deploy.sh <commit-sha>
```

服务端脚本会在 `.deploy_rollback_ref` 保存部署前提交。2026-07-31 核验时的
回滚记录为：

```text
e81a77013380f61a5694d4e5ad7f350908984aed
```

该值会随部署变化，回滚前必须重新读取，不要依赖本文中的历史值：

```bash
/Users/lingang/sens/sens-server/d-mall-sever/connect.sh \
  'cd /home/sens/ce-ssr-app && cat .deploy_rollback_ref'
```

回滚仍属于一次部署。应先确认失败范围、数据库兼容性、服务器工作区状态和目标
提交，再通过部署脚本显式执行，不能盲目自动回滚。

## 常用操作

```bash
# 日常只读巡检
./daily-check.sh

# 单独健康检查
./health-check.sh

# 查看项目和系统状态
./status.sh

# 查看后端最后 120 行
./logs.sh backend 120

# 查看前后端最后 80 行
./logs.sh both 80
```

健康检查覆盖：

- 根分区使用率和可用内存比例；
- 项目 Git 提交与回滚记录；
- `3001`、`8001` 监听状态；
- Nginx 进程和配置检查；
- 前端本机 HTTP、后端文档、本项目公网 HTTPS。

技术健康检查通过不等于登录、数据查询、定时任务或第三方接口等业务验收通过。
