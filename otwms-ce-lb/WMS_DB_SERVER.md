# WMS DB Server

> 本文件保留 `2026-08-17` 历史基线。`2026-10-03` 起，当前状态与运维方法由独立子项目 [`wms-db/`](../wms-db/) 维护。

## 当前结论

`wms-db` 不只是数据库服务器，而是 CE/WMS 的共享工具与数据平台：它同时承载 GCP `dev-lb` 默认后端、Nginx、XXL-JOB、Bitbucket、Jenkins、Jira、Nexus、YApi、数据库和监控。源码、构建、任务调度与多项基础服务集中在单机，存在较大的故障影响面。

## 2026-08-17 只读基线

| 项目 | 状态 |
|---|---|
| GCP | `cambodian-express` / `asia-southeast1-a` / `wms-db` |
| SSH | 用户 `lingang`；无外部 IP，通过 IAP 登录 |
| OS | CentOS Linux 7，kernel `3.10.0-1160.102.1.el7.x86_64` |
| 资源 | 4 vCPU、约 31 GB 内存、无 Swap |
| 磁盘 | 500 GB XFS，已用约 283 GB（57%） |
| 运行时间 | 约 993 天 |
| 系统状态 | `degraded`；失败项为本地/串口 getty，核心业务服务仍在运行 |

## 入口与核心服务

- GCP `dev-backend` 的唯一 NEG 端点是 `wms-db:80`，检查时状态为 `HEALTHY`。
- Nginx 根据 Host 转发到本机容器：`job` → `8087`、`code` → `7990`、Jenkins → `8081`、Jira → `8080`、Nexus → `8082`、YApi → `40001`。
- `job.cambodianexpress.com` 的完整链路见 [INFRASTRUCTURE_MAP.md](INFRASTRUCTURE_MAP.md)。

## Docker 服务快照

| 容器 | 镜像 | 宿主机入口 | 作用 |
|---|---|---:|---|
| `xxl-job-admin` | `xuxueli/xxl-job-admin:2.3.1` | `8087` | 任务调度管理后台 |
| `bitbucket` | `bitbucket/bitbucket` | `7990` / `7999` | 源码仓库与 Git SSH |
| `jenkins` | `jenkins/jenkins:latest` | `8081` / `50000` | 构建与发布 |
| `jira` | `jira/jira` | `8080` | 项目/问题管理 |
| `nexus` | `nexus/nexus:latest` | `8082` | 制品仓库 |
| `mysql` | `mysql:5.7` | `3307` | 容器 MySQL |
| `redis` | `redis:5` | 容器网络 | 缓存 |
| `archery` | `hhyo/archery:v1.8.5` | `9123` | SQL 审核平台 |
| `goinception` | `hanchuanchuan/goinception` | `4000` | SQL 审核执行组件 |
| `yapi-web` / `yapi-mongo` | YApi / Mongo | `40001` / 容器网络 | API 文档平台 |

宿主机还运行 MySQL `3306`、PostgreSQL、MongoDB、Google Ops Agent 和 Postfix。未读取数据库内容、容器环境变量或业务配置。

## 源码与构建位置

- Bitbucket 数据：`/home/daniel/containers/bitbucket/bitbucket` → `/var/atlassian/bitbucket`。
- Jenkins 数据：`/home/daniel/containers/jenkins/jenkins` → `/var/jenkins_home`。
- Jenkins 任务名称包括 `APP`、`AppTranslation`、`ccsl`、`mall`、`otwms`、`restart-tms`、`TMS`、`toucha`。
- `code.cambodianexpress.com` 本机入口返回 HTTP 302，符合转到 Bitbucket 登录流程的表现。
- 未登录 Bitbucket 或读取 Jenkins Job 配置，因此没有确认某个源码仓库与具体部署目标的唯一映射。

## 风险与下一步

- 多个源码、构建、调度、制品和数据服务集中在一台已长期运行的 CentOS 7 主机，单点影响范围大。
- 多个容器已连续运行约两年，部分镜像使用 `latest` 或旧版本标签；升级前需先备份数据卷并验证兼容性。
- 多个服务监听 `0.0.0.0`；实例没有外部 IP，但仍需核对 GCP 防火墙、IAP 和 VPC 内部访问边界。
- 无 Swap；当前内存余量充足，但需要按 JVM、数据库和容器总量建立监控。
- [ ] 建立 Bitbucket、Jenkins、XXL-JOB 和数据库的备份/恢复清单。
- [ ] 明确 `otwms` / `TMS` Jenkins Job、Bitbucket 仓库和目标服务器的发布映射。
- [ ] 规划 CentOS 7 与旧容器版本的迁移，不直接在共享生产宿主机原地升级。

最近验证：`2026-08-17`，仅执行只读检查。
