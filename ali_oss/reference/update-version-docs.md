# Skill: Update Version and Docs

在任何影响行为、模块、可复用逻辑、权限或数据流的改动结束时使用。

## SemVer

| 变化 | 升级 |
|---|---|
| 破坏性变更、权限模型重设计、数据模型重写、不兼容 API | MAJOR |
| 新模块、新可复用工具、明显能力扩展 | MINOR |
| 修复、小行为调整、文档或流程更新 | PATCH |

## Steps

1. 发布级变更才升 `package.json`（或等价文件）的版本号。
2. 稳定背景变化时更新 `PROJECT_OVERVIEW.md`，版本行与第 1 步一致。
3. 在 `PROJECT_ITERATION_LOG.md` 分隔线下顶部加一行：`- **vX.Y.Z** YYYY-MM-DD — 一句话描述`。
4. 细节（字段、规则、公式）写到对应 `reference/*.md`，日志里链接过去。
5. 提交前确认两处版本号一致。
