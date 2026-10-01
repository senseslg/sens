# TMS 源码、发布与运行映射

## 当前链路

```text
Bitbucket TMS/tms-server (master)
  → Jenkins: TMS / prod / tms-prod（运行于 wms-db）
  → TmsParent/tms/target/tms.war
  → gs://cambodian-express/ROOT.war
  → sudo /home/daniel/deploy.sh（目标 TMS 实例）
  → /home/daniel/apache-tomcat-8.5.50 :8080
  → tms-neg → tms-neg-backend → tms-lb → tms.cambodianexpress.com
```

## 2026-09-18 发布与入口快照

| 证据 | 已确认值 |
|---|---|
| Jenkins 任务与构建 | [TMS / prod / tms-prod #456](https://jenkins.cambodianexpress.com/job/TMS/job/prod/job/tms-prod/456/console)，结果 `SUCCESS` |
| 源码仓库 | `https://code.cambodianexpress.com/scm/tms/tms-server.git`，`origin/master` |
| #456 源码提交 | `6e323c6b892f3614cee4608001c30de9679a43d4` |
| Jenkins 容器工作区 | `/var/jenkins_home/workspace/TMS/prod/tms-prod` |
| 构建命令 | `mvn clean package -f TmsParent -P gcp`；该次测试被跳过 |
| 发布命令 | 上传 WAR 至 GCS，再 SSH 到 `tms-instance-template-20251103-082933` 执行 `sudo /home/daniel/deploy.sh` |
| 实例运行 | Tomcat 8.5.50、8080；#456 后 Java 进程属主为 root（由 Jenkins 脚本启动） |
| 域名路由 | `tms-lb` 的 `tms.cambodianexpress.com` 主机规则 → `tms-neg-backend` → `tms-neg` 当前唯一端点 `10.148.0.116:8080` |
| 健康检查 | `check-8080`，TCP/8080；不读取 HTTP 状态或响应内容 |

Jenkins 控制台证明构建、上传、调用部署脚本以及报告 PID；尚未独立比对 Jenkins WAR、GCS 对象与实例实际 WAR 的校验值，因此不能声称三者字节完全一致。每次发布需重新核对当前提交、产物和运行实例，不能把 #456 当作永久状态。

## 2026-10-01 本机源码核对

- 用户授权后已将 `ssh://git@code.cambodianexpress.com:9200/tms/tms-server.git` 克隆到本项目 `TMS-source`，本机工作树检出 `master`，HEAD `6e323c6b892f3614cee4608001c30de9679a43d4`。
- 此提交与上方 Jenkins #456 的历史源码提交相同；该事实不证明线上正在运行的 WAR 仍来自该提交。未修改源码，也未进行构建或部署。
- 10 月 1 日间歇性超时的追加日志和源码风险分析见 [事故记录](./INCIDENT_2026-09-30_INTERMITTENT_TIMEOUT.md#2026-10-01-源码与云端日志补查)。

## 与其他系统的界线

- `tms-lb` 也承载 `wms.cambodianexpress.com`，但其 `path-matcher-1` 指向独立的 `wms-backend`；TMS 故障不等于 WMS 后端故障。
- `otwms.cambodianexpress.com` 运行在独立的 OTWMS 后端；OTWMS 某些业务流程会调用 TMS。2026-09-17 曾观察到 OTWMS 向 `/api/public/tms/shipment/scan-update-app` 发起调用并收到 502。
- `wms-db` 承载 Jenkins、Bitbucket 和 XXL-JOB 管理后台，不是 `tms.cambodianexpress.com` 的 Tomcat 实例。
