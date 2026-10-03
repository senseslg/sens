# WMS DB Overview

## 目标与范围

- 维护 GCP `wms-db` 的访问方式、运行基线、入口路由、服务归属和风险。
- 维护 Bitbucket、Jenkins、XXL-JOB、Jira、YApi、Nexus、数据库及 SQL 审核组件的边界。
- 维护 Jira 需求接入；本机 Python 服务的功能、验证与操作说明集中在 [jira-service](jira-service/README.md)。
- 默认只读巡检；容器重启、升级、数据库操作、配置修改和数据清理需要明确授权。

## 当前状态（2026-10-03）

| 项目 | 已确认状态 |
|---|---|
| GCP | 项目 `cambodian-express`，区域 `asia-southeast1-a`，实例 `wms-db`；无公网 IP，通过 IAP SSH |
| 系统 | CentOS 7；4 vCPU、约 31 GB 内存，无 Swap；已运行约 1040 天 |
| 资源 | 负载约 1.0；内存可用约 12 GB；500 GB XFS 根盘使用约 278 GB（56%），inode 约 2% |
| systemd | 状态 `degraded`；历史记录指向本地/串口 getty 失败，核心容器和入口仍在运行 |
| 公网入口 | `34.117.18.41` 的 GCP `dev-lb`；Nginx 按 Host 转发到本机容器；Jenkins 入口已验证在线 |
| 核心平台 | Jira、Bitbucket、Jenkins、XXL-JOB、YApi、Nexus、MySQL、Redis、Archery、GoInception |

该实例不只是数据库服务器，而是源码、构建、任务调度、问题管理、接口文档、制品和数据服务的共享平台。单机故障会同时影响多个开发与运维流程。

Jira Server 7.12.0 的现有 REST API 已可用于需求管理。本机服务 0.3.0 已实际创建 CE-2629，支持查询、CSV 和关闭/不做预检查；没有部署服务器或取消真实需求。评估与待办见 [服务概览](jira-service/PROJECT_OVERVIEW.md)，不将本机开发进度计入服务器部署状态。

## 当前风险与下一步

- [ ] 建立 Bitbucket、Jenkins、Jira、YApi、XXL-JOB、Nexus 和数据库的数据卷、备份、保留期与恢复验证清单；Jenkins 当前数据卷已定位，备份状态待核实。
- [ ] 明确 Jenkins Job、Bitbucket 仓库与目标生产服务器的发布映射。
- [ ] 核对 GCP 防火墙、VPC 与容器端口的实际访问边界；多个端口监听所有接口。
- [ ] 规划 CentOS 7、旧版本镜像和 `latest` 镜像的替代方案；不要直接在共享生产主机原地升级。
- [ ] 评估 Swap、容量告警和实例长期运行后的维护窗口。
- [ ] 按 [Jira 服务待办](jira-service/PROJECT_OVERVIEW.md) 完成真实工作流转换验证与 CSV 格式对齐；共享部署前另行确定访问、凭据和进程管理方案。

具体端口和服务见 [SERVICE_INVENTORY.md](SERVICE_INVENTORY.md)，入口链路见 [INFRASTRUCTURE_MAP.md](INFRASTRUCTURE_MAP.md)。
