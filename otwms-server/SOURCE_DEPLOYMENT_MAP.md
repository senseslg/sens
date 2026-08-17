# OTWMS 源码与生产部署映射

## 当前结论

生产任务 13 运行的 `/root/BladeX.jar` 已与 Jenkins `otwms / prod / otwms-backend` 的构建产物通过 SHA-256 精确匹配；对应源码仓库为 `OTWMS/otwms-backend` 的 `master`。

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

| 用途 | 本地目录 | 远程仓库 | 2026-08-17 当前提交 |
|---|---|---|---|
| 后端 | `otwms-server/otwms-backend/` | `ssh://git@code.cambodianexpress.com:9200/otwms/otwms-backend.git` | `00a94febfdb50dca1175ac1940f576c4a29493dd` |
| 前端 | `otwms-server/otwms-frontend/` | `ssh://git@code.cambodianexpress.com:9200/otwms/otwms-frontend.git` | `5cda7fb19565687cf9931fd1481d71f76520a913` |

两个 checkout 当前均为 `master` 并跟踪 `origin/master`。源码目录由父仓库忽略，提交与分支操作应在各自目录内执行。

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
