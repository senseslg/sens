# Project Iteration Log

仅记录对后续开发有参考价值的重要变更，细小的调整不必列入。

## v0.1.0 - 2026-04-25

- 创建项目根目录文档体系（README、PROJECT_OVERVIEW、PROJECT_READ_FIRST、PROJECT_ITERATION_LOG）。
- 确定核心接口设计：用户提供 `lat` / `lon`，Token 鉴权，返回 `province`（level=2 area.id）和 `district`（level=3 area.id）。
- 设计 `api_token` 和 `api_request_log` 两张数据库表。
- 明确 Google Geocoding API 调用参数和八个地址字段的提取规则。
- 明确 `new_ccsl.area` 表地区匹配逻辑（按 name / level / is_deleted 查询）。
