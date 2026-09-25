# WMS Server Runbook

## 登录与只读检查

实例位于 `cambodian-express` / `asia-southeast1-a`，无公网 IP；使用 IAP：

```bash
gcloud compute ssh wms-server --project=cambodian-express --zone=asia-southeast1-a --tunnel-through-iap
```

登录后先确认资源与端口。本机 CentOS 7 已验证有 `netstat`，不能假定有 `ss`：

```bash
uptime
free -h
df -hT /
df -ih /
systemctl is-active cewms.service
sudo netstat -ltnp
```

分别对 80/90 端口做短超时 HTTP 检查，再从 `ce-lb` 按现行 Nginx 上游配置检查 90 端口，最后验证公网 `cp` HTTPS。不要把 HTTP 200 单独当成业务全流程通过。

## SSH 不通或实例无法启动

1. 核对实例与启动盘的 GCP 状态、容量；`RUNNING` 不代表客体系统健康。
2. 读取串口 1 最近输出，区分 OOM、CPU soft lockup、XFS 挂载失败和正常启动。不要将含业务日志或 SSH 公钥的原始输出整份复制到仓库。
3. 从 `ce-lb` 短超时探测 22/80/90，并对照 Nginx 错误是连接超时还是响应超时。
4. 变更前核实恢复点、业务影响与授权。2026-09-17 的故障中，先建快照、Reset 后发现 XFS 根分区无法挂载；只读救援检查确认 500 GB 满盘。用户扩至 600 GB 后再次 Reset，XFS 自动增长并恢复启动。见 [事故记录](INCIDENT_2026-09-17_UNRESPONSIVE.md)。

`gcloud compute ssh --troubleshoot` 可能启用 API 并创建连通性测试，不属于纯只读检查。实例 Reset 是强制重启；未确认恢复点及影响前不要重复尝试。

## 恢复验收

- SSH 登录成功；XFS、inode、内存有余量，负载稳定。
- 80/90 端口各自的服务状态和本机 HTTP 响应已确认。
- `ce-lb` 到后端及公网 `cp` 入口响应；继续核对 CEWMS 的实际业务功能。
- 清理临时救援资源，记录保留的快照、容量风险和告警待办。

本 Runbook 是检查与验收方法，不授权重启、扩容或清理生产文件。
