# Google Cloud 资源快照

采集日期：`2026-09-17`；来源：Chrome 中的 Google Cloud 控制台，项目 `cambodian-express`。以下仅是页面当时显示的状态，不代表后续实时状态。

## 项目与 Compute Engine

| 项目 | 控制台结果 |
|---|---|
| 显示名 / ID | `Cambodian Express` / `cambodian-express` |
| 项目编号 | `614236115553` |
| 项目选择器 | “All”列表只显示此项目；不据此断言账号在其他身份下无项目 |
| Compute Engine 总览 | 9 台 VM、4 个实例组、10 块磁盘、44 个快照、3 个映像 |
| VM 所在区域 | 本次列表中 9 台均为 `asia-southeast1-a` |

## VM 列表

控制台当时将下列 9 台都标为 `Running`；这是虚拟机状态，不是业务健康检查结果。

| 类别 | VM 名称 |
|---|---|
| 入口 | `ce-lb` |
| OTWMS | `otwms-group-1ktm`、`otwms-uat` |
| TMS | `tms-instance-template-20251103-082933`、`tms-uat` |
| Toucha | `toucha-backend`、`toucha-uat` |
| WMS | `wms-db`、`wms-server` |

`otwms-group-1ktm` 属于 `otwms-group`，其名称会随托管实例组重建而变化。`wms-server` 的运行状态与同日连接故障并存，详见 [`otwms-wms-server` 事故记录](../otwms-wms-server/INCIDENT_2026-09-17_UNRESPONSIVE.md)。

`2026-09-17` 再核对机型：当前 9 台 VM 均为 E2 或 C2 系列；6 个实例模板也均为 E2 或 C2。未发现 A2/G2，因此当日“A2/G2 快速启动节点创建失败”告警无需针对现有 VM 或模板处置；未来若新建 A2/G2，仍需重新查看事件状态。

## 实例组

| 名称 | 类型 | 成员数 | 控制台提示 |
|---|---|---:|---|
| `otwms-group` | 托管 | 1 | 自动扩缩容关闭，原配置保留 |
| `tms-group` | 托管 | 0 | 自动扩缩容关闭，原配置保留 |
| `gke-cluster-1-default-pool-a88c573d-grp` | 托管 | 0 | 关联 `cluster-1`；未核实 GKE 集群状态 |
| `ngrok-instance-group` | 非托管 | 0 | 关联 `ngrok-backend`；未核实后端用途 |

## 尚待核实

- IAM 成员、服务账号及权限边界。
- 账单账号、预算、告警与成本归属。
- VPC、子网、防火墙、负载均衡、DNS 和公网暴露。
- Cloud Storage bucket、数据库服务、GKE、监控日志与备份策略。

以上“尚待核实”表示本次未盘点，不代表资源不存在。
