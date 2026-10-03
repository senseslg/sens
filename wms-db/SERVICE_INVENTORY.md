# WMS DB Service Inventory

## 公网业务入口

| 域名 | 业务 | 本机上游 | 当前验证 |
|---|---|---:|---|
| `issue.cambodianexpress.com` | Jira 问题管理 | `127.0.0.1:8080` | 2026-10-03 公网 HTTP 200 |
| `code.cambodianexpress.com` | Bitbucket 源码管理 | `127.0.0.1:7990` | 2026-10-03 公网 HTTP 302，符合登录跳转 |
| `yapi.cambodianexpress.com` | YApi 接口文档 | `127.0.0.1:40001` | 2026-10-03 公网 HTTP 200 |
| `jenkins.cambodianexpress.com` | Jenkins 构建与发布 | `127.0.0.1:8081` | 2026-10-03 公网及本机 HTTP 403；未授权访问被拒绝，服务在线 |
| `job.cambodianexpress.com` | XXL-JOB 管理后台 | `127.0.0.1:8087` | 路由已确认；本轮未登录业务页面 |

上述域名经 GCP `dev-lb` 到 `wms-db:80`，再由 Nginx 按 Host 转发。公网 IP 是负载均衡入口，不是实例公网 IP。

## Docker 服务快照（2026-10-03）

| 容器 | 镜像 | 宿主机端口 | 作用 |
|---|---|---:|---|
| `jira` | `jira/jira` | `8080` | 问题与项目管理；REST serverInfo 实测 Server 7.12.0 |
| `bitbucket` | `bitbucket/bitbucket` | `7990` / `7999` | Web/HTTP Git 与 Git SSH |
| `jenkins` | `jenkins/jenkins:latest` | `8081` / `50000` | 构建与发布；响应头显示 Jenkins 2.503、Jetty 12.0.18，容器已运行约两年 |
| `xxl-job-admin` | `xuxueli/xxl-job-admin:2.3.1` | `8087` | 任务调度管理后台 |
| `nexus` | `nexus/nexus:latest` | `8082` | 制品仓库 |
| `yapi-web` | `jayfong/yapi:latest` | `40001` | API 文档平台 |
| `yapi-mongo` | `mongo:latest` | 容器网络 | YApi 数据库 |
| `mysql` | `mysql:5.7` | `3307` | 容器 MySQL |
| `redis` | `redis:5` | 容器网络 | 缓存 |
| `archery` | `hhyo/archery:v1.8.5` | `9123` | SQL 审核平台 |
| `goinception` | `hanchuanchuan/goinception` | `4000` | SQL 审核执行组件 |

宿主机还运行 Nginx、MySQL `3306`、PostgreSQL、MongoDB、Google Ops Agent 和 Postfix。未读取容器环境变量、数据库内容、凭据或业务数据。

## 数据与构建位置

- Bitbucket 数据卷：宿主机 `/home/daniel/containers/bitbucket/bitbucket` → 容器 `/var/atlassian/bitbucket`。
- Jenkins 数据卷：宿主机 `/home/daniel/containers/jenkins/jenkins` → 容器 `/var/jenkins_home`。
- 已知 Jenkins 任务包括 `APP`、`AppTranslation`、`ccsl`、`mall`、`otwms`、`restart-tms`、`TMS`、`toucha`；具体配置和发布目标需逐项核实。
- 本轮未登录 Jenkins、读取 Job 配置或查看凭据；HTTP 403 只证明未授权请求被拒绝和应用有响应，不代表所有构建任务健康。

## 本机接入工具（不在服务器容器清单中）

[jira-service 0.3.0](jira-service/README.md) 位于用户 Mac 的 `/Users/lingang/sens/wms-db/jira-service`，仅监听 `127.0.0.1:8765`，通过 HTTPS 调用 Jira。当前为终端进程，未部署 GCP、未开放服务器 8765 端口；能力与验证边界见其项目概览。
