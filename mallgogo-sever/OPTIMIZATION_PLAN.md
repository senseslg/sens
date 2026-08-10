# Optimization Plan

按“最快验证、最高收益、最低风险”排序。每一步都应测量前后结果。

## Phase 0：当天确认

### 1. 先解决 Nuxt / Next.js 部署不一致

- `www.cel-mall.com` 当前明确运行 Nuxt，而本地目标项目是 Next.js 16。
- 检查 Nginx upstream、Nuxt/Next 进程、部署目录和服务端口。
- 明确是要继续优化当前 Nuxt 站点，还是将域名切换到新 Next.js 项目。
- 切换前先在独立端口或测试域名验收，避免直接影响线上。

### 2. 确认生产启动模式

- 必须使用 `npm run build` 后的 `npm run start`。
- 不在生产长期运行 `npm run dev`。
- 为进程配置 systemd 或受控的进程管理器、自动重启和日志轮转。

### 3. 核对真实域名和 Nginx 配置

- 记录 `server_name`、`proxy_pass` 和 TLS 入口。
- 域名已确认为 `www.cel-mall.com`；记录对应 Server Block 和 upstream。
- 从服务器内外分别测量同一路由。

### 4. 验证带宽瓶颈

- 在访问慢时查看公网出带宽是否贴近 3 Mbps。
- 建议先临时提高到 10 Mbps 做 A/B 测试；无 CDN 的短期正式配置可从 20 Mbps 起步。
- 具体容量、计算依据和扩容标准见 [BANDWIDTH_PLAN.md](BANDWIDTH_PLAN.md)。
- 如果带宽提升后页面明显改善，优先建设 CDN，而不是升级 CPU。

## Phase 1：高收益改进

### 1. CDN / OSS 卸载静态资源和图片

- 将固定资源和可缓存图片放到 OSS + CDN。
- 当前 Nuxt 站点为 `/_nuxt/*`，未来 Next.js 为 `/_next/static/*`；两者都应设置长期不可变缓存并交给 CDN。
- 避免让 1688 图片长期由 Node.js + 3 Mbps ECS 中转。
- 如必须代理图片，可将首次抓取结果持久化到对象存储并由 CDN 返回。

### 2. 给外部 API 增加超时、缓存和降级

- `fetch` 增加明确超时。
- 搜索结果和商品详情按业务容忍度设置短期缓存。
- 上游超时时优先返回已有 seed、陈旧缓存或部分结果。
- 为 Taobao、1688、Onebound 分别记录耗时和错误率。

### 3. 避免阻塞首屏 SSR

- 商品详情可先使用搜索结果 seed 渲染首屏，再异步刷新完整详情。
- 或对详情结果使用服务端缓存，避免每次 SSR 都请求上游。
- 需要在 SEO、数据新鲜度和首屏速度之间明确取舍。

### 4. 优化 Nginx

验证并配置：

- gzip 或 Brotli。
- HTTP/2 或更高协议能力。
- `/_nuxt` 与 `/_next/static` 的长期缓存。
- upstream keepalive、合理超时和响应时间日志。
- 静态文件优先由 Nginx/CDN 返回，而不是进入 Node.js。

## Phase 2：数据库与并发

### 1. 调整 MySQL 池

- 先测连接等待、RDS 最大连接数和慢查询。
- 在证据支持下，将 `connectionLimit` 从 3 小幅提高到 10 左右做压测。
- 设置合理队列和请求超时，避免无限等待。

### 2. 检查查询与索引

- 对慢页面逐条记录 SQL 时间。
- 使用 EXPLAIN 检查过滤、排序和 JOIN。
- 优先修复全表扫描和 N+1 查询。

### 3. 进程与容量

- 只有 CPU 确实成为瓶颈后，才评估多进程或横向扩容。
- 多进程会导致内存缓存和 `/tmp` 图片缓存各自独立，需先外置缓存。

## Phase 3：稳定性、安全与运维

### 1. 建立性能可观测性

- Nginx access log 增加 `$request_time` 与 `$upstream_response_time`。
- 分别记录 Nuxt/Next SSR、MySQL、淘宝、1688 与 Onebound 的匿名化耗时和错误率。
- 为 CPU、内存、磁盘、公网出口、5xx、P95 TTFB 和进程存活建立监控与告警。
- 使用同一组首页、搜索和详情路由建立发布前后基线。

### 2. 完善应用可靠性

- 外部 API 设置明确连接和总超时、有限重试、熔断与降级。
- 使用 systemd 或受控进程管理器管理生产进程，配置自动恢复、日志轮转和健康检查。
- 发布采用独立端口或测试域名验证，再切换 Nginx upstream，并保留可快速回滚的上一版本。

### 3. 升级系统与入口安全

- Ubuntu 20.04 已结束标准支持；短期确认是否启用 Ubuntu Pro / ESM，长期计划迁移到受标准支持的 LTS。
- 升级并维护 Nginx、OpenSSL、Node.js 运行时及依赖安全补丁。
- 轮换源项目文档中暴露的疑似 Bearer Token，并清理文档和 Git 历史中的凭证。
- 收紧安全组，仅开放 80/443；应用端口只监听本机或仅允许 Nginx 访问。
- 配置 TLS、请求速率限制、上传大小限制、基础 WAF/防护和自动备份恢复演练。

## 验收指标

建议为典型页面建立基线：

| 页面/接口 | 当前 | 第一阶段目标 |
|---|---|---|
| 首页 Document TTFB | 待测 | 同地区客户端 < 500 ms |
| 商品搜索 API | 待测 | P95 < 2 s，超时可降级 |
| 商品详情 Document TTFB | 待测 | 缓存命中 < 800 ms |
| 静态资源 | 待测 | CDN 命中，避免 ECS 3 Mbps 成为瓶颈 |
| MySQL 简单查询 | 待测 | 服务端执行与网络耗时可分别观察 |

这些目标是首版建议，不是已确认 SLA；应根据实际用户地区和上游能力调整。

## 2026-07-15 优先验收项

1. 域名响应框架与目标部署一致，不再出现“本地 Next.js、线上 Nuxt”。
2. 最大 JavaScript 文件启用 gzip/Brotli。
3. HTTPS 启用 HTTP/2。
4. 浏览器首次访问的 JS/CSS/图片传输量和完成时间有明确基线。
5. 公网出带宽不持续贴近 3 Mbps；若仍贴顶，再实施 CDN 或提升带宽 A/B 测试。
