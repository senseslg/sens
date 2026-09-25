# Google Cloud 项目总览

更新日期：`2026-09-17`。本子项目用于管理 Google Cloud 控制台层面的项目、资源、访问、成本与变更记录。

## 当前范围

- 已通过 Chrome 控制台核实：当前可见项目 `Cambodian Express`，项目 ID `cambodian-express`，项目编号 `614236115553`；项目选择器的“All”列表仅显示这一项目。
- 已初步盘点 Compute Engine 的 VM、实例组、磁盘、快照和映像数量。详见 [RESOURCE_INVENTORY.md](RESOURCE_INVENTORY.md)。
- IAM、账单结构与预算、VPC/防火墙、负载均衡、Cloud Storage、GKE、监控及日志尚未逐项核实，不能仅凭控制台快捷入口推断其配置或使用情况。

## 管理目标

- 维护可追溯的项目级资源索引，发现资源、成本和安全变化。
- 为跨服务的 Google Cloud 操作提供一致的只读检查、变更前核对和事后验证规则。
- 将实例、应用、数据库等深入运维记录链接到已有子项目，避免重复维护互相冲突的状态。

## 当前重点

1. 盘点 `otwms-group` 和 `tms-group` 的目标规模、自动扩缩容关闭原因及其业务预期；当前仅确认控制台状态，未作配置变更。
2. 核实 IAM/服务账号、账单预算、VPC/防火墙、存储与备份、监控告警的真实配置，并补充资源所有者和用途。
3. 处理具体服务问题时，先查对应子项目：[`google-otwms/`](../google-otwms/)、[`otwms-ce-lb/`](../otwms-ce-lb/)、[`otwms-wms-server/`](../otwms-wms-server/)。

风险：Compute Engine 列表中的 `wms-server` 显示运行，但同日服务运维记录显示 SSH 与端口不可达。项目级巡检应保留这一状态差异，不将 `Running` 写作“服务正常”。
