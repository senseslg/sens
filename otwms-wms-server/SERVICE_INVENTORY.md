# WMS Server Service Inventory

## 公网域名映射（2026-10-17 核实）

`https://wms.cambodianexpress.com/` 的服务端确认为本实例。GCP 只读查询链路：`tms-lb` 的主机规则 → `path-matcher-1` → `wms-backend` → `wms-backend-neg` → `wms-server:80`。结合下方部署基线，对应 CEWMS .NET 后台；本次未登录应用或检查业务功能。此项为域名定位核实，无需新增脚本或 Skill。

## 已确认的服务边界

| 服务/入口 | 依据 | 当前状态 |
|---|---|---|
| CEWMS .NET 后台 | `cewms.service`，原监听 80 | 2026-10-17 按用户要求停止，inactive/dead、80 不再监听，公网 HTTP 502；开机自启仍 enabled |
| `cp.cambodianexpress.com` 后端 | `ce-lb` Nginx 代理到本实例 90 端口；`cp.service` | 2026-10-17 active/running，90 端口监听；本次未验证公网功能 |
| SSH | GCP 实例无外部 IP，使用 IAP | 扩容后可登录 |

历史 CEWMS 发布目录为 `/usr/local/cewms/prod/publish`，当时仅见编译产物、未见源码；源码/构建映射仍需在 Bitbucket/Jenkins 核对。详见 [原始基线](../otwms-ce-lb/WMS_SERVER.md)。

不在仓库记录内部上游地址、凭证、业务日志内容或完整生产连接串。服务状态以各行验证日期为准。
