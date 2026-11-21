# Cloud SQL + Compute 降本方案评估

更新：2026-11-21（UTC+7）。状态：`待决定`（方向已定，具体措施待审批）。本轮只做只读采集、账单读取和分析，没有改动任何云资源。

## 1. 目标与用户决定

- 用户目标：Cloud SQL 和 Compute Engine 合计月费降到当前的 50%，且不影响业务。
- 用户决定（2026-11-21）：
  - `wms-db`（Jira/Bitbucket/Jenkins/YApi/XXL-JOB 等共享平台）**继续保留在 GCP**。
  - **TMS 和 OTWMS 不迁到阿里云。** 本土物流业务将在另一个系统上重新开发；新系统接手后，TMS/OTWMS 整体退役。
- 基线（10 月实际，税前）：SQL **$1,143.78** + Compute **$1,040.21** = **$2,183.99**；50% 目标约 **$1,092**。全项目 10 月 $3,446.41，明细见 [10 月账单](../google-cloud/records/billing-2026-10.md)。

## 2. 实时采集（2026-10-22 至 11-21，30 天）

证据：[cost-audit-2026-11-21.json](../google-cloud/records/cost-audit-2026-11-21.json)，用 `cloud_cost_audit.py` 采集，退出码 0，无失败项。CPU 均值和 P95 都是小时均值；峰值指每小时最大值。

| 资源 | 规格 | 实测 | 变化或风险 |
|---|---|---|---|
| `tms-db` | 8 核/52G，SSD | 已用 1,194.6→**1,250.7 GiB**，配额 1,253→**1,303 GB**（自动扩容）；Binlog 12.5→48.5 GiB；内存约 43.9 GiB；连接约 69 | CPU 均值 10%，但**小时峰值的 P95 为 88%、最大 100%**，降到 4 核风险高 |
| `tms-uat-db` | 1 核/3.75G | 已用 51 GiB；平均 73 个连接，最多 129 | 仍在使用，自动备份关闭 |
| TMS VM | C2-8 核/32G | CPU 1.3% / 1.9%，峰值 23%；内存 53%/60% | 规格明显偏大 |
| OTWMS VM | C2-4 核/16G | 30 天内**换过 5 个实例**；内存 74–90% | 内存吃紧，不能降内存；实例反复重建的原因待查 |
| `otwms-uat` / `tms-uat` | e2-medium | CPU 16.5% / 4.1% | 测试机 |
| `wms-server` | e2-small，600 GB | CPU 2.5%；只剩 `cp` 后端在运行 | 迁走 `cp` 后可整台释放 |
| `wms-db` | e2-highmem-4，500 GB | CPU 13%，峰值约 100%；内存 50–52% | 保留在 GCP |
| `toucha-backend` | e2-medium，20 GB | 监控显示 `sda2` 使用率 **100%** | **需登录确认是否满盘** |
| `ce-tms` 桶 | — | 4,515→**4,624 GiB**（+108 GiB/月） | 持续增长 |
| `ce-fileserver` 桶 | — | 1,149→1,191 GiB | 归属哪个系统待确认 |
| Redis | 3 个 1 GB Basic | `tms-redis` 12 MiB、`otwms-uat` 4 MiB、`redis` 751 MiB | `redis` 的使用方待确认 |
| Geocoding | — | 10 月 143,185 次，$622.74 | 调用来源待查 |

## 3. 10 月费用归属（按 SKU 用量和单价拆分）

方法：Cloud SQL 和 C2/E2 的 SKU 用量与各实例规格×744 小时完全对上，按实例拆分；磁盘按容量拆分。出网、外部 IP、快照无法按实例拆，单列为未归属。

| 归属 | 资源 | 10 月 |
|---|---|---:|
| **TMS/OTWMS** | `tms-db`：计算 $723 + 存储约 $299 + 备份 $22 | **$1,044** |
| **TMS/OTWMS** | `tms-uat-db`：计算 $70 + 存储 $28 | **$99** |
| **TMS/OTWMS** | TMS VM C2-8（含盘） | $318 |
| **TMS/OTWMS** | OTWMS VM C2-4（含盘） | $159 |
| **TMS/OTWMS** | `tms-uat` $35、`otwms-uat` $34、`wms-server` $42 | $111 |
| 保留 | `wms-db`（含 500 GB 盘） | $188 |
| 保留 | `toucha-uat` $95、`toucha-backend` $33、`ce-lb` $31、`nacos` 空盘 $11 | $170 |
| 未归属 | 出网 $63、外部 IP $22、快照和镜像 $10 | $95 |

**TMS/OTWMS 合计约 $1,731，占 SQL+Compute 的 79%。** `otwms` 库也在 `tms-db` 上。

### 共享平台和依赖（来自服务清单）

- **`wms-db`：** Jira、Bitbucket、Jenkins、YApi（含 MongoDB）、XXL-JOB 管理后台、Nexus、容器版 MySQL 5.7、Redis、Archery、GoInception；宿主机另有 MySQL、PostgreSQL、MongoDB。见 [服务清单](../wms-db/SERVICE_INVENTORY.md)。
- **`wms-server`：** 只有 CEWMS（10/17 已停）和 `cp` 后端，见 [服务清单](../otwms-wms-server/SERVICE_INVENTORY.md)。
- **退役时要处理的依赖：**
  - OTWMS 的定时任务由 `wms-db` 上的 XXL-JOB 调度。
  - Jenkins 里有 `TMS`、`otwms`、`restart-tms` 等发布任务。

## 4. 方向：退役前低风险优化，新系统上线后退役

迁移方案已取消。TMS/OTWMS 退役前，只做**能快速回本、可以回退**的优化；需要停机、重建或长期锁定的投入，按预计退役时间判断是否值得。

### 4.1 现在就做（退役前也划算）

| 措施 | 每月节省 | 条件 |
|---|---:|---|
| `tms-uat-db` 退役（或只在测试时段开） | $99（约 $40） | 先补备份，找到连接方 |
| 3 台 UAT 按工作时段运行（约 30% 时长） | ~$86 | 确认测试和夜间任务时间 |
| TMS VM 改 E2 custom 4 核/24G | ~$155 | 可回退；先验证 JVM、OOM 和 FD |
| `tms-db` 8 核→6 核/39G | ~$181 | 可回退，重启几分钟；先压测或在低峰时段观察 |
| 迁走 `cp` 后释放 `wms-server`；释放 `nacos` 空盘 | ~$53 | 确认依赖并先快照 |
| 停止 TMS 日志增长 | 防止继续扩盘 | 每月少扩约 50 GB，约 $12/月且逐月累积 |
| **小计** | **约 $520–580（降 24–27%）** | |

### 4.2 视退役时间决定

| 措施 | 每月节省 | 判断标准 |
|---|---:|---|
| 日志清理并把 `tms-db` 存储缩到约 650 GB | ~$155 | 需要停机和重建；退役还在 6 个月以上才值得 |
| OTWMS VM 改 e2-standard-4（保留 16G） | ~$30 | 先解决实例反复重建；收益小 |
| `wms-db` 32→24G | ~$21 | 与退役无关，可随时做 |

都做到时合计约 **$720–780（降 33–36%）**。

### 4.3 不做

- **承诺折扣：** TMS/OTWMS 要退役，不能锁定一年。
- **迁移：** 已取消，议题关闭，后续不再评估（用户 2026-11-21 要求）。

### 4.4 退役后

- 新系统接手、数据归档后，可以释放：
  - `tms-db`、`tms-uat-db`
  - TMS、OTWMS 服务器和两台测试机
  - `wms-server`
  - `tms-redis`、`otwms-uat` Redis
  - TMS/WMS 入口规则
- GCP SQL+Compute 将从约 $2,184 降到约 **$360–450**（降 79–84%）。
- 是否达成 50% 目标，取决于新系统部署在哪里、费用多少。
- 退役前要处理：
  - 数据归档和保留期，包括 `ce-tms` 4.6 TB 文件。
  - XXL-JOB 的 OTWMS 任务。
  - Jenkins 发布任务。
  - 域名、API key。

## 5. 下一步

1. 审批 4.1 的措施，逐项执行，一次只改一项。
2. **待确认：**
   - 新系统预计上线和 TMS/OTWMS 退役的时间，决定 4.2 是否值得做。
   - 新系统部署在哪里，会不会增加 GCP 费用。
   - `ce-fileserver`、Redis `redis` 的归属。
   - `toucha-backend` 是否满盘。
   - OTWMS 实例反复重建的原因。
3. **两项之外的大头**（见 [28 项清单](../google-cloud/COST_OPTIMIZATION_CHECKLIST_2026-10-24.md)）：Geocoding $623、负载均衡转发规则 $208、Redis $145。
