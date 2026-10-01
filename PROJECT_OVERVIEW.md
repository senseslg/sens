# sens Overview

`sens` 是个人工作管理与日常协作仓库。它不是聊天备份，而是一套可持续维护的工作记忆：保留稳定背景、重要变化、项目状态、会议结论、决定依据和下一步行动。

## 当前版本

- `v0.17.6`
- 建立日期：`2026-07-15`
- 版本规则：
  - `MAJOR`：记录体系、目录结构或长期协作方式发生不兼容调整。
  - `MINOR`：新增一类工作能力、重要目录或可复用流程。
  - `PATCH`：修正、补充、小范围规则或文档调整。

## 主要目标

- 让新的对话能快速恢复工作上下文，减少重复说明。
- 为每个持续项目保留目标、现状、决定、风险和下一步。
- 把会议和日常沟通中的行动项沉淀为可追踪记录。
- 把反复出现的工作方式提炼为可复用流程。
- 将已经验证且会重复运行的操作沉淀为可直接执行的 Python 脚本，减少临时命令、遗漏和误判。
- 让仓库内容保持简洁、可信、可检索，而不是无限堆积材料。

## 信息分层

| 内容 | 存放位置 | 维护方式 |
|---|---|---|
| 稳定目标、范围、长期规则 | `PROJECT_OVERVIEW.md` | 背景真正变化时更新 |
| 最近的重要变化 | `PROJECT_ITERATION_LOG.md` | 新记录放在顶部，一次一行 |
| 单个持续项目 | `records/projects/<name>.md` | 工作推进或状态变化时更新 |
| 每日工作摘要 | `records/daily/YYYY-MM-DD.md` | 仅在需要跨天延续时创建 |
| 会议结论 | `records/meetings/YYYY-MM-DD-<topic>.md` | 会后记录决定和行动项 |
| 长期方法和规则 | `reference/*.md` | 方法成熟或反复使用时更新 |
| 可重复执行流程 | `SKILL.md` 与对应 `reference/` | 出现稳定重复流程时登记 |
| 项目自动化工具 | `<project>/scripts/*.py` | 重复检查稳定后脚本化，默认只读、脱敏和参数化 |
| 本机命令与环境经验 | `RUNBOOK.md` | 命令实际验证后更新 |

## 当前工作范围

当前仅确认以下范围：

- 管理个人工作内容。
- 支持日常工作协同和长期沟通。
- 逐步记录真实项目、任务、会议、决定和工作方法。

尚未提供完整项目清单、优先级或固定汇报节奏，因此不预设未确认内容；收到真实信息后再补充。

## 当前子项目

### google-cloud

- 路径：[`google-cloud/`](google-cloud/)
- 范围：Google Cloud 项目级资源索引、控制台检查、访问/费用/变更规则。
- 当前状态：已核实 `cambodian-express` 项目与 Compute Engine 基础资源；`2026-09-28` 只读审查发现共享 Cloud SQL `tms-db` 磁盘约 94.7% 已用，优先治理接口日志。详见[容量审查](google-cloud/TMS_DB_CAPACITY_REVIEW_2026-09-28.md)。

### google-otwms

- 路径：[`google-otwms/`](google-otwms/)
- 范围：OTWMS 在 Google Cloud 上的实例访问、磁盘与日志巡检、事故记录和自动化工具规划。
- 当前状态：已根据 `2026-07-15` 的运维摘要和一条公开共享对话建立首版文档；来源状态均按时间快照管理，不视为实时状态。

### otwms-ce-lb

- 路径：[`otwms-ce-lb/`](otwms-ce-lb/)
- 范围：GCP `ce-lb`、`dev-lb`、`wms-db` 和 `wms-server` 的入口、源码/构建平台、应用部署与风险管理。
- 当前状态：官网证书、Cron PATH 与 `cp` 已恢复；`2026-09-30` 官网超时通过保留隔离日志积压、补齐获批的采集写入权限及日志资源限额恢复，云端日志/指标验收通过。其他旧证书、WMS 历史大文件及低内存风险仍待治理。详见 [日志事故](otwms-ce-lb/INCIDENT_2026-09-30_LOGGING_PRESSURE.md)。

### otwms-wms-server

- 路径：[`otwms-wms-server/`](otwms-wms-server/)
- 范围：GCP `wms-server` 的访问、运行基线、CEWMS 与 `cp` 后端服务边界和故障恢复。
- 当前状态：`2026-09-18` 启动盘已扩至 600 GB，XFS、SSH、CEWMS 与公网 `cp` 入口均恢复；约 101 GB 可用。主要剩余风险是 `/home/daniel` 历史大文件及空间告警，详见 [事故记录](otwms-wms-server/INCIDENT_2026-09-17_UNRESPONSIVE.md)。

### otwms-server

- 路径：[`otwms-server/`](otwms-server/)
- 范围：OTWMS Java 后端的 Bitbucket 源码、Jenkins 构建、生产 `BladeX.jar` 部署、XXL-JOB 执行链路和数据库查询故障定位。
- 当前状态：`2026-09-21` 已通过保留证据并原位截断 42.2 GB 日志，将生产根盘容量/inode 从 100% 恢复到 22%/2%，导出打印业务恢复；XXL-JOB 保留期、POI 临时文件释放、日志轮转和模板扩容仍待受控发布。任务 13 的分批查询修复已合并 `master`，生产部署待核对、尚未重跑。`2026-10-01` 已在本机拉取前后端源码并完成初读，见 [源码导读](otwms-server/SOURCE_CODE_GUIDE.md)。

### tms-server

- 路径：[`tms-server/`](tms-server/)
- 范围：`tms.cambodianexpress.com` 的 GCP 入口、Tomcat 实例、Bitbucket/Jenkins 发布链路和服务故障定位。
- 当前状态：`2026-10-01` 再次捕捉 TMS 本机 HTTP 阻塞和 LB backend_timeout，根因未确认；FD 软/硬上限均为 4096，用户授权的软上限试验因硬上限及管理员访问障碍尚未执行。详见 [间歇超时记录](tms-server/INCIDENT_2026-09-30_INTERMITTENT_TIMEOUT.md)；历史 OOM 风险仍待治理。

### ssl

- 路径：[`ssl/`](ssl/)
- 范围：`ceccsl.com` 的通配符双证书、自动续期、Nginx、DNS 与网站部署结构。
- 当前状态：已根据新服务器部署摘要建立基线文档；`static` 与 `download-app` 仍按规划项管理，实时 DNS 和站点状态需要后续验证。

### mallgogo-sever

- 路径：[`mallgogo-sever/`](mallgogo-sever/)
- 范围：MallGoGo ECS 部署、Nuxt/Next.js 版本辨识、网络链路、静态资源、外部 API、图片代理和 MySQL 性能诊断。
- 当前状态：已完成基于源码、ECS 配置和公网入口的首轮分析；高概率瓶颈为 3 Mbps 公网带宽、生产启动模式、跨网无缓存 API 和图片中转，仍需服务器内分层计时确认。

### new-ccsl-server

- 路径：[`new-ccsl-server/`](new-ccsl-server/)
- 范围：新 CCSL 服务器的基础设施基线、应用部署、域名与 HTTPS、数据迁移、上线验证和长期运维。
- 当前状态：已归档 2026-07-21 生产连接池耗尽事故；服务已恢复但永久修复未完成，当前首要方向为 Redis Cache 锁竞争、事务范围、Hikari 监控和服务管理。
- 自动化：已建立只读服务器基线和 Jenkins 发布验证脚本，可经 SSH 直接执行并输出脱敏结果。

### admin-portal

- 路径：[`admin_portal/`](admin_portal/)
- 范围：本机管理后台，聚合本机信息、健康状况、`sens-server` 目录文档快照和后台登录账号管理。
- 当前状态：已建立 FastAPI + React 本地后台，接通本机 MySQL `sens` 库和默认管理员账号 `sens`；后台已支持登录、用户管理 CRUD、dashboard 和设备记录刷新。当前默认数据库已迁移到本机 MySQL 8.4，旧版 5.6 作为独立实例保留，脚本提供初始化、状态、停止、重启、自检和设备记录刷新流程。

### ce-finance

- 路径：[`ce-finance/`](ce-finance/)
- 范围：CE 的账目范围、账户索引、收支、应收应付、报销、对账、月结和财务行动项管理。
- 当前状态：已建立不含实际金额和敏感账户信息的首版框架；主体、币种、账户、数据来源和起始期间均待确认。
- 数据原则：Markdown 保存规则、索引和摘要，逐笔流水使用结构化表格或财务系统。

### cngg-project

- 路径：[`cngg-project/`](cngg-project/)
- 范围：菜鸟裹裹（CNGG）与 CE/CCSL 国际直邮及集运业务对接，包含接口规格、业务流程和待确认事项。
- 当前状态：需求已从 Anytype `sens` 空间 Task「菜鸟裹裹项目开发需求」和 Page「菜鸟裹裹接口文档」整理完成（读取时间 2026-08-06）；本期优先接入集运业务的 5 个必接接口，直邮下一期接入；开发优先节点 2026-08-15 至 2026-08-20，分国家放量 2026-08-20 至 2026-08-25。

### office-server

- 路径：[`office-server/`](office-server/)
- 范围：办公室 Apple Silicon iMac 的资产、远程访问、部署、运行与维护记录；具体业务用途待确认。
- 当前状态：已完成脱敏基线检查并验证 SSH Key 登录；磁盘空间充足，当前主要风险为未启用防火墙、FileVault 和备份，以及远程桌面服务对所有接口监听。

### office-network

- 路径：[`office-network/`](office-network/)
- 范围：以 MikroTik 设备为核心的办公网络资产、拓扑、配置、监控、备份和故障处理。
- 当前状态：已确认网关为 RB3011UiAS / RouterOS 6.49.1，当前 WebFig 账号可读写 NAT/Firewall，并建立公网端口映射 Runbook/只读预检查脚本；完整网络拓扑和规则顺序仍待盘点。

## 记录质量标准

- 快速理解：先结论，后证据、风险和下一步；标题和首段直接说明当前重点。
- 简短明确：删除重复背景、聊天复述、无结论过程和可由链接替代的细节。
- 可追溯：重要结论能看出日期、背景和来源。
- 可行动：待办尽量包含负责人、下一步和时间要求。
- 可区分：事实、推断、建议、决定和风险不混写。
- 可维护：同一事实只有一个主要落点，其他文件用链接引用。
- 可保护：敏感信息不进入版本库。

## 当前目录

- `records/projects/`：长期项目主记录。
- `records/daily/`：跨天日常记录。
- `records/meetings/`：会议记录。
- `google-otwms/`：OTWMS / GCP 运维子项目。
- `google-cloud/`：Google Cloud 项目级管理子项目。
- `otwms-ce-lb/`：CE/WMS 的 GCP 入口、共享平台、源码/构建与应用服务器运维子项目。
- `otwms-wms-server/`：GCP `wms-server` 的独立基线和故障恢复子项目。
- `otwms-server/`：OTWMS Java 后端源码、构建、生产部署和任务执行故障子项目。
- `tms-server/`：TMS 域名入口、Java/Tomcat、源码发布与故障恢复子项目。
- `ssl/`：`ceccsl.com` HTTPS 与网站部署子项目。
- `mallgogo-sever/`：MallGoGo SSR 服务器性能子项目。
- `new-ccsl-server/`：新 CCSL 服务器建设与运维子项目。
- `ce-finance/`：CE 财务账目与月结管理子项目。
- `cngg-project/`：菜鸟裹裹（CNGG）国际直邮及集运业务对接子项目。
- `office-server/`：办公室服务器相关工作的子项目。
- `office-network/`：基于 MikroTik 设备的办公网络管理子项目。
- `reference/`：沟通协议、维护规则和工作项生命周期。
- `templates/`：项目、每日和会议模板。

## 维护原则

- 记录真正影响后续工作的内容。
- 项目文件保存当前有效状态；迭代日志保存变化轨迹。
- 复杂细节留在对应项目或专题文件，不把总览写成流水账。
- 已过期内容应明确标记、归档或替换，不能与当前结论并列造成歧义。
- 稳定重复操作采用“脚本执行、文档解释、记录留痕”的方式维护；脚本不得硬编码生产凭证或默认执行变更。
- 每次写入 Markdown 后进行压缩检查：能删而不影响事实、决定或行动的信息应删除。
