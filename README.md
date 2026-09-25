# sens

个人工作管理与长期协作仓库，用来沉淀工作背景、项目进度、会议结论、重要决策和可复用流程。

## 核心阅读规则

> 所有 Markdown 必须简短、明确、可快速扫描。先写当前结论，再写关键证据、风险和下一步；不复制聊天全文，不保留重复背景或无结论的操作过程。目标是让 AI 或人员在短时间内准确恢复重点。

## 从这里开始

1. [PROJECT_READ_FIRST.md](PROJECT_READ_FIRST.md)
2. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)
3. [PROJECT_ITERATION_LOG.md](PROJECT_ITERATION_LOG.md)
4. [SKILL.md](SKILL.md)
5. [RUNBOOK.md](RUNBOOK.md)

## 目录说明

- `records/projects/`：项目记录，一项长期工作一个文件。
- `records/daily/`：需要跨天保留的日常工作记录。
- `records/meetings/`：会议结论、负责人和后续行动。
- `google-otwms/`：OTWMS 在 Google Cloud 上的运维子项目记录。
- `google-cloud/`：Google Cloud 项目级资源、访问、费用与管理规则记录。
- `otwms-ce-lb/`：CE/WMS 的 GCP 入口、共享服务、源码/构建平台和应用服务器记录。
- `otwms-wms-server/`：GCP `wms-server` 的独立运行基线、访问和故障记录。
- `otwms-server/`：OTWMS Java 后端的源码、Jenkins 构建、生产部署、XXL-JOB 执行与故障定位记录。
- `tms-server/`：`tms.cambodianexpress.com` 的路由、Tomcat、源码与 Jenkins 发布映射及 OOM 事故记录。
- `ssl/`：`ceccsl.com` 的 SSL、Nginx、DNS 与网站部署子项目。
- `mallgogo-sever/`：MallGoGo SSR 的服务器部署与性能诊断子项目。
- `new-ccsl-server/`：新 CCSL 服务器的建设、迁移、部署与运维子项目。
- `admin_portal/`：本机管理后台，聚合本机信息、健康状况和 `sens-server` 文档快照。
- `ce-finance/`：CE 财务账目、账户、对账与月结管理子项目。
- `cngg-project/`：菜鸟裹裹（CNGG）国际直邮及集运业务对接子项目。
- `office-server/`：办公室服务器相关工作的子项目。
- `office-network/`：基于 MikroTik 设备的办公网络配置、监控与运维子项目。
- `reference/`：长期有效的沟通规则、记录规范和专题方法。
- `templates/`：新建记录时复用的轻量模板。

## 基本原则

- 先阅读现有记录，再开始新的工作。
- 事实、推断、决定和待办分开表达。
- 只记录有助于后续工作的内容，避免把聊天全文搬进仓库。
- 稳定背景写入总览，变化写入迭代日志，复杂主题拆到独立记录。
- 密码、Token、私钥和生产凭证不得提交到仓库。
- 已验证且会重复执行的检查应优先沉淀为项目内 Python 脚本；脚本默认只读、脱敏、参数化，并通过退出码或结构化输出提供明确结果。
- 文档记录脚本的使用场景、边界和判定标准；不得只保留一串缺少上下文的临时命令。

## 当前状态

- 记录体系版本：`v0.17.0`
- 建立日期：`2026-07-15`
- 当前阶段：基础记录框架已建立，正在沉淀技术运维、业务对接与财务管理子项目。
