# TMS Server Overview

## 目标与完成标准

- 快速定位 `tms.cambodianexpress.com` 的入口、实际运行实例、源码和 Jenkins 发布任务。
- 区分“端口可连接”“应用可响应”和“业务流程可用”，并保留发布与故障证据。
- 解决 2026-09-17 OOM 的复发风险；此项尚未完成。

## 当前状态（2026-10-01）

TMS 再次出现间歇性超时，已复现本机登录页与静态资源无响应后自行恢复；故障时实例资源有余量，Redis 未见容量耗尽。根因仍需有权限的运维采集故障线程栈/GC/日志；另发现 JDWP 监听与云防火墙公网放行风险，尚未证实为故障触发点。见 [本次事故记录](INCIDENT_2026-09-30_INTERMITTENT_TIMEOUT.md)。未重启、部署或改配置。

`10-01 09:11–09:14` 再次捕捉本机 HTTP 超时、LB backend_timeout，但 TCP 健康检查仍 HEALTHY。Java FD 软/硬上限均为 4096；用户授权软上限试验尚未执行，因为软上限已等于硬上限且当前账号不能管理 root Java。继续试验需管理员入口及明确硬上限变更范围；无效恢复 4096/4096。

`2026-09-18` 发布后的登录入口曾通过验收，不代表 Franchise/Courier App 全流程已验证，也不代表当前持续健康。历史经过见 [OOM 事故记录](INCIDENT_2026-09-17_OOM_AND_RECOVERY.md)。

服务器基础信息、SSH 入口与权限障碍见 [SERVER_INFO.md](SERVER_INFO.md)。用户反馈的 CPU Idle 99% 尚未独立核实；若为 CPU 空闲指标，不代表 CPU 满载。

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

- [ ] 参与共享 Cloud SQL [`tms-db` 容量治理](../google-cloud/TMS_DB_CAPACITY_REVIEW_2026-09-28.md)：优先检查 TMS 接口审计表中重复的大响应，确认业务保留期和源码写入点。
- [ ] 授权运维查看 Tomcat 业务/启动日志及 JVM 内存诊断，定位 OOM 前的增长原因；未证实是新代码、数据库或流量引起。
- [ ] 由业务方验证 Franchise/Courier App 的原故障页面；已确认 OTWMS 曾调用 TMS 接口收到 502，但不能据此推断所有页面错误都由 TMS 导致。
- [ ] 为 Jenkins 发布增加 HTTP 就绪与业务轻量验收；评估使用稳定、无副作用的 HTTP 健康路径替代仅探测 TCP 的 `check-8080`。
- [ ] 复核 JVM `-Xms24g -Xmx24g` 与约 32 GB、无 swap 的实例容量，并建立内存告警与有依据的回滚方案；不要仅靠反复部署掩盖 OOM。

最近更新：`2026-10-01`
