# Jira 需求服务（0.3.0）

通过现有 Jira Server REST API 创建需求、关闭或标记不做、JQL 汇总和 CSV 导出。服务位于本机 Mac，仅监听 `127.0.0.1:8765`；通过 HTTPS 访问 Jira，不直接写 Jira 数据库。

2026-10-03：真实 API 创建 CE-2629 并核对成功，18 项隔离测试通过。关闭/不做已完成真实工作流预检查，尚未实际取消需求；全部 API 字段 CSV 尚未与后台“CSV（所有域）”对齐。新增解决日期周报/月报精简导出，九月已实测导出 152 条。当前适合本机受控使用，生产部署尚未完成。

## 阅读与使用

- [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：功能评估、验证证据、需求记录、风险及下一步。
- [RUNBOOK.md](RUNBOOK.md)：启动、凭据配置、接口与创建/关闭/导出示例、故障处理。
- [父项目 Jira 接入说明](../JIRA_REQUIREMENTS.md)：Jira 平台、认证和工具选择。

入口为 [本机接口文档](http://127.0.0.1:8765/docs)，服务启动后在 Authorize 填入本地服务密钥。Jira 密码和服务密钥保存在 Git 忽略的 `.local/config.json`，不要写入文档或聊天。

实现入口：[app.py](app.py)、[reporting.py](reporting.py)、[run.py](run.py)、[setup_local.py](setup_local.py)；导出命令入口：[export_report.py](export_report.py)。验证入口：[tests/test_service.py](tests/test_service.py)、[tests/test_export_report.py](tests/test_export_report.py)。

复用结论：已补充月报/日期区间导出脚本，暂不另建独立 Skill；评估与命令示例集中在 Runbook。

后续导出默认保存到 `/Users/lingang/Downloads`；脚本可通过 `--output` 指定其他位置，拒绝覆盖已有文件。
