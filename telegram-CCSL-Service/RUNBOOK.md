# 调用说明

环境：macOS / Python 3，目录 `/Users/lingang/sens/telegram-CCSL-Service`。

## 本地验证（不发送）

```bash
python3 /Users/lingang/sens/telegram-CCSL-Service/scripts/send.py --check
```

检查配置及本地 TLS 上下文，不请求 Telegram。

## 发送（需获得对应业务授权）

```bash
printf '%s' '业务通知内容' | python3 /Users/lingang/sens/telegram-CCSL-Service/scripts/send.py --send --prefix OTHER-BUSINESS
```

默认纯文本，可传 `--parse-mode Markdown` 兼容原服务。失败不自动重试，避免重复通知。2026-11-19 已获授权完成单条真实发送，验证结果见 [项目总览](PROJECT_OVERVIEW.md)。

## Python 接入

```python
import importlib.util
spec = importlib.util.spec_from_file_location('ccsl_telegram', '/Users/lingang/sens/telegram-CCSL-Service/scripts/send.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
# 此行会发送真实消息，必须先获授权：
# module.send_message('业务通知', prefix='OTHER-BUSINESS')
```

## 配置与底层接口

优先使用环境变量 `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`，否则读取 `.local/credentials.json` 的 `bot_token`、`chat_id`。可用 `--config` 或 Python `config` 参数指定配置路径。

底层接口为 HTTPS POST `https://api.telegram.org/bot<TOKEN>/sendMessage`，表单字段 `chat_id`、`text`、可选 `parse_mode`。不要把真实 Token 拼进 shell 命令、日志或文档。脚本校验 HTTP 与 Telegram JSON 的 `ok`，错误只输出状态，不输出 URL、响应正文或消息内容。

凭据目录权限 700、配置 600。共享 Bot/目标意味着其他业务通知进入同一会话；轮换 Token 后需同步更新所有使用者。没有安装系统服务或修改生产配置。

## TLS 信任与失败处理

从 0.1.1 起，CLI 和 Python helper 自动使用相同的 TLS 上下文：macOS 在 Python 默认 CA 基础上加载系统根证书及 `/Library/Keychains/System.keychain` 的证书，无需临时文件；其他系统使用 Python 默认 CA。设置 `SSL_CERT_FILE` 或 `SSL_CERT_DIR` 时优先采用显式配置，不追加 macOS CA。

始终校验证书链和主机名。系统证书读取失败时停止发送；不关闭 TLS 校验，不修改全局配置，不自动重试。沙箱 DNS 受限时需获得网络执行权限；超时等错误可能导致投递状态未知，应先核实接收情况。

2026-11-19：系统 CA 方式真实发送成功且用户确认收到；整合后的函数通过 Telegram 公共首页 HTTPS 检查（HTTP 200），未追加测试消息。

## 离线回归检查

```bash
python3 -m unittest discover -s /Users/lingang/sens/telegram-CCSL-Service/tests -v
```

覆盖系统 CA 加载、显式 CA 优先级、证书读取失败时停止、TLS 校验、禁止自动重试及 `--check` 不发送。
