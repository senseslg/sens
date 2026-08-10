# new-ccsl-server

新 CCSL 服务器的建设、迁移、部署与长期运维子项目。

## 核心阅读规则

> 本目录所有 Markdown 必须简短、明确、可快速扫描。先写当前结论，再写关键证据、风险和下一步；详细事故、发布过程拆到独立记录，总览只保留稳定状态和链接。

## 阅读顺序

1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：目标、范围、状态和行动项。
2. [INCIDENT_2026-07-21_DB_POOL_EXHAUSTION.md](INCIDENT_2026-07-21_DB_POOL_EXHAUSTION.md)：生产连接池耗尽事故、根因和修复行动。
3. [SERVER_INVENTORY.md](SERVER_INVENTORY.md)：服务器、网络、域名和服务清单。
4. [RUNBOOK.md](RUNBOOK.md)：安全检查、部署、验证和故障排查流程。
5. [ROADMAP.md](ROADMAP.md)：分阶段建设计划与验收条件。
6. [DEPLOYMENT_2026-07-22_JENKINS.md](DEPLOYMENT_2026-07-22_JENKINS.md)：2026-07-22 Jenkins 生产发布验证记录。
7. [scripts/README.md](scripts/README.md)：可重复执行的只读基线和发布验证脚本。

## 当前状态

- 状态：`active`
- 建立日期：`2026-07-21`
- 已确认：新服务器系统与资源基线、CCSL 生产/UAT Java 端口、Nginx 路由、Hikari/MySQL/Redis 依赖和 2026-07-21 连接池耗尽事故基线。
- 当前重点：修复 Redis Cache 锁竞争、缩短事务范围、监控 Hikari 并完善服务管理。
- 待确认：Region/Zone、完整安全组、应用版本标识、Hikari 参数、迁移范围和上线目标。

## 记录原则

- 事实、推断、建议和决定分开记录。
- 密码、Token、私钥、Cookie 和完整生产连接串不得写入仓库。
- 公网 IP、实例 ID 等基础设施标识只在确有运维必要时记录，并优先使用脱敏引用。
- 生产变更必须先明确影响、备份、验证和回滚方法。
- 已验证且会重复使用的只读检查应沉淀为 `scripts/` 下的 Python 脚本；文档负责说明目的、边界和判定标准，脚本负责一致执行和结构化输出。
- 脚本默认不得内置服务器 IP、账号密码或 Token，不得输出完整进程参数或原始敏感日志。
