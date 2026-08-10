# New CCSL Server Runbook

默认只读。收到服务器资料或访问权限后，先采集基线；未经明确授权，不重启服务、不修改配置、不切换 DNS、不写入生产数据。

> **记录规则：** Runbook 只保留已验证、可重复执行的最短步骤、判定标准和安全边界；临时输出、聊天过程和重复背景不得写入。

## 0. 优先运行项目脚本

重复执行的服务器检查优先使用 [`scripts/`](scripts/) 中经过验证的 Python 脚本，不再每次临时拼接命令：

```bash
python3 new-ccsl-server/scripts/server_baseline.py --ssh-host <user>@<host>
python3 new-ccsl-server/scripts/verify_deployment.py --ssh-host <user>@<host>
```

脚本不保存 SSH 地址或密码，通过标准输出返回脱敏结果，并使用退出码表示验证状态。详细参数、JSON 输出和安全边界见 [`scripts/README.md`](scripts/README.md)。以下手工命令用于理解检查内容、脚本故障时排查，或尚未脚本化的一次性问题。

## 1. 基础环境检查

```bash
hostnamectl
uname -a
uptime
free -h
df -h
df -i
lsblk
ip -brief address
```

记录操作系统、内核、负载、内存、磁盘和网络接口，不复制私钥、Token 或完整生产连接串。

## 2. 服务与端口盘点

```bash
systemctl --type=service --state=running
ss -lnt
ps -eo user,pid,ppid,%cpu,%mem,etime,comm --sort=-%mem
```

默认不要使用 `ps -ef`、`ps ... cmd`、`pgrep -af` 或直接输出 `/proc/<PID>/cmdline`。本服务器 Java 启动参数包含敏感配置，这些命令可能把 Token、密码或第三方凭证打印到终端和采集记录。确需辨认 Java 实例时，只提取经过允许的字段，例如端口和 JAR 路径，并在输出前过滤其他参数。

输出较长时只提炼与业务相关的服务。需要确认：

- Nginx、Node、Java、Python、PHP 或其他应用进程。
- 真实监听端口及其是否暴露公网。
- systemd、PM2、Docker 或其他进程管理方式。

## 3. Nginx 与 HTTPS

```bash
sudo nginx -t
sudo nginx -T
```

重点记录：

- `server_name`、`listen`、证书路径和 `proxy_pass`。
- HTTP 到 HTTPS 跳转。
- upstream 服务和健康状态。
- 静态资源缓存、压缩、HTTP/2 和日志格式。

读取配置时不得把证书私钥内容写入记录。

## 4. DNS 与外部入口

在明确域名后检查：

```bash
dig +short <domain> A
curl -sS -o /dev/null -L --max-time 20 \
  -w 'code=%{http_code} connect=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}\n' \
  https://<domain>/
```

DNS 变更和生产流量切换属于外部高影响操作，必须先确认授权、TTL、切换时间和回滚方案。

## 5. 应用部署基线

收到源码与部署方式后补充：

- 仓库与分支。
- 构建命令与产物目录。
- 环境变量来源，不记录真实值。
- 数据库迁移步骤。
- 服务启动、停止和健康检查。
- 日志位置与轮转方式。
- 上一版本保留和回滚命令。

### Jenkins 发布后的只读验证

优先执行：

```bash
python3 new-ccsl-server/scripts/verify_deployment.py --ssh-host <user>@<host>
```

脚本不可用时，再使用以下手工基线。

生产基线为：

- JAR：`/home/engineer/prod/backend/ccsl-prod.jar`
- 端口：`8080`
- 日志：`/home/engineer/prod/backend/ccsl-prod.log`
- Nginx 生产 upstream：`127.0.0.1:8080`

每次发布至少验证：

```bash
date '+%F %T %Z'
stat /home/engineer/prod/backend/ccsl-prod.jar
ps -C java -o user,pid,ppid,%cpu,%mem,rss,nlwp,lstart,etime,comm
curl -sS -o /dev/null --max-time 8 \
  -w 'code=%{http_code} connect=%{time_connect} ttfb=%{time_starttransfer} total=%{time_total}\n' \
  http://127.0.0.1:8080/
curl -sS -o /dev/null -L --max-time 12 \
  -w 'code=%{http_code} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total} final=%{url_effective}\n' \
  https://portal.ceccsl.com/
```

日志检查不得输出完整配置或包含业务数据的整行日志。至少统计：

- `Application run failed`
- `HikariPool-1 - Connection is not available`
- `OutOfMemoryError`
- `Address already in use`
- 发布后 `ERROR` 数量与错误类型

技术发布成功需要同时满足：产物时间与新进程启动时间一致、生产进程监听 `8080`、本机和外部入口成功响应、无启动失败/Hikari/OOM。登录、关键管理功能和数据读写仍需独立业务冒烟测试。

## 6. 数据与备份

执行迁移或升级前必须确认：

- 数据库备份已经完成且可恢复。
- 用户上传文件已经备份。
- 配置文件和定时任务已经盘点。
- 备份不与源数据放在同一故障域。
- 已明确恢复负责人和可接受恢复时间。

## 7. 上线验收

- [ ] 域名和证书正确。
- [ ] 首页、登录和关键业务流程正常。
- [ ] 服务重启后可自动恢复。
- [ ] 数据读写和文件访问正常。
- [ ] 日志无持续 5xx 或严重错误。
- [ ] CPU、内存、磁盘、带宽和响应时间正常。
- [ ] 监控与告警能够触达负责人。
- [ ] 回滚步骤已经验证或演练。

## 8. 故障处理顺序

1. 确认影响范围和开始时间。
2. 检查 DNS、TLS、Nginx、upstream 和业务日志。
3. 检查 CPU、内存、磁盘、网络和数据库。
4. 保存必要证据，避免先重启导致线索丢失。
5. 只有在影响与回滚路径明确后才执行变更。
6. 恢复后记录原因、处置、验证和防复发行动。

## 9. CCSL 连接池事故检查

出现登录超时、后台 504 或 `HikariPool-1 - Connection is not available` 时，先采集证据：

```bash
ps -C java -o user,pid,ppid,%cpu,%mem,rss,nlwp,lstart,etime,comm
ss -lntp | grep ':8080'
ss -ant | awk '$4 ~ /:8080$/ || $5 ~ /:8080$/ {print $1}' | sort | uniq -c
pgrep -f 'ccsl-prod.jar'
```

取得唯一 Java PID 后分别执行：

```bash
ps -o nlwp,pid,rss,%cpu,%mem,etime,comm -p <PID>
ls /proc/<PID>/fd | wc -l
jstack -l <PID>
```

线程栈重点搜索：

```text
RedisCache.get
waiting to lock RedisCache
CCSLCache.getCustomer
HikariPool.getConnection
```

数据库只读检查：

```sql
SHOW GLOBAL STATUS LIKE 'Threads_connected';
SHOW GLOBAL STATUS LIKE 'Threads_running';
SHOW FULL PROCESSLIST;
SHOW ENGINE INNODB STATUS\G
```

判断原则：

- 数据库连接数低、Running 少，但大量 Java 线程等待 Hikari：问题优先在应用连接持有和资源竞争。
- 大量线程等待同一 `RedisCache` 锁：检查缓存加载是否在锁内访问数据库，以及是否位于事务中。
- 不要在采集 jstack、processlist、InnoDB 和 GC 证据前直接重启，除非业务影响要求立即恢复且负责人已确认。
- 扩大 Hikari 池只能临时缓解；未解决连接持有问题前不得作为唯一修复。

## 10. 当前紧急恢复边界

现有 `deploy.sh` 会强制终止旧进程并通过 `nohup` 启动 JAR。它曾用于恢复服务，但存在以下风险：

- `kill -9` 无法执行优雅关闭。
- 普通用户可能无权终止进程或写日志。
- 没有 systemd 自动恢复、统一日志和明确健康检查。
- 脚本只重启现有 JAR，不执行拉取、构建或数据库迁移。

在完成 systemd 改造前，如确需再次使用脚本，必须先确认当前 JAR、运行用户、日志权限、事故证据已保存，并在重启后验证 `8080`、关键接口、Hikari 和数据库状态。
