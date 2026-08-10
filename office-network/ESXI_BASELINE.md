# ESXi Host Baseline

- 采集日期：`2026-08-08`
- 采集方式：ESXi Host Client 只读页面
- 主机代号：`esxi-02`
- 状态：在线，未连接 vCenter

## 当前结论

- 硬件：Dell PowerEdge R740，Intel Xeon Silver 4110，约 64 GB 内存。
- 系统：VMware ESXi 6.7 Update 1，Build 10302608。
- 运行时间：约 384 天，当前 CPU 约 9%、内存约 53%、存储约 74%。
- 工作负载：登记 3 台 Windows Server 2016 虚拟机；File Server 正在使用资源，Exchange Server 2016 与 PDC 当前资源显示为零，实际电源状态待确认。
- 网络：管理和虚拟机网络共用 `vSwitch0`，VLAN ID 为 `0`；仅 1 个物理网口以 1 Gbps 全双工连接，另外 3 个网口链路断开。

## 存储

| 数据存储 | 类型 | 容量 | 可用 |
|---|---|---:|---:|
| `datastore1` | VMFS6 | 550.75 GB | 522.92 GB |
| `Data` | VMFS6 | 7.28 TB | 1.54 TB |

## 虚拟机

| 角色 | 客户机系统 | 已用空间 | 当前观察 |
|---|---|---:|---|
| Exchange Server 2016 | Windows Server 2016 64-bit | 747.46 GB | CPU/内存显示为零，电源状态待确认 |
| PDC | Windows Server 2016 64-bit | 2.82 TB | CPU/内存显示为零，电源状态待确认 |
| File Server | Windows Server 2016 64-bit | 2.03 TB | 正在使用约 32 GB 内存 |

## 风险与判断

- **高：版本停止支持。** ESXi 6.7 已于 `2022-10-15` 结束常规支持，当前版本还停留在 Update 1；需要先核对 Dell 兼容性、许可证、备份和升级路径。
- **高：单链路。** 当前仅 1 个 1 Gbps 物理网口承载管理和虚拟机网络，链路或交换机端口故障会造成整机网络中断。
- **中：长期未维护。** 连续运行约 384 天，需确认补丁、固件、硬件告警和维护窗口，但不能在未验证虚拟机备份前重启。
- **中：存储使用率。** 总体存储约 74% 已用，`Data` 剩余约 1.54 TB；需确认增长速度、快照和备份占用。
- **中：默认主机名。** 主机仍使用 `localhost.localdomain`，不利于资产识别、证书和集中管理。
- **待确认：工作负载状态。** Exchange 和 PDC 的资源显示为零，推断可能已关机，但需进入各虚拟机摘要验证。

## 下一步

- 只读核对 3 台虚拟机的电源状态、配置和快照。
- 检查硬件健康、磁盘/RAID 状态和 ESXi 系统日志。
- 确认虚拟机与 ESXi 配置备份是否可恢复。
- 评估增加第二条物理链路及管理/业务网络隔离。
- 制定升级方案和维护窗口；未完成备份验证前不升级或重启。

## 来源

- 本机 ESXi Host Client，读取时间 `2026-08-08`。
- [Broadcom：vSphere 6.5/6.7 结束常规支持](https://knowledge.broadcom.com/external/article/326984/)
