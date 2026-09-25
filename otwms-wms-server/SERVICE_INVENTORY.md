# WMS Server Service Inventory

## 已确认的服务边界

| 服务/入口 | 依据 | 当前状态 |
|---|---|---|
| CEWMS .NET 后台 | `cewms.service` active，`dotnet` 监听 80 | 2026-09-17 扩容后本机 HTTP 200 |
| `cp.cambodianexpress.com` 后端 | `ce-lb` Nginx 代理到本实例 90 端口；由另一 `dotnet` 进程监听 | 本机、`ce-lb` 上游和公网入口 HTTP 200；具体服务名称待核实 |
| SSH | GCP 实例无外部 IP，使用 IAP | 扩容后可登录 |

历史 CEWMS 发布目录为 `/usr/local/cewms/prod/publish`，当时仅见编译产物、未见源码；源码/构建映射仍需在 Bitbucket/Jenkins 核对。详见 [原始基线](../otwms-ce-lb/WMS_SERVER.md)。

不在仓库记录内部上游地址、凭证、业务日志内容或完整生产连接串。上述状态是 2026-09-17 恢复后的验证快照。
