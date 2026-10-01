# OTWMS CE LB Overview

## 目标与完成标准

- 维护 `ce-lb`、GCP `dev-lb`、`wms-db` 与 `wms-server` 的安全访问方式、运行基线、风险和变更记录。
- 明确域名入口、负载均衡、源码、构建、任务调度和管理后台部署链路。
- 重复巡检应默认只读、脱敏，并能判断 CPU、内存、磁盘和关键服务状态。

## 环境

| 项目 | 当前值 |
|---|---|
| GCP Project | `cambodian-express` |
| Zone | `asia-southeast1-a` |
| Instance | `ce-lb` |
| SSH user | `lingang` |
| OS | CentOS Linux 7，kernel `3.10.0-1160.83.1.el7.x86_64` |
| 资源 | 1 vCPU、约 1.8 GB 内存、无 Swap |
| 根磁盘 | 100 GB XFS；已用 54 GB（54%） |

关联基础设施的快速定位见 [INFRASTRUCTURE_MAP.md](INFRASTRUCTURE_MAP.md)：`job.cambodianexpress.com` 通过 GCP `dev-lb` 落到 `wms-db`，CEWMS .NET 管理后台部署在 `wms-server`。

## 2026-08-10 只读快照

- SSH 登录成功，系统已连续运行约 273 天，`systemctl` 报告系统状态为 `running`。
- 本机 `http://127.0.0.1/` 返回 HTTP 200，响应约 0.002 秒。
- 运行进程包括 Nginx `1.20.1`、PHP-FPM、MySQL、GCS Fuse、Google Ops Agent、Postfix 和 firewalld。
- MySQL 客户端版本为 `5.6.51`；未读取数据库内容或配置。
- 监听端口包括 `22`、`80`、`443`、`3306`、`20201` 和 `20202`；其中 `20201`、`20202` 属于 Google Ops Agent，`9000` 与 `25` 仅监听本机地址。
- 根分区 inode 使用率约 1%，systemd journal 占用约 88.4 MB。

以上均为采集时快照，不代表持续状态。

## 服务器作用

`ce-lb` 实际是单机多角色边缘网关与 Web 主机，不只是名称意义上的负载均衡器：

- **TLS 终止与跳转：** Nginx 处理多个域名的 80/443，主域名跳转到 `www`。
- **反向代理：** `cp`、`scm`、`api-scm`、`nacos` 等域名转发到内网服务，`ccsl` 转发到外部 HTTP 上游。
- **官网源站：** `www.cambodianexpress.com` 直接运行本机 WordPress，经 PHP-FPM `127.0.0.1:9000` 提供服务；站点目录约 2.1 GB。
- **对象存储挂载：** GCS bucket 通过 GCS Fuse 挂载到 `/TMS`，用途仍需与业务确认。
- **监控与日志：** Google Ops Agent 负责日志与指标采集。

该结构把入口、代理、官网、PHP 和数据库集中在一台 1 vCPU VM 上，形成明显单点故障和资源竞争风险。

域名路由、组件状态以及已确认事实与推断见 [SERVICE_INVENTORY.md](SERVICE_INVENTORY.md)。本机 MySQL 很可能支持 WordPress 或历史业务，但本次未读取应用或数据库配置，依赖关系仍待确认。

## SSL 状态

- **2026-09-17 已恢复：** 根域名、`www`、`cp` 的 Let's Encrypt 证书已续期至 `2026-12-16`；公网官网 TLS 验证通过，`www` 返回 HTTP 200。
- root Cron 已补充 Nginx 所在目录的 PATH，官网证书 dry-run 通过；其他历史证书的失败项尚待处理。
- 8 月的 GoDaddy 停放事故为历史事件，见 [INCIDENT_2026-08-16_DOMAIN_PARKING.md](INCIDENT_2026-08-16_DOMAIN_PARKING.md)；详细证书状态见 [SSL_INVENTORY.md](SSL_INVENTORY.md)。
- 详细域名和证书状态见 [SSL_INVENTORY.md](SSL_INVENTORY.md)。

## 当前风险与判断

- **2026-09-30 官网已恢复：** 隔离保留 5.2 GB 缓存、补齐获批的日志/指标写入权限并限制日志资源后，官网连续返回 200；日志和 CPU 指标上传已验证。细节及独立 TMS 故障边界见 [事故记录](INCIDENT_2026-09-30_LOGGING_PRESSURE.md)。
- **WMS Server 容量：** `wms-server` 已扩至 600 GB 并恢复服务，约 101 GB 可用；`/home/daniel` 历史大文件仍占约 473 GB，需确认保留要求和容量告警。
- **共享平台单点：** `wms-db` 同时承载负载均衡后端、源码、构建、XXL-JOB、数据库和多项工具服务，故障影响范围大。
- **`cp` 业务：** 证书与后端均已恢复，`ce-lb` 上游和公网入口 HTTP 200。见 [独立故障记录](../otwms-wms-server/INCIDENT_2026-09-17_UNRESPONSIVE.md)。
- **CPU：** 日志风暴处理后瞬时空闲恢复到 100%；日志子服务已有持久的 20% CPU 与 2 MB/s 读取限额，仍需持续监控。
- **内存余量低：** 恢复后可用内存约 209 MB，且无 Swap；PHP-FPM 上限 10 个 worker。直接处理旧缓存曾触发 Fluent Bit OOM，不应一次性重放。
- **系统生命周期：** CentOS 7 已进入停止常规维护的旧系统阶段，需要规划升级，不宜直接在生产实例上原地尝试。
- **数据库监听：** `3306` 显示为非 loopback 监听。尚未核对 GCP 防火墙、主机防火墙和 MySQL 授权，不能据此断言公网可访问，但必须确认暴露边界。
- **主机防火墙：** firewalld 将 `eth0` 放在 `trusted` zone 且目标为 `ACCEPT`，主机层未形成有效端口收敛；需核对 GCP 防火墙是否承担完整访问控制。
- **历史证书风险：** 官网续期链路已修复，但其他旧 lineage 仍可能使整批续期任务报错。
- **服务管理不清晰：** Nginx 进程存在，但 `systemctl is-active nginx` 返回 `unknown`；其启动、重载和恢复方式待确认。

## 决定与运维边界

- 默认仅执行只读检查；本次证书续期及 Cron PATH 变更已获用户授权并完成备份与验收。
- 重启、升级、端口调整、日志清理和数据库操作必须先确认影响、回滚与验收方式。
- 仓库不保存公网地址、密码、私钥、数据库连接串或业务数据。

## 下一步

- [ ] 在明确备份、负责人和回滚后处理 `wms-server` 的超大日志、历史 SQL 备份和高 inode 文件目录，并完成 CEWMS 恢复验证。
- [ ] 建立 `wms-db` Bitbucket/Jenkins/XXL-JOB/数据库的备份与恢复清单，确认源码到部署的映射。
- [ ] 按 [wms-server 故障记录](../otwms-wms-server/INCIDENT_2026-09-17_UNRESPONSIVE.md) 跟进容量与内存风险，并清理或修复旧证书续期项。
- [x] 恢复官网和新日志/指标上传，旧缓存完整保留；共享账号两项采集写入角色已获用户明确批准。
- [ ] 建立日志上传失败、缓存、FD、内存告警，并评估隔离缓存的保留与分批处置。
- [ ] 确认 Nginx、PHP-FPM、MySQL 和 GCS Fuse 的启动方式与业务归属。
- [ ] 核对主机 firewalld 与 GCP 防火墙，确认 `3306`、`20201`、`20202` 的允许来源。
- [ ] 评估扩容、Swap 策略和 CentOS 7 迁移方案；形成方案后再决定是否变更。
- [ ] 建立关键服务、HTTP、磁盘、内存和 CPU 的重复巡检脚本。

最近更新：`2026-09-30`
