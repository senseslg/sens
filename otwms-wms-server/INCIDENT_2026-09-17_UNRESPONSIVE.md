# Incident: WMS Server Unresponsive

## 结论（2026-09-18）

`wms-server` 曾在 GCP 显示 `RUNNING`，但 IAP SSH 和内网端口均超时。离线检查确认 500 GB 根分区仅余 33 MB；首次 Reset 后，XFS 日志恢复失败，系统进入 emergency mode。用户将启动盘扩至 600 GB 后，再次 Reset 正常启动；IAP SSH、CEWMS 和 `cp` 入口均已恢复。**扩容解决了本次启动和访问故障，历史大文件的保留与容量告警仍待处理。**

## 关键证据与恢复过程

| 阶段 | 已确认事实 |
|---|---|
| 失联 | `ce-lb` 连接本机 90 端口超时；22/80/90 均不可达。串口出现 OOM、CPU soft lockup；GCP 的 `RUNNING` 未反映客体健康。 |
| 恢复点 | Reset 前创建启动盘快照 `wms-server-pre-reset-20260917`，核实为 `READY`。这是运行中创建的崩溃一致性快照，会产生存储费用。 |
| 首次 Reset | 串口报告 `reserve blocks depleted`、`Failed to recover intents` 和 `Failed to mount /sysroot`；系统进入 emergency mode，SSH 仍超时。 |
| 离线检查 | 快照副本以只读方式附加到临时救援机；XFS 只读挂载显示 500 GB 已用满、仅余 33 MB，inode 使用率 87%。`xfs_repair -n` 报告断链 inode；未执行修复。 |
| 扩容与再次 Reset | 用户将原启动盘扩至 600 GB；再次 Reset 后正常启动。XFS 自动增长到 600 GB，约 500 GB 已用、101 GB 可用（84%），inode 约 1% 已用。 |
| 验收 | IAP SSH 可登录；`cewms.service` active；80/90 端口由不同 `dotnet` 进程监听，本机请求、`ce-lb` 到 90 端口及公网 `https://cp.cambodianexpress.com/` 均返回 HTTP 200。 |

恢复后 1.8 GB 内存中约 1.3 GB 可用，仍无 Swap。一次目录扫描期间 SSH 握手短暂超时，随后复查登录成功、负载低，不能据此认定故障复发。

## 容量来源与剩余风险

- `/home/daniel` 约 473 GB。经只读复核，[2026-08-17 记录](../otwms-ce-lb/INCIDENT_2026-08-17_WMS_SERVER_DISK_FULL.md)中的 `spider.log` 仍约 405 GiB，最后修改于 `2026-08-14`，检查时未被进程打开；约 55 GiB 的旧 SQL 备份、5.2 GiB 压缩文件和 1.3 GiB 旧日志仍在。`/var/log` 约 284 MB，邮件队列约 1.8 MB，不是本次主要容量来源。
- `spider.log` 的产生方式、上述文件的保留要求，以及先前 OOM/soft lockup 的触发源尚未确认。未读取文件内容，也未删除、截断或修复原盘文件系统。
- 临时救援机及磁盘副本已删除；恢复快照保留为 `READY`。快照保留周期仍需确定。

## 下一步

1. 确认历史大文件的业务归属、保留要求和可恢复副本，再决定归档或清理；未确认前不改动。
2. 建立磁盘空间、内存及 80/90 端口告警，观察 SSH 和业务入口稳定性。
3. 核实 90 端口服务名称、持久化依赖，以及快照的保留周期。

操作方法见 [RUNBOOK.md](RUNBOOK.md)。Google Cloud 的[满盘恢复指南](https://docs.cloud.google.com/compute/docs/troubleshooting/troubleshooting-disk-full-resize)说明了启动盘不可访问时的排查路径。
