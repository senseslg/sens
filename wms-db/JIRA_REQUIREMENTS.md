# Jira 需求管理接入

## 当前状态（2026-10-03）

Jira 地址为 [issue.cambodianexpress.com](https://issue.cambodianexpress.com/)，实测 Jira Server 7.12.0，位于 GCP `wms-db`。Chrome 和本机 Python 服务均已验证 `sens` 认证；现有 REST API 可以创建、查询、导出和调用工作流，无需先升级 Jira。

主工具为 [jira-service 0.3.0](jira-service/README.md)。真实 API 已创建 CE-2629；CCSL-2679 是此前通过 Chrome 创建的需求，已用 API 查询与导出。关闭/不做功能已开发并通过真实预检查，未实际取消需求。完整证据、评估和待办见 [服务项目概览](jira-service/PROJECT_OVERVIEW.md)，操作见 [服务 Runbook](jira-service/RUNBOOK.md)。

## 接入约定

- 优先 API，无法规范操作时再用 Chrome；不直接向 Jira 数据库插入或修改需求。
- 根据实际项目 metadata 确定类型、必填字段和允许值。当前 CCSL/CE 任务类型为 `10300`，报告人必填；其他项目与后续变更仍需重新查询。
- 创建先预检查和查重，提交后核对关键字段；关闭/不做须有指定编号与原因，通过工作流记录状态、解决结果和备注。
- 导出默认偏好 **CSV（所有域）**。服务支持全部 API 字段 CSV，但不能将其视为后台全域等价。周报/月报改用按解决日期筛选的精简 8 列，已核对原生样本并导出九月 152 条；可用 `export_report.py` 重复导出，详见服务 Runbook。
- Python 服务在用户本机 `127.0.0.1:8765`，不是部署在 `wms-db` 的新容器；Jira 账号凭据与本地服务密钥分别管理，浏览器 Cookie 不搬入脚本。
- 后续导出文件统一默认保存到 `/Users/lingang/Downloads`，不进入仓库。

## 创建需求的信息清单（2026-10-05）

用户确认创建需求主要提供以下六项，可用自然语言表达，不要求严格填写表单。

| 信息 | 约定 | Jira/API 对应 |
|---|---|---|
| 项目平台 | 如代购商城、CCSL；匹配真实项目 | `project` |
| 类型 | 如开发任务、故障；匹配项目实际问题类型 | `issue_type_id` |
| 模块 | 如 APP、后端、前端、H5，可多选 | `extra_fields.components`，使用目标项目的模块 ID |
| 需求标题 | 保留用户给定标题 | `summary` |
| 需求描述 | 说明需要处理的事项；已知问题可以简洁，不强制扩写 | `description` |
| 到期日 | 要求完成日期；如“明天”按柬埔寨当地日期换算 | `extra_fields.duedate`，`YYYY-MM-DD` |

经办人按下方人员分工与用户指定确定，不作为额外必填的用户输入；报告人等 Jira 必填字段从当前认证身份及项目元数据补齐。缺少信息时先结合上下文判断，只询问无法可靠确定的部分；不擅自编造描述或完成日期。模块可多选，但单个 Jira 问题的经办人仍需明确，跨模块负责人不自动拆单或随机分配。

## 跨项目人员分工（2026-10-05）

用户确认以下人员支持全项目平台，按技术职责分配需求，不局限于代购商城或 CCSL。Jira 用户名与显示名已通过 API 核对，账号当前均为启用状态。

| 同事／显示名 | Jira 用户名（API 经办人） | 职责 |
|---|---|---|
| longmh | `longmh` | 仅 APP 客户端开发 |
| HENG HONGTHAI | `BRIAN` | 仅前端与 H5 客户端开发 |
| YUTH（Jira 显示名 yuth） | `yuth` | 后端开发 |
| 胡志武 | `huzw` | 后端开发 |
| milinfang | `milf` | 测试工程师 |

创建时先识别项目、模块和问题类型，再按上述职责选择经办人。用户明确指定经办人时优先采用该指示；后端由两位同事负责，未明确负责人时结合现有归属确定，无法确定则询问，不固定默认给其中一人。跨模块需求应明确各自负责内容，不把整个需求默认交给仅负责单端的同事。

人员跨项目支持是团队职责约定，不代表 Jira 已授权全部项目；提交前仍核对目标项目的模块、创建字段及经办人可分配性。API 使用用户名，尤其 `HENG HONGTHAI → BRIAN`、`milinfang → milf`，不能将显示名直接作为用户名。

## 认证与旧工具

7.12.0 当前使用用户名/密码 Basic Auth，私有配置位置见服务 Runbook。原生 PAT 从 8.14 起提供；本轮没有升级 Jira、安装 Token 插件、更改密码或许可证。版本升级与费用评估需另行核实许可、兼容性、备份恢复和维护窗口，不能为使用现有 API 而直接升级共享主机。

依据：[Basic Auth](https://developer.atlassian.com/server/jira/platform/basic-authentication/)、[PAT 版本要求](https://confluence.atlassian.com/enterprise/using-personal-access-tokens-1026032365.html)、[Jira REST 示例](https://developer.atlassian.com/server/jira/platform/jira-rest-api-examples/)。

早期 [jira_requirements.py](scripts/jira_requirements.py) 支持探测、创建和 JSON 分页导出，仅 `info` 已实测；不作为经过完整认证验证的日常工具。其 JSON 导出限制不代表新服务没有 CSV 功能。
