# TMS UAT OOM 与 CCSL 转运失败

调查、配置调整与恢复检查日期：2026-10-06。除注明 UTC 外，均为 Asia/Phnom_Penh（UTC+7）。
状态：技术入口已恢复；CCSL 订单业务验收和长期内存观察尚未完成。

## 影响与结论

CCSL UAT 单 `CC05102600001` 执行“更新状态 > 已转运”后，因 TMS 返回 HTTP 502
被置为转运失败（99）。产品通道合法，基础字段检查通过；故障不在 CCSL 产品配置。

TMS UAT 在 10-05 06:10:06 发生系统 OOM，内核杀掉 Java。Tomcat 日志在同一时间附近停止更新，
调查时 Java 不存在、8083 未监听，Nginx upstream 连接被拒绝，转运接口持续返回 502。
堆配置超过物理内存是明确风险；未确认具体内存增长或泄漏来源，不能声称泄漏已修复。

## 测试环境定位

| 项目 | 本次核实值 |
|---|---|
| GCP project / zone | `cambodian-express` / `asia-southeast1-a` |
| 实例 | `tms-uat`，不是生产 Tomcat 实例 |
| 公网入口 | `https://tms-uat.cambodianexpress.com/` |
| 转运接口 | `POST /api/public/v3/order/body-booking` |
| LB 链路 | `tms-uat-lb -> tms-uat -> tms-uat-neg -> tms-uat:80` |
| NEG 端点快照 | `10.148.0.19:80` |
| 健康检查 | `port-80`；应用停机时仍为 HEALTHY，不代表 8083 可用 |
| Tomcat | `/home/daniel/tomcat`，HTTP 8083，另有 Connector 8019 |
| 部署脚本 | `/home/daniel/deploy.sh` |
| 内存参数 | `/home/daniel/tomcat/bin/setenv.sh` 的 `CATALINA_OPTS` |
| Nginx 配置 | `/etc/nginx/conf.d/tms-uat*.conf` |
| Nginx 错误日志 | `/var/log/nginx/reverse-error.log` |
| Tomcat 日志 | `/home/daniel/tomcat/logs/` |

只读 SSH：`gcloud compute ssh tms-uat --zone asia-southeast1-a --project cambodian-express`。
本次登录身份具备免密 sudo 读取权限；这不代表生产实例也具备同样权限。

## 故障证据与时间线

- 10-05 06:10:06：内核记录 OOM（UTC 为 `2026-10-04T23:10:06Z`），
  杀掉 Java PID 15338，anon-rss 2583836 KiB（约 2.46 GiB）。
- `catalina-2026-10-05.out` 最后修改时间为 06:10:08；随后未发现运行中的 Java，8083 未监听。
- 10-05/10-06 Nginx 错误日志有持续 `connect() failed / Connection refused`，
  upstream 为 `127.0.0.1:8083`，包括 `body-booking` 请求。
- CCSL 对目标单的推送在 10-05 08:59:54、09:00:07、09:01:33、13:00:00，
  以及 10-06 13:00:00 均收到 502；13:00 自动重试不能修复停机根因。
- UAT 总内存 3789 MiB、无 swap，同机 MySQL/Redis；原配置为 `-Xms4096m -Xmx4096m`。
  JVM 非堆内存和其他服务也需要内存，不能将物理内存全部配置为堆。

## 已执行处理

用户明确授权后，仅修改 UAT `setenv.sh`：

```text
原配置：-Xms4096m -Xmx4096m
新配置：-Xms512m -Xmx1536m
```

保留其他内容、属主和权限，通过 `bash -n` 和写入后内容检查。
原文件备份：`/home/daniel/tomcat/bin/setenv.sh.bak.20261006T071255Z`。

读取服务器端 `deploy.sh` 确认它更新 webapps/WAR 并启动 Tomcat，没有覆盖 setenv 的操作。
Jenkins 完整任务配置、任务名和构建号未独立核对；不要将生产 `tms-prod` 任务当作 UAT 恢复入口。
用户随后报告已经重启，实际 Java 启动时间为 10-06 14:20:22（UTC 07:20:22）。
诊断与配置调整期间没有通过 SSH 手动启动、停止或重启服务。

## 重启后验收

- Java 为 root，8083 正常监听，本机 `/` 返回 302。
- 从 CCSL 服务器访问 TMS UAT 入口，跟随跳转最终 200；转运路径无凭据 GET 返回 405，不再是 502。
- `jcmd VM.flags` 确认实际 InitialHeapSize=512 MiB、MaxHeapSize=1536 MiB。
  只输出这两个数值，不导出完整 Java 参数、环境变量或连接串。
- 验证时运行约 1 小时 37 分，Java RSS 约 1 GiB，系统 available 1564 MiB，启动后没有新的内核 OOM。
- CCSL 该单仍为 99，无转运时间、无 TMS 单号；最新失败操作日志仍为 10-06 13:00。
  没有发送转运 POST、重试订单或修改数据库。GET 405 不是业务成功验收。

## 后续与回滚边界

1. 后台重新执行该单“已转运”，核验 CCSL 状态 7、TMS 单号与成功日志，避免重复创建订单。
2. 持续观察 available、Java RSS、GC 与 OOM；1536 MiB 是恢复起点，不保证长期足够。
   若堆不足，应评估实际工作负载、同机服务与扩容，不直接恢复不合理的 4096 MiB 配置。
3. 核实 Jenkins QA/UAT 任务及配置归属，避免未来部署覆盖；考虑增加应用层 HTTP 就绪检查。
4. 部署及所有服务启停只能通过目标已核实的 Jenkins 任务，不能经 SSH 手动启动 Java。
   备份用于审计或受控配置回滚；恢复原 4 GiB 堆会重新引入容量风险，不能盲目回滚。
5. CCSL 失败日志 remark 为空的既有问题尚未修复，后台无法直接显示失败原因。

本次没有查测试数据库。`tms_uat` 也是生产 Cloud SQL 使用的 schema 名，不能仅凭名称判断环境。
CCSL 对应记录：`/Users/lingang/work/new_ccsl/incidents/UAT_TRANSFER_FAIL_TMS_OOM_2026-10-05.md`。
