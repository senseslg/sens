# Performance Analysis

## 结论摘要

2026-07-15 对 `https://www.cel-mall.com` 的只读检查发现：线上返回 `x-powered-by: Nuxt`，静态资源位于 `/_nuxt/`；被分析的本地项目 `/Users/lingang/mallgogo-ssr-app` 则是 Next.js 16。这说明当前首先要解决的是“本地与线上不是同一套构建/服务”，其次才是 Next.js 代码本身的性能。

服务器算力仍不是首要嫌疑；当前线上链路是：

```text
Browser → 3 Mbps public link → Nginx → current Nuxt service
```

如果后续正确切换到本地 Next.js 项目，请求链路才会变为：

```text
Local
Browser → localhost Next.js → local/network APIs

Server
Browser → 3 Mbps public link → Nginx → Next.js
        → RDS / Taobao / 1688 / Onebound / image sources
        → 3 Mbps public link → Browser
```

线上每个额外网络环节都会叠加延迟，图片代理还会同时消耗入站、出站和 Node.js 处理能力。

## P0：线上与本地框架不一致

已确认事实：

- `www.cel-mall.com` 与 `cel-mall.com` 均解析到目标 ECS。
- `/` 跳转到 `/en`。
- `/en` 返回 `x-powered-by: Nuxt`。
- 首页资源路径使用 `/_nuxt/`，而不是 Next.js 的 `/_next/`。

因此不能把当前线上慢完全归因于 `/Users/lingang/mallgogo-ssr-app` 的 Next.js 代码。最优先检查 Nginx `proxy_pass`、当前监听进程、部署目录和发布流程，确认是否仍在运行旧 Nuxt 商城。

## P0：线上静态资源未充分优化

只读检测结果：

- `/en` 未压缩 HTML 约 `195 KB`，gzip 后约 `37 KB`。
- HTML 中引用约 `61` 个 `/_nuxt/` 资源；其 `Content-Length` 汇总约 `1.04 MB`，但浏览器是否立即下载全部资源仍需用 Network 面板确认。
- 最大 JavaScript 文件约 `613 KB`，响应没有 `Content-Encoding`，即未使用 gzip/Brotli。
- HTTPS 协商结果为 HTTP/1.1，没有使用 HTTP/2。
- 静态资源已有 `public, immutable` 和 7 天缓存，这是正确项。

在 3 Mbps 下，单个 `613 KB` 文件的理论传输时间约 `1.6 秒`，大量独立请求在 HTTP/1.1 下还会受到连接并发限制。首次访问明显慢与这些事实一致。

## P0：切换到 Next.js 后排除 next dev

仓库提供：

- `npm run dev` → `next dev --port 3001`
- `npm run start` → `next start --port 3001`

当前域名尚未指向这份 Next.js 构建。完成服务确认或切换后，如果服务端直接使用 `npm run dev`，页面首次访问可能触发按需编译、缓存生成和开发诊断逻辑，速度会明显慢于生产构建。服务器必须是：

```text
npm ci
npm run build
npm run start
```

这只是目标状态；是否已经这样运行，需要在服务器检查进程命令。

## P0：3 Mbps 公网带宽

商城页面包含 JavaScript、CSS 和多张商品图片。3 Mbps 约等于 0.375 MB/s，多个用户或多个并发图片会共享这一带宽。

尤其是 1688 图片：

1. 浏览器请求 MallGoGo `/api/cached-image`。
2. Next.js 从阿里图片源下载图片。
3. Next.js 写入 `/tmp/mallgogo-image-cache`。
4. Next.js 再通过 ECS 公网链路把图片返回浏览器。

首次缓存未命中会同时承受上游延迟和有限下行带宽。缓存命中仍需经过 3 Mbps 出口。

## P0：SSR 等待外部 API

商品详情服务器组件会在返回 HTML 前调用 `getProductDetail()`：

- 1688 → `gw.open.1688.com`
- Taobao → `api.taobao.global`

统一 HTTP helper 设置 `cache: "no-store"`，没有统一超时。结果是：

- 每次请求都访问上游。
- 上游慢会直接增加 TTFB。
- 上游长时间不响应时，请求可能长时间占用 Node.js 资源。
- 香港 ECS 到平台 API 的延迟可能与本地网络不同。

搜索 `source=all` 会并行访问淘宝与 1688；虽然是并行，但整体完成时间取决于较慢的一方。

### 代码确认的等待机制

- `lib/services/http.ts` 对统一上游请求使用 `cache: "no-store"`，没有统一 `AbortSignal` 或超时。
- `lib/product-search.ts` 使用 `Promise.allSettled()` 同时请求淘宝和 1688；它能隔离单个失败，但仍要等待所有任务结束，一个长时间未完成的供应商会拖慢整个搜索响应。
- 商品详情 SSR 在返回页面前执行 `getProductDetail()`；上游慢会直接进入 Document TTFB。
- `/api/cached-image` 缓存未命中时先完整下载上游图片到内存，再写入本地缓存并响应用户；首次请求同时受到上游、内存处理和 ECS 出口带宽影响。

这些结论来自本地 Next.js 项目。当前线上域名运行 Nuxt，必须检查线上 Nuxt 是否采用相同供应商链路，不能直接把本地实现当成线上事实。

### 三类链路要分别判断

| 链路 | 慢时表现 | 主要优化 |
|---|---|---|
| ECS → 淘宝/1688 API | HTML 或搜索 API TTFB 高 | 超时、缓存、降级、供应商耗时日志 |
| 用户浏览器 → 淘宝/1688 图片 CDN | Document 快但图片完成慢 | 图片 CDN、缩略图、格式和用户网络 |
| 淘宝/1688 图片 → ECS → 用户 | 图片首次加载最慢并占用 ECS 出口 | OSS/CDN 持久缓存，避免应用实时中转 |

### 香港地域与 3 Mbps 的边界

香港 ECS 访问中国内地服务可能受到跨境公网路由、拥塞和供应商接入点位置影响，因此淘宝/1688 API 确实可能比开发者本地或中国内地服务器慢。但不能仅凭地域确认，必须在目标 ECS 上测量。

当前 `3 Mbps` 固定公网带宽主要约束 ECS 公网出方向。服务端发给淘宝/1688 的 API 请求通常很小，供应商返回 JSON 则主要是进入 ECS 的流量；所以提高到 10/20 Mbps 通常更直接改善 ECS 向用户发送页面、JavaScript 和图片，不会自动降低供应商接口的处理与网络等待时间。

判断接口慢在哪里，应拆分：

- DNS、TCP、TLS 已经慢：更偏向香港 ECS 到接入点的网络路径。
- DNS、TCP、TLS 快，但真实 API TTFB 高：更偏向供应商处理、限流或业务查询。
- 供应商 API 快，但 MallGoGo 接口慢：更偏向应用组合、序列化、数据库或等待其他供应商。

### 2026-07-15 本地网络基线

在当前开发 Mac 和当前网络环境执行只读测试：

| 指标 | 本地结果 |
|---|---:|
| 下行能力 | 约 `316 Mbps` |
| 上行能力 | 约 `43 Mbps` |
| 空闲延迟 | 约 `44 ms` |
| 负载响应延迟 | 约 `205 ms`，macOS 评级 Medium |
| 淘宝 API 域名基础请求 | 热 DNS 后总时间约 `0.19–0.21 s` |
| 1688 API 域名基础请求 | 热 DNS 后总时间约 `0.27–0.31 s` |

该结果证明本地到两个供应商域名的基础链路当前较快，但不能单独证明香港 ECS 较慢；还需要在 ECS 上运行相同测试做同时间段对照。

本地开发还有一个天然优势：应用 JavaScript、CSS 和 HTML 由 `localhost` 提供，不经过公网。线上用户下载这些资源则受 ECS 公网出口限制。因此本地 `316 Mbps` 下行不能与 ECS `3 Mbps` 出方向做完全对等比较，但两者足以解释大量静态资源为何在线上更容易表现出明显差异。

### 2026-07-15 香港 ECS 对照结果

用户在目标香港 ECS 上执行了相同的五轮基础请求：

| 目标 | 香港 ECS 热 DNS 总耗时 | 本地热 DNS 总耗时 | 判断 |
|---|---:|---:|---|
| `api.taobao.global` | 约 `0.17–0.21 s` | 约 `0.19–0.21 s` | 基本相同，ECS 没有明显劣势 |
| `gw.open.1688.com` | 约 `0.15–0.18 s` | 约 `0.27–0.31 s` | ECS 明显更快 |

1688 在 ECS 上的 TCP connect 约 `1–2 ms`，说明其当前接入点离阿里云香港 ECS 的网络路径非常近。淘宝首次冷 DNS 请求约 `0.42 s`，之后稳定在约 `0.17–0.21 s`，与本地表现接近。

结论：没有证据支持“香港 ECS 到淘宝/1688 基础网络效率低”。当前应降低跨境线路问题的优先级，继续优先检查静态资源出口、Nuxt/Next.js 部署不一致、真实签名 API 的平台处理时间、无超时/无缓存等待和图片中转。

本测试访问的是供应商域名根路径，只验证 DNS、TCP、TLS 与基础响应。它不能代替真实商品搜索/详情 API 的处理耗时；下一步应在应用层记录每个合法只读 API 调用的总时间和状态。

### 推荐的接口策略

- 搜索接口：设置单供应商超时，允许先返回较快平台结果；可按关键词和页码短缓存 `30–120 秒`。
- 商品详情：建议缓存 `5–15 分钟`，上游失败时返回已有 seed 或陈旧缓存。
- 图片：首次成功抓取后持久化到 OSS，并由 CDN 返回，不依赖单机 `/tmp`。
- 日志：记录 `provider`、匿名化请求类型、DNS/连接/TTFB/总耗时、状态码、缓存命中和超时，不记录 Token、签名或完整商品敏感参数。

## P1：MySQL 连接池偏小

`lib/mysql.ts` 当前配置：

```text
connectionLimit: 3
maxIdle: 1
waitForConnections: true
queueLimit: 0
```

三个连接对低流量可用，但管理后台和客户端同时加载多个 API 时，请求会等待可用连接。`queueLimit: 0` 允许队列持续增长，压力大时表现为响应越来越慢，而不是快速失败。

不能在未检查 RDS 最大连接数和查询耗时前直接把池调得很大。建议先记录连接等待和慢查询，再测试 `10` 左右的小幅提升。

## P1：没有 CDN / 对象存储卸载证据

当前服务器没有关联负载均衡，仓库也没有 CDN 或静态资产域名配置。若 `_next/static`、图片缓存和下载资源都由这台 ECS 返回，3 Mbps 会成为共享瓶颈。

适合卸载的内容：

- `/_next/static/*`
- 商品图片代理结果
- 固定图片、图标和下载资源
- 可长期缓存的公开页面资源

## P1：单机入口与进程模型未记录

仓库没有生产 Nginx、systemd 或 PM2 配置，因此无法确认：

- Nginx 是否启用 gzip/Brotli、HTTP/2 和合理缓存头。
- upstream 是否正确指向 `127.0.0.1:3001`。
- Node 是否有自动重启、日志轮转和资源限制。
- 是否只有一个 Node 进程处理所有请求。

这些属于待验证项，不能仅凭 ECS 控制台判断。

## 不是首要原因的项目

- 4 vCPU / 16 GiB：除非监控显示持续高 CPU、GC 或内存换页，否则不应先升级。
- NVMe：已安装驱动，且当前应用的主要风险更偏向网络和外部依赖。
- Ubuntu 20.04：版本需要维护，但不会单独解释“本地快、线上慢”。

## 额外安全发现

源项目的 `RUNBOOK.md` 含有一段看起来像有效 Bearer Token 的示例命令。该内容与性能无关，但不应继续保留在受版本控制文档中；建议尽快确认、轮换并从文档及 Git 历史中移除。本文不复制该值。
