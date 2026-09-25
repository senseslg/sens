# TMS 只读定位与发布验收

## 入口和目标实例

以下命令在 2026-09-18 已验证；实例名、NEG 端点和构建号是时间快照，执行前应先重新核对。

```bash
curl -sS -L -o /dev/null -w 'http=%{http_code} ssl=%{ssl_verify_result} total=%{time_total}\n' --max-time 15 https://tms.cambodianexpress.com/
gcloud compute url-maps describe tms-lb --global --project cambodian-express --format='yaml(hostRules,pathMatchers)'
gcloud compute backend-services get-health tms-neg-backend --global --project cambodian-express --format=json
gcloud compute network-endpoint-groups list-network-endpoints tms-neg --zone asia-southeast1-a --project cambodian-express --format=json
gcloud compute health-checks describe check-8080 --global --project cambodian-express --format='yaml(type,tcpHealthCheck)'
```

`HEALTHY` 只说明现有 TCP 检查通过；还要检查真实 HTTP。域名 `/` 正常会跳转 `/login`，使用 `curl -L` 验证最终 200 与 TLS 校验，不能用 `curl -k` 掩盖证书问题。

## 实例与发布定位

```bash
gcloud compute ssh tms-instance-template-20251103-082933 --zone asia-southeast1-a --project cambodian-express
```

实例上只读核对 `ps -eo user,pid,ppid,etime,rss,args`、`free -m`、`netstat -lnt` 和 `curl --max-time 10 http://127.0.0.1:8080/`。避免输出完整 Java 参数、环境变量或连接串。当前 OS Login 账号无 sudo，`/home/daniel` 为 700；Tomcat 日志、`deploy.sh` 和 root Java 诊断需由具备权限的运维人员执行，不应通过修改启动元数据绕过访问控制。

Jenkins 任务为 [TMS / prod / tms-prod](https://jenkins.cambodianexpress.com/job/TMS/job/prod/job/tms-prod/)。查看目标构建的 Console Output、Parameters、Git Build Data，依次核对提交、构建、GCS 上传、部署脚本和最终 HTTP；不要只看 Jenkins 的 `SUCCESS`。不要在生产机或 Jenkins 工作区直接改 WAR/源码。

Jenkins 中另有名为 `restart-tms` 的任务，但其目标实例和实际脚本尚未核实；不能仅凭名称作为恢复入口。

## 故障判断和恢复边界

1. 域名失败时先区分 TLS、负载均衡、实例端口和应用 HTTP：公网 502、8080 拒绝连接与 8080 可连接但 HTTP 超时，是不同阶段。
2. 若进程消失，先检查内核 OOM 记录、磁盘和内存，再考虑沿既有 Jenkins 链路受控恢复。不要手动用不同身份启动 Tomcat。
3. Jenkins 部署后等待真正的 HTTP 就绪，再验证登录页与业务轻量请求；本次从 PID 出现到应用可响应超过十分钟。超时应报告失败，不应只因进程存在便宣布恢复。
4. OOM 复发时先保留日志/诊断并查明增长来源；修改 JVM 堆、实例规格、健康检查或部署脚本都属于独立生产变更，需授权、回滚和验收。

参考 [HTTP 就绪与 TCP 健康检查](reference/http-readiness-vs-tcp-health.md)；本次详细证据见 [事故记录](INCIDENT_2026-09-17_OOM_AND_RECOVERY.md)。
