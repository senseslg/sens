# OTWMS Server Runbook

## SSH 入口

```bash
gcloud compute ssh otwms-group-cq0l \
  --zone asia-southeast1-a \
  --project cambodian-express

gcloud compute ssh wms-db \
  --zone asia-southeast1-a \
  --project cambodian-express \
  --tunnel-through-iap
```

`otwms-group-*` 实例名可能随实例组替换。应先从 XXL-JOB 日志取得执行器地址，再用 GCP 实例清单映射当前实例。

## 任务日志

生产执行器的任务日志按日期和日志 ID 保存：

```text
/tmp/YYYY-MM-DD/<xxl-job-log-id>.log
```

只读取目标日志的开头、结尾和异常链，避免输出完整业务参数：

```bash
sudo wc -lc /tmp/YYYY-MM-DD/<log-id>.log
sudo sed -n '1,60p' /tmp/YYYY-MM-DD/<log-id>.log
sudo tail -n 120 /tmp/YYYY-MM-DD/<log-id>.log
```

## 源码与 Git 核对

生产 Jenkins 工作区：

```text
/home/daniel/containers/jenkins/jenkins/workspace/otwms/prod/otwms-backend
```

该服务器 Git 版本较旧，不支持 `git -C`；只读核对使用：

```bash
git --git-dir=<workspace>/.git --work-tree=<workspace> remote -v
git --git-dir=<workspace>/.git --work-tree=<workspace> rev-parse HEAD
git --git-dir=<workspace>/.git --work-tree=<workspace> log -1 --format='%ci%n%s'
```

远程 URL 若包含用户信息，输出前应脱敏。不要直接编辑工作区文件。

## 构建产物核对

在 Jenkins 与生产实例分别执行：

```bash
sha256sum <jenkins-workspace>/target/BladeX.jar
sha256sum /root/BladeX.jar
```

校验值一致只能证明产物字节一致；还应核对目标提交、进程启动时间、端口和发布后日志。

## 数据库诊断边界

- 先看 `SHOW INDEX`、`information_schema.TABLES`、`EXPLAIN`、超时变量和 `SHOW WARNINGS`。
- 大型 `IN` 诊断使用虚构值和 `EXPLAIN`，不要先执行真实 SELECT 或无界 COUNT。
- 不输出应用数据源凭据、完整连接串或业务 shipment code。
- 修改索引、数据库 flags、超时参数或业务数据前必须单独授权。

详细方法见 [reference/mysql-large-in-query.md](reference/mysql-large-in-query.md) 和 [reference/xxl-job-source-tracing.md](reference/xxl-job-source-tracing.md)。

## 生产变更边界

以下操作必须明确目标提交、影响、回滚和验收，并获得授权：

- Jenkins 构建或部署。
- 替换、移动或重启 `/root/BladeX.jar`。
- 手动重跑 XXL-JOB。
- 修改 Cloud SQL flags、索引或数据。
