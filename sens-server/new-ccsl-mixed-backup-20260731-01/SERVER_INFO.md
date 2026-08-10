# New CCSL Server Information

## SSH 连接

| 项目 | 当前值 |
|---|---|
| SSH 主机 | `8.212.48.176` |
| SSH 端口 | `22` |
| 登录用户 | `sens` |
| SSH 别名 | `ccsl-new`（通过本目录 `ssh_config` 使用） |
| 本机私钥 | `~/.ssh/id_ed25519`（仅引用，不复制） |
| 认证方式 | ED25519 公钥；2026-07-31 已用 `BatchMode` 验证 |
| 远端主机名 | `new-ccsl` |

登录命令：

```bash
/Users/lingang/sens/sens-server/new-ccsl/bin/connect.sh
```

等价命令：

```bash
ssh -F /Users/lingang/sens/sens-server/new-ccsl/ssh_config ccsl-new
```

如果 SSH 报主机指纹不匹配，不要关闭校验或删除 `known_hosts` 记录；先向服务器
负责人核对新指纹和服务器是否发生重装。

## 服务器基线

以下是截至 2026-07-22 的已确认基线，实时状态应运行
`bin/server-status.sh` 重新采集：

| 项目 | 信息 |
|---|---|
| 云平台 | 阿里云 ECS |
| 操作系统 | Ubuntu 24.04.3 LTS，x86-64 |
| CPU / 内存 | 2 vCPU / 14 GiB |
| 磁盘 | 系统盘约 99 GiB；`/mnt` 约 492 GiB |
| 关键服务 | Nginx、Docker、Fail2ban |
| 进程管理 | Jenkins + 部署脚本 + `nohup`，尚未迁移到 systemd |

## CCSL 环境

| 环境 | JAR | 日志 | 本机端口 | 外部入口 |
|---|---|---|---|---|
| 生产 | `/home/engineer/prod/backend/ccsl-prod.jar` | `/home/engineer/prod/backend/ccsl-prod.log` | `8080` | `https://portal.ceccsl.com/`、`https://m.ceccsl.com/` |
| UAT | `/home/engineer/uat/backend/ccsl-uat.jar` | `/home/engineer/uat/backend/ccsl-uat.log` | `8081` | `https://ccsl-uat.cambodianexpress.com/`、`https://m-uat.ceccsl.com/` |

Nginx 将生产域名转发至 `127.0.0.1:8080`，将 UAT 域名转发至
`127.0.0.1:8081`。两个 Java 端口在 2026-07-31 的只读探测中均处于监听状态。

当前 `/actuator/health` 返回 `404`，因此健康脚本综合验证 JAR、进程启动时间、
监听端口、本机 HTTP、外部 HTTPS 和选定的致命日志标记。技术检查通过不代表
登录、订单、数据写入或第三方接口的业务验收已经完成。

## 日常操作

```bash
# SSH 和身份
./bin/check-ssh.sh

# 系统资源、服务、监听端口、脱敏 Java 摘要
./bin/server-status.sh

# 分环境发布/健康验证
./bin/health-check.sh prod
./bin/health-check.sh uat
```

## 2026-07-31 验证结果

- SSH 公钥登录：`PASS`，主机名和远端用户均符合预期。
- 生产环境：`PASS`，JAR、Java 进程、`8080`、本机 HTTP 和两个生产 HTTPS
  入口均通过；选定的启动失败、Hikari、OOM、端口占用标记均为 `0`。
- UAT 环境：`PASS`，JAR、Java 进程、`8081`、本机 HTTP 和两个 UAT HTTPS
  入口均通过；选定的四类致命标记均为 `0`。
- Nginx、Docker、Fail2ban：`active`。
- 系统要求重启，存在约 60 个可更新软件包；应在维护窗口评估，不由巡检脚本
  自动处理。
- UAT 发布后日志窗口仍有较多 `PersistenceException` 分类记录。它没有触发
  当前技术健康检查失败，但应结合业务测试确认影响。

发生 504、Hikari 超时或大面积接口超时时，先保存证据，再考虑重启。不要使用
`ps -ef`、`pgrep -af` 或输出完整 `/proc/<PID>/cmdline`，因为 Java 启动参数
可能包含敏感配置。

## 已知风险

- 生产和 UAT Java 当前监听所有网卡，需要结合安全组与防火墙控制公网访问。
- 现有部署脚本可能使用强制终止，缺少 systemd 的优雅停止和自动恢复。
- 生产曾发生 Hikari 连接池耗尽，重点关注 Redis Cache 锁竞争、事务范围、
  Hikari 等待线程及 Nginx 504。
- Java 启动参数存在敏感值风险；不要采集或传播完整命令行。
