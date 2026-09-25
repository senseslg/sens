# MikroTik Device Inventory

> 仅记录脱敏后的当前有效基线；不得保存密码、密钥、完整公网地址、序列号或完整配置导出。

## 当前结论

- MikroTik 网关已确认为 `RB3011UiAS (arm)`，运行 RouterOS `6.49.1 stable`。
- `192.168.1.0/24` 内有两台 VMware ESXi 主机，均开放 HTTPS Host Client，SSH 当前关闭。
- 当前 `admin` 账号属于自定义 `admin` 组，具备 `read`、`write` 和 `web`，可通过 WebFig 管理 NAT/Firewall；不具备 `policy`、`ssh`、`telnet` 或 `api`。

## 设备清单

| 设备代号 | 角色 | 型号 | RouterOS | 网络位置 | 管理方式 | 状态 |
|---|---|---|---|---|---|---|
| `office-gateway` | 办公网网关/交换设备 | RB3011UiAS | 6.49.1 stable | `192.168.0.0/23` | HTTP WebFig / WinBox | 在线，已确认写权限 |

## 服务器入口

| 设备代号 | 平台 | 网络位置 | 管理入口 | SSH | 状态 |
|---|---|---|---|---|---|
| `esxi-01` | VMware ESXi | `192.168.1.0/24` | HTTPS Host Client | 关闭 | 在线，待登录盘点 |
| `esxi-02` | VMware ESXi | `192.168.1.0/24` | HTTPS Host Client | 关闭 | [已完成首轮只读基线](ESXI_BASELINE.md) |

## 端口与链路

| 设备代号 | 端口 | 用途 | 对端 | VLAN / 模式 | 状态 |
|---|---|---|---|---|---|
| 待确认 | 待确认 | 待确认 | 待确认 | 待确认 | 待盘点 |

## 配置与运维基线

- 身份与时间：设备命名、时区、NTP 待确认。
- 二层网络：Bridge、VLAN、STP/RSTP 和链路聚合待确认。
- 三层服务：该设备是当前默认网关；DHCP、DNS 和完整路由基线仍待盘点。
- 防火墙：已确认可读取 Filter/NAT；现有动态规则包含 UDP 5060 与 UDP 10000–65535 的 SIP/RTP 转发，新增 UDP 映射前必须复核冲突。
- 管理面：当前 WebFig 使用 HTTP，登录流量未加密；账号可写 NAT/Firewall，但不能管理用户或通过 SSH/API 登录。
- 可观测性：日志、SNMP、流量和资源监控待确认。
- 恢复能力：配置导出、二进制备份、保留周期和恢复演练待确认。

## 采集边界

- 优先使用只读命令和脱敏输出。
- 配置导出必须先移除密码、密钥、社区字符串、公网地址和身份信息。
- 任何升级、重启、端口或 VLAN 变更都必须单独确认。
