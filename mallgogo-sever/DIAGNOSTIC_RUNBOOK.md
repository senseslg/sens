# Performance Diagnostic Runbook

默认只读。先收集数据，不重启服务、不改安全组、不升级实例。

## 1. 确认真实入口

已确认域名为 `www.cel-mall.com`。仍需补充：

- Nginx Server Block 文件。
- upstream 地址。
- TLS/CDN/负载均衡路径。

在服务器检查：

```bash
sudo nginx -T | grep -nE 'server_name|proxy_pass|listen'
```

还要确认当前框架和服务目录：

```bash
ps -ef | grep -Ei '[n]uxt|[n]itro|[n]ext|[n]ode'
sudo nginx -T | grep -nE 'cel-mall|proxy_pass|root'
```

判定：线上响应为 Nuxt。如果目标是部署 `/Users/lingang/mallgogo-ssr-app`，但 upstream 仍指向 Nuxt，则先修正部署与流量切换，不应继续把两套应用的性能混在一起比较。

## 2. 确认生产启动方式

```bash
ps -ef | grep -E '[n]ext (dev|start)|[n]ode'
systemctl --type=service --state=running | grep -Ei 'mallgogo|next|node'
pm2 list
```

判定：

- 出现 `next dev`：优先修正为 build + start。
- 出现 `next start --port 3001`：启动模式正确，继续检查其他层。
- 没有进程管理器：记录当前启动、重启和日志方式。

## 3. 分层测量响应时间

### 本机直连应用服务

```bash
curl -sS -o /dev/null -w 'connect=%{time_connect} ttfb=%{time_starttransfer} total=%{time_total}\n' http://127.0.0.1:<actual-port>/
```

### 经 Nginx 本机入口

```bash
curl -sS -o /dev/null -H 'Host: www.cel-mall.com' -w 'connect=%{time_connect} ttfb=%{time_starttransfer} total=%{time_total}\n' http://127.0.0.1/
```

### 客户端访问真实 HTTPS

```bash
curl -sS --compressed -o /dev/null -w 'http=%{http_version} dns=%{time_namelookup} connect=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total} bytes=%{size_download}\n' https://www.cel-mall.com/en
```

解释：

- localhost 也慢：Next.js、API、数据库或主机资源问题。
- localhost 快、Nginx 慢：代理配置问题。
- 服务器内快、外部慢：公网带宽、TLS、DNS、CDN或客户端距离问题。
- HTML TTFB 快、页面完成慢：JS、CSS、图片或浏览器请求瀑布问题。

## 4. 检查主机资源

```bash
uptime
free -h
vmstat 1 10
df -h
df -i
iostat -xz 1 10
```

重点看：

- load average 是否持续高于 CPU 核数。
- swap 是否持续使用。
- `wa` / I/O await 是否高。
- 磁盘或 inode 是否接近满载。

## 5. 检查 3 Mbps 带宽是否打满

优先看阿里云监控的公网出方向带宽。如果访问慢时接近 3 Mbps，基本可以确认带宽瓶颈。

服务器可辅助观察：

```bash
sar -n DEV 1 10
```

记录访问慢时的并发数、带宽峰值和持续时间。

## 6. 测量外部依赖

对不需要密钥的主机只测连接/TLS，不把凭证写进命令记录：

```bash
curl -sS -o /dev/null -w 'connect=%{time_connect} tls=%{time_appconnect} total=%{time_total}\n' https://api.taobao.global/
curl -sS -o /dev/null -w 'connect=%{time_connect} tls=%{time_appconnect} total=%{time_total}\n' https://gw.open.1688.com/
```

建议在 ECS 上连续执行多次并记录分项：

```bash
curl -sS -o /dev/null --connect-timeout 3 --max-time 10 -w 'dns=%{time_namelookup} connect=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}\n' https://api.taobao.global/
curl -sS -o /dev/null --connect-timeout 3 --max-time 10 -w 'dns=%{time_namelookup} connect=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer} total=%{time_total}\n' https://gw.open.1688.com/
```

根路径即使返回 4xx，也仍可用于观察 DNS/TCP/TLS 基础链路；供应商真实处理耗时必须通过合法、只读的实际 API 调用记录。

真实 API 调用应在应用日志中记录匿名化耗时，不输出 Token、签名和完整查询串。

至少连续采集正常与高峰期数据，并分别统计淘宝、1688、Onebound 的 P50、P95、超时率和错误率。判断时区分：

- TCP/TLS 很快、API 总时间慢：供应商处理或接口参数对应的业务查询慢。
- ECS 调用慢、本地调用快：香港 ECS 到供应商的线路或出口路径值得重点排查。
- 两处都慢：更可能是供应商接口本身、限流或调用方式问题。
- API 快但页面慢：继续检查 SSR 组合逻辑、静态资源、图片和浏览器渲染。

本地 2026-07-15 基线可用于首轮对比：淘宝基础请求约 `0.19–0.21 s`，1688 约 `0.27–0.31 s`。ECS 测试必须使用相同 URL、相同次数和相近时间段；如果 ECS 的连接、TLS 或总时间持续显著高于该范围，再进一步检查路由、丢包和 BGP 线路。

已取得的香港 ECS 对照值：淘宝约 `0.17–0.21 s`，1688 约 `0.15–0.18 s`。基础链路已通过首轮检查，不需要优先购买 BGP 精品线路或迁移地域；后续重点记录真实签名 API 的业务处理耗时。

## 7. 测量 MySQL

需要记录：

- ECS 到 RDS 的连接时间。
- `SELECT 1` 时间。
- 具体慢页面对应 SQL 的执行时间与 EXPLAIN。
- RDS 当前连接数、最大连接数和慢查询。

涉及真实库结构和值时，先走安全数据库诊断流程；默认只读并使用窄查询。

## 8. 浏览器 Network 检查

至少记录：

- Document TTFB。
- JS/CSS 总传输大小。
- 最大 JS 是否有 gzip/Brotli，以及协议是否为 HTTP/2。
- 最慢的 10 个请求。
- 图片是从 Alicdn 直连，还是 `/api/cached-image` 中转。
- 是否大量出现 `MISS`、重复下载或无缓存。

## 诊断结果模板

| 层级 | 指标 | 结果 | 判断 |
|---|---|---|---|
| Next localhost | TTFB / total | 待测 | 待确认 |
| Nginx localhost | TTFB / total | 待测 | 待确认 |
| Public HTTPS | TTFB / total | 待测 | 待确认 |
| Public bandwidth | peak Mbps | 待测 | 待确认 |
| CPU / memory | peak / swap | 待测 | 待确认 |
| MySQL | connect / query | 待测 | 待确认 |
| Taobao / 1688 | API latency | 待测 | 待确认 |
