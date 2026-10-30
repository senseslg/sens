# WMS DB Runbook

## IAP 登录

```bash
gcloud compute ssh wms-db \
  --project=cambodian-express \
  --zone=asia-southeast1-a \
  --tunnel-through-iap
```

实例无公网 IP。登录后默认只做脱敏、只读检查：

```bash
uptime
free -h
df -hT /
df -ih /
systemctl is-system-running
sudo docker ps --format '{{.Names}}|{{.Image}}|{{.Ports}}'
sudo nginx -t
sudo netstat -ltn
```

不要输出容器环境变量、完整进程参数、数据库连接串、凭据或原始业务日志。

## 域名定位

1. 核对 DNS 是否仍指向 GCP `dev-lb` 的共享入口。
2. 核对 GCP 后端健康状态和 `wms-db:80`。
3. 在 `wms-db` 使用 `nginx -T` 定位目标 Host 的本机上游；Jenkins 当前为本机 `8081`。
4. 核对对应 Docker 容器与监听端口。
5. 依次验证本机上游、负载均衡和公网域名，区分入口、代理和应用故障。Jenkins 未授权根路径当前返回 403，可作为在线信号，但不能替代登录后的 Job 健康检查。

## Jira 需求操作

需求管理优先使用本机 [jira-service Runbook](jira-service/RUNBOOK.md)：读取项目字段 → 查重与预检查 → 按授权提交 → 读回核对。关闭/不做先读取当前工作流，并确认指定编号与原因；导出按用户偏好使用 CSV，同时说明全部 API 字段与后台“所有域”的差异。

服务在本机启动，不需要 SSH 到 `wms-db` 安装。凭据放入本机 Git 忽略配置，不输出到日志或文档。需求创建/状态变更授权不包含 Jira 升级、容器操作或数据库修改。

## Jira 时区

后台默认/账号展示时区与 JVM 时区分开核对。REST 返回 UTC 不代表金边设置失效；先比较带偏移时间代表的同一时刻，不为改变返回格式而直接重启。当前结论及业务影响见 [Jira 时区评估](JIRA_TIMEZONE_ASSESSMENT.md)。

## Bitbucket 时区

2026-10-23 已按授权将 Bitbucket 4.0.2 的 JVM 时区改为 `Asia/Phnom_Penh` 并重启验证；启动脚本已同步持久化。配置、备份和回滚方法见 [Bitbucket 时区记录](BITBUCKET_TIMEZONE.md)。核对运行中 `user.timezone`，不以容器 `date` 或 HTTP `Date` 头判断应用时区。

## 操作边界

- 容器重启、镜像升级、Nginx 修改、数据库操作、数据卷清理、端口或防火墙变更均需明确授权和回滚方案。
- 该机是共享单点，处理单个业务前先列出对 Jira、Bitbucket、Jenkins、XXL-JOB、YApi、Nexus 和数据库的影响。
- 变更前核实备份及恢复验证；不要仅凭容器 `Up` 或 GCP `RUNNING` 判断业务健康。
