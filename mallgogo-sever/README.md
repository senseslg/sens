# mallgogo-sever

MallGoGo SSR 应用的服务器部署与性能诊断子项目。目录名称按创建要求保留为 `mallgogo-sever`。

## 阅读顺序

1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：项目范围、应用架构和当前结论。
2. [SERVER_INVENTORY.md](SERVER_INVENTORY.md)：ECS 配置与已确认的入口状态。
3. [PERFORMANCE_ANALYSIS.md](PERFORMANCE_ANALYSIS.md)：本地快、服务端慢的原因分析。
4. [DIAGNOSTIC_RUNBOOK.md](DIAGNOSTIC_RUNBOOK.md)：服务端验证命令与判定方法。
5. [OPTIMIZATION_PLAN.md](OPTIMIZATION_PLAN.md)：按优先级实施的优化方案。
6. [BANDWIDTH_PLAN.md](BANDWIDTH_PLAN.md)：公网带宽容量建议、A/B 测试和扩容标准。

## 当前结论

- 线上域名为 `www.cel-mall.com`，裸域名与 `www` 均解析到目标 ECS。
- 线上响应明确显示 `x-powered-by: Nuxt`，资源路径为 `/_nuxt/`；本地待部署项目则是 Next.js 16，二者当前并非同一构建产物。
- `4 vCPU / 16 GiB` 对当前应用不是明显短板。
- `3 Mbps` 固定公网带宽是商城首屏与图片加载的高概率瓶颈。
- 线上最大首页 JavaScript 约 `613 KB`，未启用 gzip/Brotli；HTTPS 仍协商为 HTTP/1.1。
- 商品搜索和详情会实时访问淘宝、1688、Onebound，且代码使用 `cache: "no-store"`。
- 1688 图片经 `/api/cached-image` 由应用服务器中转，会占用 ECS 公网带宽。
- MySQL 连接池只有 3 个连接，高并发时可能排队。
- 必须先确认 Nginx 指向哪个 Nuxt 进程/目录，以及 Next.js 项目是否实际部署；之后再判断 `next start` 或 `next dev`。
- 带宽建议先从 `3 Mbps` 临时升至 `10 Mbps` 验证；无 CDN 的短期正式配置可从 `20 Mbps` 起步。
- 带宽之外优先启用压缩与 HTTP/2、统一部署版本、建设 CDN、外部 API 超时降级和性能监控。
- Ubuntu 20.04 已结束标准支持，需要确认 ESM 或制定 LTS 升级计划。

当前已有域名侧的只读检测结果，但尚未取得服务器 SSH、Nginx 完整配置和进程信息；代码层结论仅适用于本地 Next.js 项目，不能直接当作当前 Nuxt 线上服务的事实。
