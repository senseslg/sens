# OTWMS CE LB Overview

## 目标与完成标准

- 维护 GCP 实例 `ce-lb` 的安全访问方式、运行基线、风险和变更记录。
- 明确该实例承载的业务、服务启动方式、网络入口、监控和恢复流程。
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
- **官网源站：** `www.cambodianexpress.com` 直接运行本机 WordPress，经 PHP-FPM `127.0.0.1:9000` 和本机 MySQL 提供服务；站点目录约 2.1 GB。
- **对象存储挂载：** GCS bucket 通过 GCS Fuse 挂载到 `/TMS`，用途仍需与业务确认。
- **监控与日志：** Google Ops Agent 负责日志与指标采集。

该结构把入口、代理、官网、PHP 和数据库集中在一台 1 vCPU VM 上，形成明显单点故障和资源竞争风险。

## SSL 状态

- `cambodianexpress.com` 与 `www.cambodianexpress.com` 实际 SNI 证书域名匹配，均为 Let's Encrypt 签发，有效至 `2026-09-13`。
- `cp.cambodianexpress.com` 证书同日到期；`api-scm`、`scm` 及部分共享证书已经过期。
- root Cron 每日执行 Certbot renew；systemd renew timer 未启用。
- 详细域名和证书状态见 [SSL_INVENTORY.md](SSL_INVENTORY.md)。

## 当前风险与判断

- **CPU 高负载：** 两轮采样中 1 vCPU 均无空闲，负载约 3.7–4.1；第二轮 `systemd-journald` 占用约 82% CPU。需要继续定位日志产生源，当前不能仅凭短时采样认定永久根因。
- **内存余量低：** 可用内存约 230 MB，且无 Swap；多个 PHP-FPM worker 各占约 80–110 MB，存在突发流量下的内存压力。
- **系统生命周期：** CentOS 7 已进入停止常规维护的旧系统阶段，需要规划升级，不宜直接在生产实例上原地尝试。
- **数据库监听：** `3306` 显示为非 loopback 监听。尚未核对 GCP 防火墙、主机防火墙和 MySQL 授权，不能据此断言公网可访问，但必须确认暴露边界。
- **主机防火墙：** firewalld 将 `eth0` 放在 `trusted` zone 且目标为 `ACCEPT`，主机层未形成有效端口收敛；需核对 GCP 防火墙是否承担完整访问控制。
- **证书风险：** 三张当前有效证书将在 `2026-09-13` 到期，另有多张生效配置引用的过期证书；必须验证自动续期并处置废弃域名。
- **服务管理不清晰：** Nginx 进程存在，但 `systemctl is-active nginx` 返回 `unknown`；其启动、重载和恢复方式待确认。

## 决定与运维边界

- 当前仅执行只读检查，不修改服务、配置、数据库、防火墙或日志。
- 重启、升级、端口调整、日志清理和数据库操作必须先确认影响、回滚与验收方式。
- 仓库不保存公网地址、密码、私钥、数据库连接串或业务数据。

## 下一步

- [ ] 只读确认 `systemd-journald` 的高 CPU 来源、日志速率与异常日志单元。
- [ ] 验证主域名、`www`、`cp` 的 Certbot 续期，并处理仍在配置中的过期证书。
- [ ] 确认 Nginx、PHP-FPM、MySQL 和 GCS Fuse 的启动方式与业务归属。
- [ ] 核对主机 firewalld 与 GCP 防火墙，确认 `3306`、`20201`、`20202` 的允许来源。
- [ ] 评估扩容、Swap 策略和 CentOS 7 迁移方案；形成方案后再决定是否变更。
- [ ] 建立关键服务、HTTP、磁盘、内存和 CPU 的重复巡检脚本。

最近更新：`2026-08-10`
