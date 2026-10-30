# Google Cloud 项目总览

更新日期：`2026-10-24`。本子项目用于管理 Google Cloud 控制台层面的项目、资源、访问、成本与变更记录。

## 当前范围

- 已通过 Chrome 控制台核实：当前可见项目 `Cambodian Express`，项目 ID `cambodian-express`，项目编号 `614236115553`；项目选择器的“All”列表仅显示这一项目。
- 已初步盘点 Compute Engine 的 VM、实例组、磁盘、快照和映像数量。详见 [RESOURCE_INVENTORY.md](RESOURCE_INVENTORY.md)。
- 已重新核实 9 月税后 `$4,075.25`，目标税后 `$2,000`；[完整优化清单](COST_OPTIMIZATION_CHECKLIST_2026-10-24.md) 含 28 项待办、控制台入口、负载证据和估价条件，未调整资源。
- 当前 9 台运行 VM、2 SQL、3 Redis、1 个节点组为 0 的 GKE、10 块磁盘、45 个快照、3 镜像、19 地址（16 全局/3 区域）、33 条转发规则、17 bucket；IAM、VPC/防火墙及逐 key 业务归属仍需核实。
- `tms-db` 当前约 95.4% 磁盘已用，接口日志物理约 716 GiB；旧日志尚未清完。`ce-tms` 两年前对象版本约 829 万个/2,537 GiB，须先确认引用和保留要求；见完整清单和 [历史清理计划](TMS_INBOUND_LOG_CLEANUP_PLAN.md)。

## 管理目标

- 维护可追溯的项目级资源索引，发现资源、成本和安全变化。
- 为跨服务的 Google Cloud 操作提供一致的只读检查、变更前核对和事后验证规则。
- 将实例、应用、数据库等深入运维记录链接到已有子项目，避免重复维护互相冲突的状态。

## 当前重点

1. 核实 `tms-uat`、`otwms-uat`、`toucha-uat` 最近 30 天使用证据，形成首批停用清单。
2. 将 Geocoding、Translate、Cloud SQL、Compute Engine 和负载均衡分别压到降本计划的费用上限。
3. 为 `tms-db` 建立容量与性能基线，确认接口日志保留期并在克隆环境验证表空间回收和降配方案。
4. 核实 IAM/服务账号、预算、VPC/防火墙、逐 bucket 用量及资源所有者。

风险：Compute Engine 的 `Running` 只代表虚拟机状态，不代表业务健康。`wms-server` 当前仍运行，但 `cewms.service` 已停止且公网 WMS 返回 502，只有 `cp.service` 继续提供服务；不得据 VM 状态写作“WMS 正常”。
