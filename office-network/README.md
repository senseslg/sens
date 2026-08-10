# office-network

基于 MikroTik 设备的办公网络配置、监控与运维子项目。

## 阅读顺序

1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：目标、范围、状态、行动项和风险。
2. [DEVICE_INVENTORY.md](DEVICE_INVENTORY.md)：脱敏后的网络设备、服务器入口和服务基线。
3. [ESXI_BASELINE.md](ESXI_BASELINE.md)：已登录 ESXi 主机的脱敏硬件、虚拟机、存储、网络与风险基线。

## 当前状态

- 状态：`proposed`
- 建立日期：`2026-08-08`
- 已确认：项目名为 `office-network`，管理对象为办公网 MikroTik 设备。
- 下一步：确认 MikroTik 型号与 RouterOS 版本，并盘点两台 ESXi 主机的用途和虚拟机。

## 安全边界

- 不记录密码、Token、私钥、Cookie、完整配置导出或未脱敏备份。
- 管理地址、MAC、公网 IP、序列号和账号写入前必须脱敏。
- 配置变更前必须确认影响范围、备份方式和回滚方案。
