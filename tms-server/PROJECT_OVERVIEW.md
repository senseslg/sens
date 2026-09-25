# TMS Server Overview

## 目标与完成标准

- 快速定位 `tms.cambodianexpress.com` 的入口、实际运行实例、源码和 Jenkins 发布任务。
- 区分“端口可连接”“应用可响应”和“业务流程可用”，并保留发布与故障证据。
- 解决 2026-09-17 OOM 的复发风险；此项尚未完成。

## 当前状态（2026-09-18）

公网 `/` 跳转至 `/login`，登录页返回 HTTP 200 且 TLS 校验通过；实例本机 HTTP 返回 200，GCP 后端为 `HEALTHY`。这是登录入口验收，不代表 Franchise/Courier App 全流程已验证。详细经过见 [事故记录](INCIDENT_2026-09-17_OOM_AND_RECOVERY.md)。

## 系统边界

| 层级 | 已确认位置 |
|---|---|
| 域名入口 | `tms.cambodianexpress.com` → GCP URL map `tms-lb` 的 `path-matcher-2` |
| 后端 | `tms-neg-backend` → `tms-neg`，`asia-southeast1-a` |
| 实例 | `tms-instance-template-20251103-082933`，当次内网端点 `10.148.0.116:8080` |
| 应用 | `/home/daniel/apache-tomcat-8.5.50` 中的 Java/Tomcat；生产 WAR 由部署脚本处理 |
| 源码 | Bitbucket `TMS/tms-server` 的 `master`；本子项目未克隆源码 |
| 构建发布 | `wms-db` 上 Jenkins `TMS / prod / tms-prod` |
| 部署包中转 | `gs://cambodian-express/ROOT.war` |

完整映射及证据强度见 [SOURCE_DEPLOYMENT_MAP.md](SOURCE_DEPLOYMENT_MAP.md)。`tms-lb` 同时有 `wms.cambodianexpress.com` 路由；调整共享 URL map 前须核对 WMS 影响。

## 当前风险与下一步

- [ ] 授权运维查看 Tomcat 业务/启动日志及 JVM 内存诊断，定位 OOM 前的增长原因；未证实是新代码、数据库或流量引起。
- [ ] 由业务方验证 Franchise/Courier App 的原故障页面；已确认 OTWMS 曾调用 TMS 接口收到 502，但不能据此推断所有页面错误都由 TMS 导致。
- [ ] 为 Jenkins 发布增加 HTTP 就绪与业务轻量验收；评估使用稳定、无副作用的 HTTP 健康路径替代仅探测 TCP 的 `check-8080`。
- [ ] 复核 JVM `-Xms24g -Xmx24g` 与约 32 GB、无 swap 的实例容量，并建立内存告警与有依据的回滚方案；不要仅靠反复部署掩盖 OOM。

最近更新：`2026-09-18`
