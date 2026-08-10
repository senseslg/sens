# MallGoGo Server Performance Overview

## 目标

- 找出 `/Users/lingang/mallgogo-ssr-app` 本地运行快、部署到服务器后变慢的原因。
- 建立可重复的服务器性能检查方法。
- 区分网络、Next.js、外部 API、MySQL、图片和系统资源问题。
- 以测量结果决定优化顺序，避免直接升级 CPU 或盲目改代码。

## 应用基线

- 源码：`/Users/lingang/mallgogo-ssr-app`
- 线上域名：`https://www.cel-mall.com`
- Framework：Next.js 16 App Router
- React：19
- 服务端口：`3001`
- 生产脚本：`next start --port 3001`
- 开发脚本：`next dev --port 3001`
- 数据库：MySQL，`mysql2/promise` 连接池
- 外部服务：淘宝、1688、Onebound、Chatwoot 与外部图片源

## 主要请求链路

```text
Browser
  ↓ 3 Mbps ECS public bandwidth
Nginx
  ↓ localhost:3001（待确认实际配置）
Next.js
  ├─ MySQL / RDS
  ├─ Taobao API
  ├─ 1688 API
  ├─ Onebound API
  ├─ Chatwoot
  └─ 1688 image proxy + local temp cache
```

## 已确认的代码特征

- `lib/services/http.ts` 对外部 API 请求统一使用 `cache: "no-store"`。
- `/api/search` 同时请求 1688 与淘宝，并等待两个请求完成或失败。
- 商品详情页在 SSR 阶段调用上游详情 API，首字节时间会受上游影响。
- 外部请求没有统一超时或 `AbortSignal`，上游卡顿可能长时间占住请求。
- 1688 图片通过 `/api/cached-image` 下载到系统临时目录，再由本机返回给浏览器。
- 图片缓存有效期 3 天，但首次请求仍需要“上游下载 + ECS 下行”。
- MySQL 池配置为 `connectionLimit: 3`、`maxIdle: 1`。
- 仓库没有 Nginx、systemd、PM2 或服务器部署配置，无法从代码确认线上进程模式。

## 当前判断

### 高概率

1. 线上实际是 Nuxt，而本地项目是 Next.js 16；Nginx 可能仍指向旧服务或错误部署目录。
2. `3 Mbps` 公网带宽限制静态资源和图片吞吐。
3. Nuxt 首页的大型 JavaScript 未压缩，且 HTTP/1.1 需要处理大量资源请求。
4. 若切换到本地 Next.js 项目，SSR 与 API 路由仍会等待跨网的淘宝、1688、Onebound 或 RDS。
5. Next.js 项目的 1688 图片中转会让有限带宽承受额外压力。

### 中概率

1. MySQL 三连接池在多请求时排队。
2. 查询缺少索引或单页并发多个数据库 API。
3. 单个 Node 进程、日志或磁盘 I/O 在高并发下成为瓶颈。

### 低概率或暂未发现证据

- ECS 的 4 核 16 GiB 规格不足。
- 香港 ECS 到淘宝/1688 的基础网络链路慢；实测淘宝与本地相近，1688 比本地更快。
- Ubuntu 20.04 本身导致明显变慢。
- NVMe 驱动或磁盘设备数量是首要原因。

## 尚缺的关键事实

- Nginx Server Block、实际 upstream 和当前 Nuxt 部署目录。
- 本地 Next.js 项目是否曾部署，以及部署后实际由哪个进程监听。
- 线上启动命令与进程管理方式。
- 页面慢在 TTFB、JS、图片、API 还是数据库。
- ECS CPU、内存、负载、磁盘等待和网络出入带宽曲线。
- ECS 到 MySQL、淘宝、1688 和 Onebound 的实际延迟。
