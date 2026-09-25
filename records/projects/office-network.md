# Office Network

## 当前状态

- 状态：`proposed`
- 已创建 [`office-network/`](../../office-network/) 子项目。
- 已确认项目以办公网 MikroTik 设备的配置、监控和运维为核心。
- 已识别两台在线 VMware ESXi 主机，HTTPS 管理开放、SSH 关闭；`esxi-02` 已完成首轮只读基线。
- MikroTik 已确认为 RB3011UiAS / RouterOS 6.49.1；当前 `admin` 组具备 WebFig `read/write`，可配置 NAT/Firewall，但无用户管理、SSH 或 API 权限。
- 已建立公网端口映射 Runbook 和只读预检查脚本；实际变更仍需明确服务参数并审核现有 NAT/Filter 规则。

## 重要决定

| 日期 | 决定 | 影响 |
|---|---|---|
| 2026-08-08 | 项目命名为 `office-network` | 范围可从交换机扩展至完整办公网络运维 |
| 2026-09-19 | 端口映射先只读预检，再人工确认并实施 | 配置最多包含一条必要 DST-NAT 和一条条件性 Forward 放行规则 |

## 下一步

- 盘点 MikroTik 设备及 RouterOS 版本。
- 采集脱敏后的端口、VLAN、网段和拓扑基线。
- 明确配置备份、监控、升级与故障恢复要求。
- 在首次真实端口映射时验证 Runbook 和脚本，再评估是否提炼为仓库 Skill。
- 盘点 MikroTik DHCP、DNS、路由、接口和完整 Filter/NAT 规则顺序。

## 风险

- 网络基线尚未采集，现有配置和故障风险未知。
- 采集内容可能包含敏感网络信息，必须按项目安全边界脱敏。
- WebFig 当前使用 HTTP，管理凭据与会话缺少传输加密。

详细范围、完成标准和行动项见 [`PROJECT_OVERVIEW.md`](../../office-network/PROJECT_OVERVIEW.md)。
