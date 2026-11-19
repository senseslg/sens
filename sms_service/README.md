# SMS Service

PlasGate REST 单发/批发调用工具。只依赖 Python 3.10+ 标准库，默认离线预览，加 `--apply` 才发送。接口要点见 [REST_API.md](REST_API.md)。继承上级 `PROJECT_READ_FIRST.md` 和全局框架规则。

## 凭据

在本机 [config.local.json](config.local.json) 填入 `private_key` 和 `X-Secret`。文件已创建为空值、权限 `600` 且被 Git 忽略；不要将真实凭据写进示例、脚本或聊天。

也可用环境变量 `PLASGATE_PRIVATE_KEY`、`PLASGATE_X_SECRET`（各字段优先于配置文件）。配置文件必须为当前用户所有、普通文件、权限 `600`，脚本不接受符号链接。

## 调用

从仓库根目录运行，先将示例复制到 Git 忽略的 `sms_service/secrets/` 下并填写真实号码、sender、内容：

```bash
mkdir -p sms_service/secrets
cp sms_service/message.example.json sms_service/secrets/message.json
chmod 600 sms_service/secrets/message.json
python3 sms_service/scripts/send_sms.py --payload sms_service/secrets/message.json
# 确认号码、内容和发送授权后执行：
python3 sms_service/scripts/send_sms.py --payload sms_service/secrets/message.json --apply
```

批发使用 `--batch --payload <批发JSON路径>`，格式见 [batch.example.json](batch.example.json)。自定义凭据文件用 `--config <路径>`；端点由 `PLASGATE_BASE_URL` 或 `--base-url` 设置，默认官方域名，仅允许 HTTPS。密钥只会发送到所配置的端点，变更端点前核对目标。

Python 集成可导入 `scripts/send_sms.py` 的 `send_request(payload, credentials, batch=False, base_url=..., timeout=...)`；它返回 `(HTTP状态码, 原始响应字节)`，调用方负责业务码、回执判定和数据保护。

## 结果与验证

- CLI 仅输出脱敏摘要，不打印号码、短信正文、密钥、请求 URL 查询串或服务端原始响应。
- HTTP 2xx 输出 `http_response_received`，业务状态仍为 `unverified`；HTTP 错误、超时和断连均不自动重试，避免重复扣费。结果不明时先查交易报告。
- 退出码：`0` 预览完成或收到 HTTP 2xx；`1` HTTP 非 2xx；`2` 参数、配置、网络等执行错误。
- 离线检查：`python3 -m unittest discover -s sms_service/tests -v`。

当前状态（2026-11-19）：已配置本地凭据并按用户授权尝试单条测试；接口返回 HTTP 403、`403 Untrusted Token`，未获受理。原始响应仅保存在 Git 忽略的 `secrets/test-2026-11-19.response.json`；下一步核对配对凭据及 API 启用状态。复用方式为项目内脚本，暂不创建全局 Skill。

本机 Python HTTPS 校验出现 `self signed certificate in certificate chain`；本轮改用保持证书校验的系统 `/usr/bin/curl` 完成接口请求。Python 脚本的真实网络链路仍待修复证书信任配置后验证。
