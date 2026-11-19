# PlasGate REST 调用记录

核验日期：2026-11-19。来源：[官方 REST 文档](https://cloud.plasgate.com/support/rest)（读取该页面公开加载的 REST 文档资源）。以下为调用要点整理。

## 通用规则

- 需要有效 API Key 和账户余额；凭据入口：[API 管理](https://cloud.plasgate.com/smppapi)。
- HTTPS POST；URL 查询参数 `private_key`，请求头 `X-Secret`；请求体为 JSON，使用 `Content-Type: application/json`。
- 本文的 `private_key` 是服务商 API 凭据字符串，不是 SSH 私钥文件。

| 用途 | 地址 | 文档限流 |
|---|---|---|
| 单发 | `https://cloudapi.plasgate.com/rest/send` | 200 请求/分钟 |
| 批发 | `https://cloudapi.plasgate.com/rest/batch-send` | 100 请求/分钟 |

## 单发

JSON 包含 `sender`（发送方文本）、`to`（接收号码）、`content`（短信文本），见 [单发示例](message.example.json)。官方示例以字符串传号码，例如 `85512345678`；真实 sender 使用账号获准的值。

可把敏感片段写成 `#ma#片段#ma#`，支持多个片段。接收人看到原文，交易报告中该片段显示为星号，标记本身不出现在接收设备上。这不代替本地日志脱敏。

## 批发

见 [批发示例](batch.example.json)：

- 必填 `globals`，文档示例为 `{"sender":"SMS Info"}`。
- 必填 `messages` 数组，各项包含号码数组 `to` 和文本 `content`。
- 可选 `batch_config`，文档示例为 `{"callback_url":"https://example.com/callback","schedule_at":"2021-09-30 09:00:00"}`。

## 文档边界

该页未定义响应结构、业务成功码、回执签名、号码完整校验规则、单批最大数量或 `schedule_at` 时区。定时发送前先向服务商确认时区；HTTP 2xx 不能直接证明投递成功。

官方扩展资料：[Postman 文档](https://documenter.getpostman.com/view/10217000/UzXKXf3S)（本轮未核验其内容）。本脚本不实现回调服务、自动重试或跨进程限流；多次调用需由调用方按上述配额控制。
