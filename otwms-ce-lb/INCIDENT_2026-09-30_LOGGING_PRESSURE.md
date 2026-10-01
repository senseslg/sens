# 2026-09-30 官网间歇性超时与日志采集器异常

## 当前结论

- **已恢复官网及日志/指标上传。** 截至柬埔寨时间 `22:08`，官网本机与公网连续返回 200；Fluent Bit 活动缓存约 132 KB，CPU 瞬时空闲 100%，日志和主机 CPU 指标均有新的云端到达记录。
- 根因链路：实例服务账号缺少日志写入权限 → Cloud Logging 返回 403 → 缓存积压、FD 耗尽及重复错误 → 单核主机资源压力。隔离积压并补齐权限后，官网与采集器同时恢复。
- 权限缺失的起始时间和多年旧缓存的全部来源尚未追溯；上述链路描述本次已验证的故障与恢复关系。
- `tms.cambodianexpress.com` 经独立 GCP LB 到独立 Tomcat VM，目前不能把 TMS/App 超时归因于 `ce-lb`。两条故障线需分别验收。
- 来源：当日 GCloud SSH、Cloud Monitoring/Logging、Cloud SQL Query Insights；下表为修复前 `21:27–21:30` 的诊断快照，后续恢复证据见下节。

## 关键证据

| 检查 | 结果 |
|---|---|
| 实际官网源站 | 使用 `--resolve www.cambodianexpress.com:443:127.0.0.1`、正常 TLS 校验；8 秒未收到响应 |
| CPU/内存 | 1 vCPU，多次 vmstat/top 空闲 CPU 为 0%；可用内存约 60–80 MB，无 Swap |
| 日志进程 | Fluent Bit PID 909，持续运行自 2025-11-10；journald 同时处理重复错误 |
| 文件描述符 | PID 909 使用 1024 个，实际 soft/hard 为 1024/4096，重复 `Too many open files` 和无法打开 chunk/自身日志 |
| 缓存 | `/var/lib/google-cloud-ops-agent/fluent-bit/buffers`：5.2 GB、2799 文件，包含多年旧 chunk |
| 日志速率 | 近 2 分钟 Fluent Bit journal 输出约 4000 行；不是仅靠累计 CPU 百分比判断 |
| 版本 | 生成配置标示 Ops Agent 2.27.0；二进制输出 Fluent Bit 2.0.9 |
| 指标采集 | `google-cloud-ops-agent-opentelemetry-collector` 为 active |
| 软件包管理 | RPM Berkeley DB 报 `DB_RUNRECOVERY`，不能将 rpm 的“未安装”当作真实包状态 |
| PHP | pool 上限 10 个 worker；历史多次 SIGKILL，尚不能仅凭 PHP 日志认定 OOM |

根盘此前采样约 54% 使用、47 GB 可用。当前瓶颈不表现为 ce-lb 磁盘写满。

## 分离 TMS/SQL 故障线

- `21:41–21:47` 后续入口对照、TMS 本机阻塞/自行恢复、Redis 指标和调试暴露风险见 [TMS 独立事故记录](../tms-server/INCIDENT_2026-09-30_INTERMITTENT_TIMEOUT.md)。
- TMS 登录入口故障时曾在 Tomcat 本机超时，LB 记录 `502/backend_timeout`；TCP 健康检查仍可显示健康。
- Cloud SQL 故障窗口磁盘约 95.44%、剩余约 57 GiB；自动扩容已开且未设容量上限，无同期重启/维护证据。
- Query Insights 19:30–20:30 显示整体负载低于 8 核容量；TMS 来源的运单统计查询平均 1.94 秒、扫描约 20 万行、调用 127 次。存在优化空间，但未证实为整体超时主因。
- TMS 根因仍需故障现场 Java 线程栈和 Tomcat 日志；当前 SSH 用户不具备对应权限。

## 已执行恢复与验收

1. 复核 PID、实际 FD 上限和二进制后，试将 soft limit 从 1024 提至 4096。处理旧缓存时 I/O 等待升高，并触发一次 Fluent Bit OOM；系统自动重启它。**该试验未解决问题，不应复用为单独修复步骤。**
2. 暂停日志子服务后，CPU 空闲恢复，官网首页约 0.6 秒返回 200。指标子服务未停止；未重启 Nginx、PHP、MySQL 或整机。
3. 将 `buffers/tail.1`、`tail.2` 完整隔离至 `/var/lib/google-cloud-ops-agent/fluent-bit/backlog-quarantine-20260930-rTBSYS/`（5.2 GB），并备份位置文件及 agent 配置。原位置数据库留在 `buffers`，避免从头重复读取。**没有删除旧日志数据；隔离内容未重新上传。**
4. 发现上传返回 `403/IAM_PERMISSION_DENIED`，缺少 `logging.logEntries.create`。实例已有 `cloud-platform` scope；绑定账号是项目默认 Compute 服务账号，被 8 台 VM 共用。经用户明确批准，为它追加 `roles/logging.logWriter` 与 `roles/monitoring.metricWriter`，保留其他绑定。变更前 IAM 备份在本机 `/private/tmp/ce-lb-recovery-20260930-MNMPWA/iam-before.json`（临时文件，可能被系统清理）。
5. 仅恢复日志子服务，并持久设置 `CPUQuota=20%`、`BlockIOReadBandwidth=/dev/sda 2M`；配置为该单元 `/etc/systemd/system/...service.d/50-CPUQuota.conf` 与 `50-BlockIOReadBandwidth.conf`。指标采集继续运行。

| 恢复验收 | 结果 |
|---|---|
| 官网 | 本机/公网六次连续 HTTP 200、正常 TLS 校验，约 0.7–1.7 秒；后续本机仍为 200，约 0.7 秒 |
| 资源 | CPU 瞬时空闲 100%；约 209 MB 可用内存；根盘仍约 54%，无 Swap |
| 日志进程 | active，FD 224；重启后实际 soft/hard 为 1024/4096，活动缓存约 132 KB |
| 云端日志 | `syslog` 于 `15:08 UTC` 产生并成功接收，新上传未再见权限错误 |
| 云端指标 | 主机 CPU 指标出现 `15:08:24 UTC` 的新数据点；不仅以进程 active 判定 |

缓冲目录与位置文件的区别见 [Google 官方排障文档](https://docs.cloud.google.com/logging/docs/agent/ops-agent/troubleshoot-run-ingest)；本次采用保留归档而非删除，不认定为特定旧版本缺陷。最小采集权限见 [官方权限说明](https://docs.cloud.google.com/logging/docs/agent/ops-agent/troubleshoot-install-startup)。

## 回滚与后续

- 停止日志子服务后才可调整隔离缓存；不能直接搬回 5.2 GB 并重启，否则可能再次 OOM。旧日志需另评估时间戳可接受性、保留期和分批恢复。
- IAM 如需回退，只移除本次追加的两项绑定，不整份覆盖项目策略；账号共用，必须核对其他 VM 的采集影响。资源限额如需撤销，仅处理本次两个专用 drop-in。
- 约 209 MB 内存余量仍低；RPM 数据库异常、软件升级、PHP 容量和历史证书治理尚未处理。需建立缓存/FD/内存及采集失败告警；短时恢复不能证明间歇故障永久消除。

## 复用评估

本次包含失败试验、共享 IAM 与缓存隔离，自动修复风险较高；仅沉淀事故及 Runbook，不生成自动修复脚本或 Skill。默认只读巡检可另行脚本化。
