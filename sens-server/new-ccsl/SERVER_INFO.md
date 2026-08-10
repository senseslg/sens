# CCSL Server Information

## SSH 连接

| 项目 | 当前值 |
|---|---|
| 公网主机 | `8.212.48.176` |
| SSH 端口 | `22` |
| 登录用户 | `sens` |
| SSH 别名 | `ccsl-new` |
| 本机私钥 | `~/.ssh/id_ed25519`（只引用，不复制） |
| 认证方式 | ED25519 公钥，已用 `BatchMode` 验证 |
| 远端主机名 | `new-ccsl` |

```bash
./bin/connect.sh
```

等价的标准 SSH 命令：

```bash
ssh -F /Users/lingang/sens/sens-server/new-ccsl/ssh_config ccsl-new
```

## 服务器基线

| 项目 | 已确认信息 |
|---|---|
| 云平台 | 阿里云 ECS |
| 操作系统 | Ubuntu 24.04.3 LTS，x86-64 |
| CPU / 内存 | 2 vCPU / 15 GiB |
| 磁盘 | 系统盘约 98 GiB；`/mnt` 约 492 GiB |
| 关键服务 | Nginx、Docker、Fail2ban |
| 进程管理 | Jenkins + 部署脚本 + `nohup`，尚未迁移到 systemd |

## CCSL 应用

| 环境 | JAR | 日志 | 端口 | 外部入口 |
|---|---|---|---|---|
| 生产 | `/home/engineer/prod/backend/ccsl-prod.jar` | `/home/engineer/prod/backend/ccsl-prod.log` | `8080` | `https://portal.ceccsl.com/`、`https://m.ceccsl.com/` |
| UAT | `/home/engineer/uat/backend/ccsl-uat.jar` | `/home/engineer/uat/backend/ccsl-uat.log` | `8081` | `https://ccsl-uat.cambodianexpress.com/`、`https://m-uat.ceccsl.com/` |

Nginx 将生产入口转发至 `127.0.0.1:8080`，将 UAT 入口转发至
`127.0.0.1:8081`。

`/actuator/health` 当前返回 `404`。健康脚本因此综合检查 JAR、Java 进程、
进程启动时间、本机 HTTP、外部 HTTPS 和以下致命日志标记：

- `Application run failed`
- `HikariPool-1 - Connection is not available`
- `OutOfMemoryError`
- `Address already in use`

技术检查通过不等于登录、订单、数据写入和第三方接口的业务验收通过。

## 2026-07-31 验证状态

- SSH 登录：`PASS`。
- 生产环境：`PASS`，`8080` 及两个生产入口正常。
- UAT 环境：`PASS`，`8081` 及两个 UAT 入口正常。
- Nginx、Docker、Fail2ban：`active`。
- 根分区使用约 28%，`/mnt` 使用约 67%，无 Swap。
- 系统提示需要重启，并有约 60 个可更新软件包；需在维护窗口评估。
- UAT 发布后日志窗口存在较多 `PersistenceException` 分类记录，未触发当前
  技术检查失败，但需要结合业务测试确认影响。

## 已知风险

- 生产和 UAT Java 端口监听所有网卡，需结合安全组和防火墙限制公网访问。
- 现有部署方式缺少 systemd 的优雅停止、自动恢复和统一日志管理。
- 生产曾发生 Hikari 连接池耗尽，应重点监控 Redis Cache 锁竞争、事务范围、
  Hikari 等待线程和 Nginx 504。
- Java 启动参数可能包含敏感配置，不得使用 `ps -ef`、`pgrep -af` 或完整
  `/proc/<PID>/cmdline` 采集命令行。
