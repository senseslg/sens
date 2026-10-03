# OTWMS Server Runbook

## SSH 入口

```bash
gcloud compute ssh <current-otwms-instance> \
  --zone asia-southeast1-a \
  --project cambodian-express

gcloud compute ssh wms-db \
  --zone asia-southeast1-a \
  --project cambodian-express \
  --tunnel-through-iap
```

`otwms-group-*` 实例名可能随实例组替换。应先从 XXL-JOB 日志取得执行器地址，再用 GCP 实例清单映射当前实例。

## 磁盘与 inode 巡检

使用默认只读、脱敏脚本同时检查容量、inode、应用日志实际占用、`/tmp`、POI、XXL-JOB、Java 打开文件和本机 HTTP：

```bash
python3 /Users/lingang/sens/otwms-server/scripts/check_disk_pressure.py \
  --project cambodian-express \
  --zone asia-southeast1-a \
  --instance <current-otwms-instance>
```

退出码和治理边界见 [reference/disk-capacity-triage.md](reference/disk-capacity-triage.md)。脚本不清理文件；任何周期删除都必须单独确认保留期、打开文件、回滚和验收。

## 磁盘修复专项回归（本地）

```bash
python3 otwms-server/scripts/verify_disk_fixes.py
```

需要本地后端修复分支、支持 `--release 8` 的 JDK 和 Maven 缓存中的 POI 4.1.0/Logback 1.2.3 等依赖。不加载 Spring、不连接数据库、不运行 SSH；仅证明资源清理和日志 XML 专项通过，不替代完整 Maven 构建、部署及业务验收。当前完整构建受私有依赖缺失阻碍。

## 磁盘治理分支上线前验收

本次基线、提交和影响范围以 [10-03 事故记录](INCIDENT_2026-10-03_DISK_FULL_RECURRENCE.md) 为主。测试环境完成以下检查后，再另行授权生产发布：

- 在有私有依赖的公司环境完整构建；确认目标分支、产物 hash、旧 JAR 和启动配置回退点。
- 公共 `/export`：正常及大数据量导出内容一致；模拟异常、取消/断连后临时文件释放。尤其检查 EasyPOI 返回 workbook 前失败的路径。
- 持续占用 10 个导出许可的受控并发测试：多余请求拒绝，结束后许可恢复，拒绝请求不扩大并发上限；不要在生产压测。
- 核对任务日志保留期与日期目录内容，实际观察超期日志清理；核对日志配置生效、采集路径、轮转与归档上限，确认 stdout 不再无界增长。
- 登录、订单查询、Daily Report、Order Print 和执行器注册冒烟通过；检查容量/inode/POI 文件趋势，不能仅以首页 200 验收。

回退只覆盖代码与配置，不能恢复已删旧日志。脚本不做业务集成测试、生产部署或自动删除。

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

本地源码更新：

```bash
git -C /Users/lingang/sens/otwms-server/otwms-backend pull --ff-only
git -C /Users/lingang/sens/otwms-server/otwms-frontend pull --ff-only
```

公司 Bitbucket SSH 当前只提供旧版 `ssh-rsa`。两个仓库已在各自 `.git/config` 设置兼容参数；不要把该设置扩大到全局 SSH 配置。

Windows 工作机（`D:\sens_apps\sens`，Git Bash，2026-10-01 验证）：

```bash
git -C /d/sens_apps/sens/otwms-server/otwms-backend pull --ff-only
git -C /d/sens_apps/sens/otwms-server/otwms-frontend pull --ff-only
```

- 该 Bitbucket 不接受 ED25519 公钥（提示 “You must enter a valid public key”），需使用 RSA。
- 本机专用密钥为 `~/.ssh/id_rsa_otwms`，已注册到有 OTWMS 权限的账号；两个仓库的 `core.sshCommand` 固定使用该密钥并加上 `IdentitiesOnly=yes`。
- 本机默认的 `id_rsa` 能通过 Bitbucket 认证，但它所属的账号没有 OTWMS 仓库权限；如果不指定密钥，会报 “repository does not exist”。

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

## UAT 前端 Cloud Storage 恢复

目标桶：

```text
gs://otwms-frontend-uat/
```

先只读确认桶策略、live 对象和软删除对象：

```bash
gcloud storage buckets describe gs://otwms-frontend-uat --format=json
gcloud storage ls --recursive --long 'gs://otwms-frontend-uat/<prefix>/**'
gcloud storage ls --soft-deleted --recursive --json 'gs://otwms-frontend-uat/<prefix>/**'
```

恢复前必须锁定对象名、generation、软删除时间和 hard delete 时间。只恢复明确版本，不对整个桶使用通配符；恢复操作需单独授权：

```bash
gcloud storage restore 'gs://otwms-frontend-uat/<object>#<generation>'
```

恢复后需核对：

- live 对象数量、大小、MD5/CRC32C 和 `Content-Type`；
- 业务 URL 返回 HTTP 200；
- bucket-level IAM 仍能满足业务读取与 Jenkins 更新；
- 原软删除 generation 会继续保留到 hard delete 时间，这是正常行为；恢复会创建新的 live generation。

Lifecycle 的 `age` 按对象创建时间计算，不按最后访问时间计算。重新配置删除规则前必须限定业务前缀并预先列出命中对象。Cloud Audit Logs 不记录 Lifecycle 自动变更；如需追踪，应评估配置 Cloud Storage usage logs。

## 生产变更边界

以下操作必须明确目标提交、影响、回滚和验收，并获得授权：

- Jenkins 构建或部署。
- 替换、移动或重启 `/root/BladeX.jar`。
- 手动重跑 XXL-JOB。
- 修改 Cloud SQL flags、索引或数据。
- 恢复 Cloud Storage 对象、修改 Lifecycle、软删除策略或 IAM/ACL。
