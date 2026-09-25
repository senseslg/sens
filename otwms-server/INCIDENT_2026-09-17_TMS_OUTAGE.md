# OTWMS 受 TMS 中断影响（2026-09-17—18）

TMS 的完整入口、OOM、Jenkins #456 与恢复证据统一维护在 [tms-server 事故记录](../tms-server/INCIDENT_2026-09-17_OOM_AND_RECOVERY.md)，这里仅记录 OTWMS 的依赖影响，避免两处事故时间线漂移。

## 已确认影响

- 2026-09-17 OTWMS 生产日志曾记录向 `https://tms.cambodianexpress.com/api/public/tms/shipment/scan-update-app` 发起的 Feign 调用收到 502。TMS 中断会影响这类跨系统业务动作。
- Franchise/Courier App 可以登录但换页出现 `network connection error`，用户未提供失败请求 URL/状态码；不能证明所有页面都直接依赖 TMS，也不能仅凭 TMS 登录页恢复确认两款 App 全面恢复。

## 当前状态与下一步

- 2026-09-18，TMS 公网登录页与本机 HTTP 已恢复；OTWMS 的独立登录和部分接口此前也可用。
- 由业务方复测两款 App 的原故障页面。若仍报错，采集具体请求 URL/时间/状态码，再分别核对 OTWMS 与 TMS 日志，不把所有移动端错误归于单一服务。
