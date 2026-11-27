# Project Skills

本项目重复工作的流程索引。执行前先读 [PROJECT_READ_FIRST.md](PROJECT_READ_FIRST.md)。

| Skill | File | When to use |
|---|---|---|
| OSS API 管理 | [RUNBOOK.md](RUNBOOK.md) · [scripts/oss.py](scripts/oss.py) | 列桶、查配置/容量、列/下载对象、签名 URL；上传/删除/改 ACL（默认 dry-run，需授权） |
| OSS 安全加固 | [reference/security-hardening-plan.md](reference/security-hardening-plan.md) | 提升健康检测分数、公共读改私有、防盗链、日志转存 |
| 更新版本与文档 | [reference/update-version-docs.md](reference/update-version-docs.md) | 行为、模块、数据流变化时升版本并追加日志 |

- 流程描述触点与顺序，不替代读取当前状态；写操作仍按 AGENTS.md 逐项授权。
