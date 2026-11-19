# 项目总览

版本：0.1.1。

复用 CCSL Telegram Bot API，供其他项目通过 Python 或命令行调用。无第三方 Python 依赖，无常驻服务。

`scripts/send.py` 提供 `send_message()` 和显式发送入口；`.local/credentials.json` 保存私密配置；调用方式见 [RUNBOOK.md](RUNBOOK.md)。2026-11-19 获授权发送 1 条 `[SENS-TEST]` 消息成功（`ok: true`、`message_id: 3434`）；本机 TLS 处理见 [RUNBOOK.md](RUNBOOK.md)。

CLI 与 Python helper 已统一自动加载 macOS 系统 CA，并尊重显式 CA 环境配置；本地配置/TLS 检查、6 项离线回归与 Telegram 公共首页 HTTPS 验证通过。
