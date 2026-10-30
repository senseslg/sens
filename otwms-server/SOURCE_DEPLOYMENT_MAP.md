# OTWMS 源码与生产部署映射

## 当前结论

2026-10-16：生产 `otwms-group-1h76:/root/BladeX.jar` 与 Jenkins 生产工作区产物 SHA-256 一致：`d3a630f4f6fb90cdace66e67a53966a32cb87c59e592b0e2f419741ff9a7441f`。该 Job 配置构建 `*/master`，当前可读取的最近构建为 `#193`，2026-09-22 21:47:11（UTC+7）启动、结果 `SUCCESS`。构建 XML 未提取到 Git SHA，不将其推定为某个确切提交。

10-03 磁盘治理提交 `a5cc1f94e` 仍只在远程 `codex/fix-disk-pressure-retention`，未进入最新 `origin/master` `5b5af4ae2`（10-16 PR #3034）。最新 master 仍为 `setLogRetentionDays(1)`；当前生产 JAR 无新增清理类/保留期标记。**已确认修复未进入当前生产，不是修复上线后失效。** 本次只 fetch 与核对文件，未构建、合并或发布。

下方链路及 08-17 提交/哈希均为历史快照，不代表当前实例或运行提交。

```text
Bitbucket OTWMS/otwms-backend (master)
  → Jenkins: otwms / prod / otwms-backend
  → workspace target/BladeX.jar
  → otwms-group-cq0l:/root/BladeX.jar
  → XXL-JOB executor :9999
  → dailyBillJobHandler
```

## 2026-08-17 验证快照

| 项目 | 值 |
|---|---|
| 仓库 | `https://code.cambodianexpress.com/scm/otwms/otwms-backend.git` |
| 分支 | `master` |
| 生产提交 | `00a94febfdb50dca1175ac1940f576c4a29493dd` |
| Jenkins 构建产物 | `.../workspace/otwms/prod/otwms-backend/target/BladeX.jar` |
| 生产产物 | `otwms-group-cq0l:/root/BladeX.jar` |
| 两端 SHA-256 | `7e00a63099441b9482610783ce65b13f9a87759b74957e9a8baf5887ea143c16` |

## 本地源码 checkout

| 用途 | 本地目录 | 远程仓库 | 2026-08-17 提交 | 2026-10-01 `master` |
|---|---|---|---|---|
| 后端 | `otwms-server/otwms-backend/` | `ssh://git@code.cambodianexpress.com:9200/otwms/otwms-backend.git` | `00a94febfdb50dca1175ac1940f576c4a29493dd` | `5ba65f13f95b9eeda644046f2b43ce62e729a81a`（PR #3026，2026-09-22） |
| 前端 | `otwms-server/otwms-frontend/` | `ssh://git@code.cambodianexpress.com:9200/otwms/otwms-frontend.git` | `5cda7fb19565687cf9931fd1481d71f76520a913` | `4ec71efe69a42db417e2cdee10003f0321d142ef`（PR #593，2026-09-22） |

两个 checkout 当前均为 `master` 并跟踪 `origin/master`。源码目录由父仓库忽略，提交与分支操作应在各自目录内执行。

- 2026-08-17 生产提交 `00a94febf` 之后，后端 `master` 新增约 40 个提交，其中包括分批查询修复（PR #2976 合并 `a77eb6e71`）；前端新增 6 个提交。
- 当前生产 `/root/BladeX.jar` 对应哪个提交**未重新核对**；下次需按下方流程重新比对 SHA-256。
- 源码结构与风险见 [SOURCE_CODE_GUIDE.md](SOURCE_CODE_GUIDE.md)。

校验值只证明该时间点两端产物一致；每次发布后必须重新核对。

## 本次问题源码位置

查询实现：

```text
src/main/java/org/springblade/tms/service/impl/
TmsShipmentRevenueCostServiceImpl.java
```

- `getShipmentRevenueCosts(Set<String> shipmentCodes)` 位于当时源码第 64～77 行。
- 第 70～72 行通过 MyBatis-Plus `.in(..., shipmentCodes).list()` 一次提交全部参数。

任务入口：

```text
src/main/java/org/springblade/modules/biz/job/DailyBillJob.java
```

- `createDailyBillByShipments()` 在当时源码第 148 行调用该查询。
- 执行链：`generateDailyBill → rerun → run → createDailyBillByShipments → getShipmentRevenueCosts`。

## 角色边界

- `wms-db` 的 `xxl-job-admin` 是调度平台，不包含这段 OTWMS 业务源码。
- `otwms-group-cq0l` 运行编译后的 JAR，不是源码编辑位置。
- Bitbucket 是源码事实来源，Jenkins 负责构建，生产实例负责运行。
