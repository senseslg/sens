# 2026-09-17 TMS OOM 与恢复

## 结果

2026-09-18 00:15（柬埔寨时间）前，TMS 登录页、本机 HTTP 与公网 HTTPS 均已恢复为 200。恢复来自用户触发的 Jenkins `tms-prod` #456 部署及其后的应用初始化；本次排查未再次重启或部署。App 业务流程尚待验证，OOM 的内存增长根因尚未查明。

## 事件证据

| 时间（UTC+7） | 已确认事实 |
|---|---|
| 09-17 22:04 | 内核 OOM killer 杀死 Java PID 2617，匿名 RSS 约 25.7 GB；随后本机 8080 拒绝连接，公网返回 502。 |
| 09-18 00:02—00:03 | Jenkins #456 完成 WAR 构建与 GCS 上传，执行 `sudo /home/daniel/deploy.sh`；Tomcat 重新启动。 |
| 00:05—00:11 | Java 已监听 8080，但本机 `/`、`/login`、`/favicon.ico` 仍超时；公网请求同样无业务响应。 |
| 同期 | `tms-neg-backend` 显示 `HEALTHY`，因为 `check-8080` 仅探测 TCP 连接；Jenkins `SUCCESS` 也只证明其脚本执行结束。 |
| 00:15 | 本机 `/` 返回 200；公网 `/` 正常跳转到 `/login`，登录页 200、TLS 校验通过，浏览器显示登录表单。 |

## 已知状态与未解问题

- 恢复后 Java RSS 约 8.7 GB；实例内存约 32 GB、无 swap；JVM 启动参数含 `-Xms24g -Xmx24g`。这些数值不单独证明 OOM 的原因。
- 故障期已验证 TMS 域名的 TLS 证书有效；公网 502 与本机 8080 拒绝连接相符，不能归因于证书失效。
- Jenkins #456 构建自 `master` 提交 `6e323c6b892f3614cee4608001c30de9679a43d4`，Maven 测试被跳过。没有证据证明此次提交导致此前 OOM。
- 当前 OS Login 账号无 sudo，且 `/home/daniel` 权限为 700，无法读取 Tomcat 业务日志或对 root Java 采集线程/堆诊断；需授权运维协助。
- Jenkins 部署脚本本身以 `sudo` 执行并启动 root Java。曾有人工启动导致后续 Jenkins 停止失败的经验，但不能仅凭 root 属主认定本次为人工启动；应以脚本、进程树及日志核对。

## 后续处理

1. 保存并检查 OOM 前后 Tomcat 日志、GC/内存曲线及必要的线程/堆信息，确定内存增长来源；再次 OOM 前不要盲目扩大堆或反复重部署。
2. 给发布流水线增加 HTTP 就绪轮询及超时失败判定，再由业务方验收 App 原故障页面。
3. 评估从 TCP 健康检查切换到无副作用的 HTTP 就绪端点；`tms-lb` 也服务 WMS，修改前核对关联后端和回滚。

Google Cloud 对 [TCP 与 HTTP 健康检查成功条件](https://docs.cloud.google.com/load-balancing/docs/health-check-concepts) 的说明支持上述“端口健康不等于应用就绪”的判断。
