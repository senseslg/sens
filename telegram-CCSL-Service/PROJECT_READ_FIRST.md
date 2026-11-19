# Project Read First

> **强制规则：** 新增或更新 Markdown 必须简短、明确、可快速扫描。保留当前结论、关键证据、决定、风险和下一步；删除重复说明和聊天复述。

开始任何新需求前按顺序读取：

1. [AGENTS.md](AGENTS.md) — 常驻规则
2. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) — 稳定背景、结构、当前版本
3. [PROJECT_ITERATION_LOG.md](PROJECT_ITERATION_LOG.md) — 最近变化
4. [todos/TODO.md](todos/TODO.md) — 未结束的待办；过期、将到期、停滞的在回复开头提醒（规则见 [todos/README.md](todos/README.md)）
5. [SKILL.md](SKILL.md) — 匹配的流程，详细步骤在 `reference/`
6. [RUNBOOK.md](RUNBOOK.md) — 本机命令与环境问题
7. 与本次任务相关的 `reference/*.md`

## 改了什么 → 更新哪里

- 稳定背景变化（结构、路由、模块、运行配置、部署）→ `PROJECT_OVERVIEW.md`
- 有长期价值的变化 → `PROJECT_ITERATION_LOG.md` 顶部一行：`- **vX.Y.Z** YYYY-MM-DD — 一句话描述`
- 架构、字段、状态映射、公式、业务规则 → `reference/<feature>.md`（一功能一文件，没有就新建）
- 本机命令与环境经验 → `RUNBOOK.md`
- 新产生 / 推进 / 完成的行动项 → `todos/TODO.md`，结束后归档到 `todos/done/YYYY-MM.md`
- 发布级变更 → SemVer：`MAJOR` 破坏性 / `MINOR` 新模块或可复用能力 / `PATCH` 修复与文档

## 完成后的复用评估

- 稳定、可迁移、会重复 → `reference/`，重复出现后登记 `SKILL.md`
- 已验证、会重复执行、适合自动化 → `scripts/*.py`（只读、脱敏、参数化、退出码 / JSON）
- 单次或未稳定 → 只留记录

结论写进交付说明；不为形式完整创建低价值 skill 或脚本。

## Keep it light

- 优先共享 helper，逻辑留在仓库内。
- 只记录对下一次任务有帮助的内容。
