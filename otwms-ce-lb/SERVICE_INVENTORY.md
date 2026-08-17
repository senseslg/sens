# CE LB Service Inventory

## 当前结论

`ce-lb` 是单机七层入口、反向代理和官网源站。Nginx 为每个域名转发到单一目标，未发现多后端轮询配置，因此它更接近“边缘反向代理网关”，不具备传统高可用负载均衡的冗余。

本文件只记录 `ce-lb`；跨 `dev-lb`、`wms-db` 和 `wms-server` 的完整关系见 [INFRASTRUCTURE_MAP.md](INFRASTRUCTURE_MAP.md)。

## 请求链路

| 入口 | 当前处理方式 | 后端类型 |
|---|---|---|
| `cambodianexpress.com` | HTTP/HTTPS 跳转到 `www` | Nginx 301 |
| `www.cambodianexpress.com` | 本机直接提供官网 | `/www/wordpress` → PHP-FPM `127.0.0.1:9000` |
| `cp.cambodianexpress.com` | Nginx 反向代理 | 单个内网 HTTP 服务 |
| `scm.cambodianexpress.com` | Nginx 反向代理 | 单个内网 HTTP 服务 |
| `api-scm.cambodianexpress.com` | Nginx 反向代理 | 单个内网 HTTP 服务 |
| `nacos.cambodianexpress.com` | Nginx 反向代理 | 单个内网 Nacos 服务 |
| `mp-api.ssl-global.cn` | Nginx 反向代理 | 单个内网 HTTP 服务 |
| `ccsl.cambodianexpress.com` | Nginx 反向代理，仅配置 HTTP | 单个外部 HTTP 上游 |

内网和外部上游地址不写入仓库；需要操作时以服务器当前 Nginx 配置为准。

## 服务组件

| 组件 | 采集时状态 | 作用与说明 |
|---|---|---|
| Nginx `1.20.1` | master/worker 正在运行；配置测试通过 | 监听 80/443，TLS 终止、跳转、静态文件、PHP FastCGI 和反向代理 |
| WordPress | `/www/wordpress` 约 2.1 GB；官网返回 HTTP 200 | `www` 官网源站 |
| PHP-FPM | master 与多个 `www` pool worker 正在运行 | 本机监听 `127.0.0.1:9000`；响应头显示 PHP `7.2.34` |
| MySQL `5.6.51` | `mysqld.service` 正在运行 | 监听 `3306` 非 loopback；未读取数据库内容或 WordPress 配置 |
| GCS Fuse | 进程正在运行，挂载到 `/TMS` | 对象存储文件挂载；当前业务用途待确认 |
| Google Ops Agent | 日志与指标组件正在运行 | `20201` 为 collector，`20202` 为 Fluent Bit |
| Postfix | 正在运行 | SMTP 25 仅监听 loopback |
| firewalld | 正在运行 | `eth0` 位于 `trusted` zone，主机层接受全部流量 |

## 已确认事实与推断

### 已确认

- 主域名跳转到 `www`，`www` 由本机 WordPress/PHP-FPM 返回内容。
- Nginx 各代理域名当前只配置一个上游目标。
- MySQL 与 WordPress 同机运行，但 MySQL 监听范围不是 loopback-only。
- Nginx 未由可识别的 `nginx.service` 管理；进程存在且配置测试成功，实际启动方式待确认。

### 推断

- 本机 MySQL 很可能为 WordPress 或历史业务提供数据库，但本次未读取 `wp-config.php` 或数据库配置，不能视为已确认依赖。
- `/TMS` 可能用于应用包或业务静态文件；Nginx 配置中仅看到历史注释，实际消费者待确认。
- 实例名包含 `lb`，但当前 Nginx 配置没有多后端负载均衡证据，主要作用应是域名入口和反向代理。

## 架构风险

- 单台 VM 同时承载 TLS、反向代理、WordPress、PHP、MySQL、对象存储挂载与监控，任一主机故障会影响多个入口。
- 1 vCPU 已观察到持续满载，PHP、MySQL、journald 和采集组件共享有限资源。
- 约 1.8 GB 内存且无 Swap，可用内存约 230 MB，突发流量或日志异常可能放大故障。
- CentOS 7、PHP 7.2 和 MySQL 5.6 均属于旧版本栈，应以迁移替代高风险原地升级。
- 主机防火墙未收敛端口；必须确认 GCP 防火墙是否限制 SSH、MySQL 和 Ops Agent 监听端口。

最近验证：`2026-08-10`，仅执行只读检查。
