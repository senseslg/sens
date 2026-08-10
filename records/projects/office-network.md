# Office Network

## 当前状态

- 状态：`proposed`
- 已创建 [`office-network/`](../../office-network/) 子项目。
- 已确认项目以办公网 MikroTik 设备的配置、监控和运维为核心。
- 已识别两台在线 VMware ESXi 主机，HTTPS 管理开放、SSH 关闭；`esxi-02` 已完成首轮只读基线。
- MikroTik 型号、RouterOS 版本、拓扑和负责人待确认。

## 重要决定

| 日期 | 决定 | 影响 |
|---|---|---|
| 2026-08-08 | 项目命名为 `office-network` | 范围可从交换机扩展至完整办公网络运维 |

## 下一步

- 盘点 MikroTik 设备及 RouterOS 版本。
- 采集脱敏后的端口、VLAN、网段和拓扑基线。
- 明确配置备份、监控、升级与故障恢复要求。

## 风险

- 网络基线尚未采集，现有配置和故障风险未知。
- 采集内容可能包含敏感网络信息，必须按项目安全边界脱敏。

详细范围、完成标准和行动项见 [`PROJECT_OVERVIEW.md`](../../office-network/PROJECT_OVERVIEW.md)。
