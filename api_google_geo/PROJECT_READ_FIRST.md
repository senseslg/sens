# Project Read First

开始任何新需求前先阅读：

1. `PROJECT_OVERVIEW.md` — 接口设计、字段提取规则、数据库表结构、匹配逻辑
2. `PROJECT_ITERATION_LOG.md` — 已交付的功能和重要工程里程碑

## 关于文档更新

当改动影响以下任一方面时：

- 接口参数或响应结构
- Token 鉴权规则
- Google API 调用方式或字段提取规则
- 地区匹配逻辑
- 数据库表结构

请：

- 更新 `PROJECT_OVERVIEW.md` 中对应章节
- 在 `PROJECT_ITERATION_LOG.md` 末尾追加一条版本记录

## 关于数据库

- Token 管理：`api_token` 表，鉴权时检查 `is_active = 1` 且 `expired_at > NOW()`
- 请求日志：每次接口调用（包括失败）都必须写入 `api_request_log`
- 地区匹配：使用 `new_ccsl.area` 表，通过 `name`、`level`、`is_deleted` 条件查询

## 关于配置

- 优先从环境变量读取 Google API Key 和数据库连接信息
- 本地开发可使用 `.env` 文件作为回退（不提交到版本库）
- 参考 `.env.example` 了解所需的配置项

## 保持简洁

- Google API 调用封装在独立 service 中
- 地区匹配封装为独立函数
- 日志写入封装为独立函数
- 不要在接口层混入业务逻辑
