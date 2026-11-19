# Telegram CCSL Service

本机复用 CCSL Telegram Bot 的调用工具，版本 0.1.1；不是常驻 HTTP 服务。

- [调用与配置](RUNBOOK.md)
- [项目规则](PROJECT_READ_FIRST.md)
- 凭据只存 `.local/credentials.json`，不提交 Git。其他业务使用同一机器人和默认通知目标。
- 默认只验证配置；必须明确传 `--send` 才发送，发送须有业务授权。

- macOS 自动加载系统 CA，命令行与 Python 调用均无需手工导出证书；TLS 校验始终启用。
