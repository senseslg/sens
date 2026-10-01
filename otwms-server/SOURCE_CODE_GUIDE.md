# OTWMS 源码导读

> 快照：`2026-10-01` 初读 `origin/master`。后端 `5ba65f13f`（PR #3026，2026-09-22），前端 `4ec71efe6`（PR #593，2026-09-22）。只读阅读结论，不代表生产已部署版本。

## 一句话结论

OTWMS 是基于 **BladeX 2.0.7（SpringBlade 商业版）** 二次开发的单体系统：后端为 Java 8 / Spring Boot 2.1.7 单 JAR，前端为 Saber（Vue 2 + Element UI + Avue）管理后台。业务核心在后端 `otwms/business` 与 `tms` 包，并直接跨 schema 读写共享 Cloud SQL 的 `tms_uat`。

## 后端 `otwms-backend`

| 项 | 事实 |
|---|---|
| 技术栈 | Java 1.8、Spring Boot 2.1.7、BladeX 2.0.7、MyBatis-Plus、HikariCP、Redis + JetCache、Undertow |
| 主要依赖 | XXL-JOB core 2.3.1、Apache POI 4.1.0、GCP Pub/Sub / GCS、Firebase、Telegram Bot、iText（含高棉文渲染 `org.seuksa.itextkhmer`） |
| 构建产物 | `pom.xml` `finalName=BladeX` → `target/BladeX.jar`，即生产 `/root/BladeX.jar` |
| 启动类 | `org.springblade.Application` |
| Profile | `application.yml` + `-dev/-test/-prod`；`server.port=80`；Liquibase 关闭 |
| 规模 | 约 1,667 个 Java 文件、71 个 Mapper XML、132 个 Controller、22 个测试文件；`master` 共约 3,755 个提交，最早 2021-05 |
| 过时文件 | `Dockerfile` 仍引用 `BladeX-Boot.jar`/端口 8800；README 基本为空；不代表当前部署方式 |

### 包结构（`src/main/java/org/springblade/`）

| 包 | 文件数 | 职责 |
|---|---:|---|
| `otwms/business` | 534 | OTWMS 核心业务：`order`(133)、`basic`(87)、`customer`(53)、`commission`(42)、`externaldelivery`(33)、`pay`、`workorder`、`inventory`、`wallet`、`withdraw` 等 |
| `otwms/external` | 33 | 对外开放接口与回调通知 |
| `tms` | 248 | 访问 TMS 数据（39 个实体均为 `schema="tms_uat"`）、费用/运费计算、TMS 报表和同步任务 |
| `modules` | 403 | BladeX 平台模块：`system`、`auth`、`biz`（含 `DailyBillJob`）、`fee`、`touch`（推送/SMS）、`bot`（告警机器人）、`feign`（调用 TMS/CCSL） |
| `app` | 50 | 移动端 API：`customer`、`courier`、`franchisee`、`ceexpresscn`、`otp` |
| `integration` | 49 | Pub/Sub 消息、GCS、Firebase 推送、邮件、短信、`di` 客户同步 |
| `common` | 246 | 导出（`common/export`）、切面、缓存、拦截器、i18n、工具类 |

### 外部依赖关系

- **数据库**：业务库 + 共享 Cloud SQL `tms-db` 上的 `tms_uat` schema（名称含 uat，但是生产数据）。
- **TMS / 新 CCSL**：HTTP 调用，地址取自配置 `tms.server`、`new.ccsl.url`。
- **Pub/Sub**：订阅 `order/shipment/customer/shop_event_sub_pro`。
- **XXL-JOB**：执行器端口 `9999`，调度在 `wms-db` 的 `xxl-job-admin`。源码中共 36 个 `@XxlJob` handler，分布在 29 个类（多数为 `*/job/*Job.java`），主要包括：
  - TMS 同步：订单、取消、客户、地址、快递员、加盟商、状态等。
  - 账单与佣金：`dailyBillJobHandler`、`commissionJobHandler`、`exportLastMonthCommissionJobHandler`。
  - 报表邮件、提醒、自动取消/清理，以及 `findSleepingThreadDeadLock` 告警。

### 故障相关源码位置

| 主题 | 位置 | `master` 现状 |
|---|---|---|
| 任务 13 大 `IN` 查询 | `tms/service/impl/TmsShipmentRevenueCostServiceImpl.java` | **已修复**：按 500 个分批（PR #2976，2026-08-17 合并）；生产是否已部署待核对 |
| XXL-JOB 日志保留 | `config/JobConfig.java:24` | **未修复**：仍为 `setLogRetentionDays(1)`，2.3.1 下等于关闭清理 |
| POI 临时文件 | `common/export/controller/ExportController.java` | **未修复**：两处 `new SXSSFWorkbook()` 均无 `dispose()` |
| Daily Bill 任务 | `modules/biz/job/DailyBillJob.java` | `rerun` 先删后跑，重跑前需确认幂等 |

## 前端 `otwms-frontend`

| 项 | 事实 |
|---|---|
| 技术栈 | Saber 2.0.7：Vue 2、Vuex、Vue Router、Element UI、Avue、vue-i18n、ECharts 5、axios；Vue CLI 3 |
| 语言 | `src/lang/`：`zh`、`en`、`kh`（高棉语） |
| API 前缀 | 全部走 `/api`；本地开发 `devServer` 端口 8086，代理目标：默认/dev → `otwms-uat.cambodianexpress.com/api/`，`NODE_ENV=prod` → `otwms.cambodianexpress.com/api/` |
| 外部直链 | 附件下载 `tms(-uat).cambodianexpress.com/api/public/attach/download/`；接口文档注释指向 `yapi.cambodianexpress.com` |
| 规模 | 322 个 `.vue`；主要业务视图 `ExpressOrderManagement`(39)、`Ordermanagement`(28)、`basic`(23)、`dashboard`(15)、`report`(12) |
| 构建 | `yarn build`/`npm run build`；UAT 由 Jenkins `otwms-frontend-uat` 发布到 `gs://otwms-frontend-uat/` |
| 过时文件 | `build.sh` 为框架原始脚本（scp 到外部 IP），不是当前发布方式，**不要执行** |

## 开发活跃度（2026 年 `master`，不含合并提交）

- 后端：`SiGentIsHere` 58、`milo` 22、`21287` 12、`cyj` 7。2026-08 下旬 `bugfix/CE-2616-returning` 被合并后 revert 了两次，发布时要留意。
- 前端：`SiGentIsHere` 34、`Brian.H.Wang` 10。
- 分支命名：`bugfix/CE-*`、`bugfix/CCSL-*`（Jira 编号），经 Bitbucket PR 合并到 `master`。后端约 320 个、前端约 220 个远程分支，大量为历史残留。

## 风险

- **明文凭据入库**：`application*.yml` 中存在数据库、邮件、对象存储等凭据字段的明文值，任何拥有仓库读权限的人都可见。建议改为环境变量或 Secret Manager，并轮换已暴露的凭据；本记录不复制具体值。
- **技术栈老旧**：Java 8、Spring Boot 2.1、Vue 2、Vue CLI 3 均已停止维护，升级成本高，短期以安全补丁和配置治理为主。
- **跨库耦合**：OTWMS 直接读写 `tms_uat` 表，TMS 侧的表结构变更会直接影响 OTWMS。
- **生产版本未知**：`2026-08-17` 之后 `master` 新增约 40 个提交，生产 JAR 对应哪个提交需重新核对 SHA-256。
