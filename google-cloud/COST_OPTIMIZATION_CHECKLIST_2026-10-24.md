# Google Cloud 成本优化清单

核查日期：**2026-10-24（柬埔寨时间）**。项目：`cambodian-express`。范围：9 月完整账单、当前资源、近 30 天监控、数据库大小元数据、对象存储年龄。**本次未停机、改配或删除业务数据；以下均为待评审建议。**

## 1. 结论与目标

- 9 月税前 **$3,704.77**，税费 **$370.48**，税后 **$4,075.25**。税后 $2,000 对应税前约 **$1,818.18**，需比 9 月减少约 **$1,886.59/月**。
- 最大机会是 **Geocoding 调用治理、Cloud SQL 日志/容量/规格、TMS 服务器规格、测试环境运行时段、重复公网入口**。单独停 WMS 约省税后 $46/月。
- 已找到两年前对象存储约 **2,591 GiB**，主要在 `ce-tms`；这是归档候选容量，不能直接当成可删数据。数据库接口日志物理表空间约 **716 GiB**，清理尚未完成。
- 平均利用率低不等于可直接减半：TMS 数据库 CPU 采样峰值 100%，缓冲池约 38 GiB；TMS VM 虽 CPU 很低，仍有约 15–17 GiB 的非缓存内存使用和历史故障。
- 10 月 1–23 日税前已发生 **$2,475.02**，月预测 **$3,404.62**；报表当前没有 Translate 收费行。9 月翻译费的下降已部分反映在 10 月趋势中，不能再次宣称为新操作节省。

### 目标预算：用于验收，不是已经验证可达的报价

| 类别 | 9 月税前实付 | 目标税前/月 | 相对 9 月减少 |
|---|---:|---:|---:|
| Cloud SQL | $1,115.78 | $625 | $490.78 |
| Compute Engine | $1,013.94 | $650 | $363.94 |
| Geocoding API | $673.77 | $150 | $523.77 |
| Translate | $287.21 | $0 | $287.21 |
| Networking | $263.67 | $160 | $103.67 |
| Cloud Storage | $156.08 | $100 | $56.08 |
| Redis | $140.02 | $95 | $45.02 |
| Monitoring | $36.64 | $25 | $11.64 |
| Storage Insights | $17.65 | $0 | $17.65 |
| **合计** | **$3,704.77** | **$1,805** | **$1,899.77** |

目标税后约 **$1,985.50**，距离 $2,000 仅有 $14.50 余量，实际落地应再预留增长缓冲。Translate/Insights 的零预算以业务确已停用为前提；如果仍需保留，必须从其他类别补足。若数据库/生产压测不允许降配，不能靠清理少量快照弥补数百美元缺口。

## 2. 入口索引

下表为当前项目入口；进入后再选择本清单的资源名。参数和页面布局可能变化。

| 编号 | 控制台入口 | 用途 |
|---|---|---|
| B | [账单报表](https://console.cloud.google.com/billing/01209E-555525-BB4F55/reports) | Last invoice by service/SKU、September 2026；当前月单独查看 |
| P | [价格表](https://console.cloud.google.com/billing/01209E-555525-BB4F55/pricing) | 核实账号实际 SKU 单价和折扣 |
| V | [VM 实例](https://console.cloud.google.com/compute/instances?project=cambodian-express) | 实例 → Observability/监控；改配前停机和恢复规划 |
| D | [磁盘](https://console.cloud.google.com/compute/disks?project=cambodian-express) | 挂载关系、磁盘类型与容量 |
| S | [快照](https://console.cloud.google.com/compute/snapshots?project=cambodian-express) | 恢复点、保留期、实际存储量 |
| Q | [Cloud SQL](https://console.cloud.google.com/sql/instances?project=cambodian-express) | 实例 → System insights、Query insights、Backups、Edit |
| R | [Redis](https://console.cloud.google.com/memorystore/redis/instances?project=cambodian-express) | 容量、连接、命令量和依赖确认 |
| L | [负载均衡](https://console.cloud.google.com/net-services/loadbalancing/list/loadBalancers?project=cambodian-express) | Frontends/Backends、域名规则、健康检查 |
| A | [API 使用](https://console.cloud.google.com/apis/dashboard?project=cambodian-express) | 30 days；选择 Geocoding/Translate，查看 Metrics 与 Quotas |
| K | [凭据](https://console.cloud.google.com/apis/credentials?project=cambodian-express) | API key 的应用/API 限制；本次未读取 key 值 |
| G | [存储桶](https://console.cloud.google.com/storage/browser?project=cambodian-express) | 对象、Lifecycle、Protection、版本/软删除 |
| I | [Storage Intelligence 配置](https://console.cloud.google.com/storage/storage-intelligence/configuration?project=cambodian-express) | 当前 Standard/Enabled；核对是否应停止或限制范围 |
| J | [Storage Insights](https://console.cloud.google.com/storage/storageinsights?project=cambodian-express) | 已有分析数据集、90 天保留、对象年龄分析 |
| M | [监控](https://console.cloud.google.com/monitoring?project=cambodian-express) | Metrics explorer、告警、指标采集量 |
| U | [预算](https://console.cloud.google.com/billing/01209E-555525-BB4F55/budgets) | 预算及异常告警；预算不是硬停机开关 |
| C | [GKE 集群](https://console.cloud.google.com/kubernetes/list/overview?project=cambodian-express) | `cluster-1` 工作负载、节点、持久卷 |

## 3. 资源使用证据

监控窗口约 9 月 24 日至 10 月 24 日。均值/P95 为**小时平均值**；采样峰值另外使用 `ALIGN_MAX`，不能把小时均值最大值称为瞬时峰值。共享核心 E2 可因突发出现超过 100% 的 CPU 指标，不能按普通专用核心比例理解。

### 服务器

| 实例 | 当前规格/启动盘 | CPU 均值 / 小时均值 P95 | 内存证据 | 建议 |
|---|---|---|---|---|
| TMS `tms-instance-template-20251103-082933` | C2 8 核/32 GiB，100 GB balanced | 1.1% / 1.6%；采样峰值 21.9% | used 小时均值约 48.4%，最大约 53.1%（约 17 GiB），另有文件缓存；历史 JVM 配置约 24 GiB | **重点压测候选**：4 核/24 GiB E2 custom，先调整 JVM/验证 OOM、并发和延迟；粗估省约 $159/月计算费 |
| OTWMS `otwms-group-fql0` | C2 4 核/16 GiB，50 GB balanced | 当前实例仅约 81 小时：3.2% / 4.5%；采样峰值 47.0% | used 约 55.8%，小时最大约 71.5%；旧实例曾接近 89% | 优先修复日志、镜像和内存；随后评估 E2 2 核/16 GiB，粗估省约 $69/月；变更应固化到实例模板 |
| `wms-db` | E2 highmem 4 核/32 GiB，500 GB standard | 12.3% / 20.5%；采样峰值约 100% | used 均值约 53.8%、小时最大约 57.8%（约 18.5 GiB） | 不能直接压到 16 GiB；若验证通过，可保留 4 核并改 24 GiB，粗估省约 $21/月 |
| `toucha-uat` | E2 2 核/8 GiB，300 GB balanced | 10.8% / 12.3%；采样峰值 22.5% | 本次无连续 agent 内存数据 | 官方建议改 `e2-custom-medium-7936`，月投影省 **$17.93**；或按时段启停，两方案不能叠加 |
| `tms-uat` | E2 medium/4 GiB，100 GB standard | 4.3% / 9.5% | used 小时最大约 83.3% | 优先按时段运行，不能仅凭 CPU 改成 2 GiB |
| `otwms-uat` | E2 medium/4 GiB，30 GB balanced | 16.5% / 20.4% | used 小时最大约 69.5%；有突发 CPU | 先确认测试/任务时段；不视为闲置 |
| `toucha-backend` | E2 medium/4 GiB，20 GB balanced | 7.7% / 9.3% | used 小时最大约 55.5% | 可查 JVM，但不优先将内存减半 |
| `ce-lb` | E2 custom 1 核/2 GiB，100 GB standard | 16.2% / 50.0%；采样峰值约 100% | used 小时最大约 81.6% | 官网、cp 和证书任务共享，经历日志事故；保留，先治理采集负担 |
| `wms-server` | E2 small/2 GiB，600 GB standard | 2.3% / 2.9% | SSH 当前根盘约 36 GB 已用；cewms 停、cp 运行 | 迁移后释放约 $41.49/月；若继续保留，迁到 100 GB 盘约省 $22/月磁盘费；两者互斥 |

VM 估价用 730 小时、账号 E2 CPU/RAM 单价；C2 参考 9 月约 20% 持续使用折扣后的计算费，不能用 C2 原价对比 E2 净价夸大节省。以上均未把其他项目共享网络费用重复分摊。

### 数据库、Redis 和集群

| 资源 | 实测 | 结论 |
|---|---|---|
| `tms-db` | 8 核/52 GiB；1,253 GiB SSD；当前约 1,195.5 GiB 已用（95.4%），余约 57.5 GiB，30 天增长约 12.7 GiB | 先控制日志和容量；不能在此余量下原地重建 716 GiB 大表 |
| `tms-db` CPU/内存 | CPU 均值 8.4%、小时均值 P95 16.4%，采样峰值 100%；RAM usage 约 44 GiB；InnoDB buffer pool 配置约 38 GiB，数据约 36.4 GiB；历史最大连接 126 | 降配必须含缓冲池、查询与 I/O 验证。6 核/39 GiB 或 4 核/26 GiB 只是实验候选，计算费理论分别省约 $177/$355/月 |
| `tms-uat-db` | 1 核/3.75 GiB；121 GiB SSD，约 50.8 GiB 已用；CPU 均值 12.6%、采样峰值 80.5%；平均约 73 个连接；自动备份关闭 | 有实际连接，不能按名称直接关；非工作时间停可省部分计算费；完全停用并释放磁盘约 $98/月，须先建立可恢复副本 |
| Redis `otwms-uat` | 1 GiB Basic；约 4.1 MiB 已用，平均约 15 个连接，有 GET/SET/MGET 等命令 | 容量很小但在使用；测试依赖迁移/停用后才可释放，约 $47.45/月 |
| Redis `tms-redis` | 1 GiB Basic；均值约 12.3 MiB，小时最大约 38.4 MiB，平均约 34 个连接；存在队列/列表相关命令 | 优先评估轻量自建或专用替代，不与测试 Redis 随意合并；潜在释放约 $47.45/月但要扣替代成本 |
| Redis `redis` | 1 GiB Basic；当前约 693 MiB，平均约 20 个连接 | 保留；容量利用率较高，不作为首批缩容项 |
| GKE `cluster-1` | 节点组目标数 0 | 9 月控制平面 $71.88 被 -$71.88 完全抵扣，净费 **$0**；清理属资源治理，不能宣称每月再省 $72 |

Cloud SQL 高内存使用包含数据库缓冲池，不能简单等同于不可减少的业务内存；同样不能忽略缓冲池缩小后的磁盘 I/O 和查询延迟。[内存说明](https://docs.cloud.google.com/sql/docs/mysql/optimize-high-memory-usage)。

## 4. 两年前数据与存储清理

截止边界为 **2024-10-24 00:00（UTC+7）**。对象元数据来自现有 Insights 最新快照 **2026-10-22 16:00 UTC**，存在采集延迟；统计单位是对象版本，不一定等于唯一业务文件。

| 候选 | 已确认容量/年龄 | 需要做的事 | 可降低费用 |
|---|---|---|---|
| `ce-tms` 对象 | 共约 4,518.8 GiB；两年前约 **8,287,861 个版本、2,536.8 GiB** | 先按文件用途/订单终态/结算争议/引用关系分类；决定删除、冷存或保留；按前缀小批量演练 | 如全部获准删除，标准存储约 **$50.6/月**；归档方案需另算检索、最低存储期及操作费 |
| `ce-fileserver` 对象 | 共约 1,149.4 GiB；两年前 **24,079 个版本、46.46 GiB** | 同上；不能因为时间老就删除仍被业务访问的附件 | 旧对象仅约 **$0.93/月**，不是主要节省项；重点分析其较新大文件 |
| 其他桶旧对象 | 主要为构建物、APP 内容、前端文件等；合计约 7.6 GiB | 保留当前发布引用和至少一个可靠回滚版本；静态文件时间老不等于失效 | 纯存储不到 $1/月，低优先级 |
| `sys_if_invoke_inbound` | 物理约 **716.37 GiB**，表级数据+索引统计约 **706.84 GiB**，最早仍为 **2022-11-18** | 先冻结截止时间，评审保留需求；复核索引、binlog/undo、备份；用现有脚本分日限额清理，另外验证物理重建与缩容 | 每真正减少 **100 GiB 计费 SSD** 约省 **$23.80/月**；本次不能量化超期行的可回收字节 |
| `otwms.station_letter` | 物理约 **44.38 GiB**，表级统计约 **4.18 GiB** | 先核对保留任务与索引，在克隆环境验证重建；不是再增加盲目删除 | 差额约 40 GiB 是候选，不是保证回收量；实际计费容量下调后才省钱 |
| `otwms.external_interface_log` | 物理约 **16.0 GiB** | 设置明确保留期，成功报文精简，敏感头脱敏；不要以永久全报文做审计默认值 | 单表节省有限，但可抑制持续增长 |
| `tms_shipment_revenue_cost_lt_2024` / `daily_bill_item_bk` | 表级约 **6.34 / 3.48 GiB** | 检查代码、报表、结算和审计引用；确认后归档 | 不能按表名或年份直接删除 |
| 快照/镜像 | 45 个快照，计量存储合计约 **71.07 GiB**；唯一两年前快照 `tms-customer-for-uat` 约 **9.57 GiB**；3 个镜像 | 列明负责人、恢复用途、保留期，删除需逐项确认 | 所有快照存储大致每月数美元；不宜为少量节省牺牲唯一恢复点 |

**修正旧判断：** 9 月曾见接口日志表级统计约 238 GiB，本次已约 707 GiB；不能继续使用“716−238≈478 GiB 可回收”的假设。InnoDB 表行数和尺寸统计会变化，不以估算行数推算精确删除量。

数据库原清理于 9 月 28 日已删除约 211 万条后暂停，本次未重新进行千万级 COUNT 或删除。后续沿用 [两年日志计划](TMS_INBOUND_LOG_CLEANUP_PLAN.md)，每轮重新核实备份与停止阈值。

**降低 Cloud SQL 存储账单的完整链路：** 删除/归档 → 验证物理空间回收 → 保留必要余量 → 检查实例存储缩容资格 → 窗口内缩容或迁至较小实例 → 核对新计费容量。当前官方支持符合条件的存储缩容，可能有明显停机；建议保留约 100 GB 或已用量 20% 的较大值。不能按旧文档笼统认定永远不能缩容。[官方说明](https://docs.cloud.google.com/sql/docs/mysql/about-storage-shrink)。

## 5. 完整待办清单

金额均为 **税前/月**。`P0` 为首先取证/遏制增长，`P1` 为先执行的成本候选，`P2` 为需压测或迁移的方案，`P3` 为低收益治理。没有一项因列在此表就自动获得修改或删除授权。

| ID / 优先级 | 资源与具体待办 | 节省测算与条件 | 入口 |
|---|---|---|---|
| 01 / P0 | Geocoding：按 key/调用系统定位来源；检查同地址重复请求、页面触发、重试；先加告警，再调整测试配额 | 9 月 $673.77；目标 $150，对 9 月最多约省 $524；当前约 13.7–13.8 万次/30 天仍在调用 | [API](https://console.cloud.google.com/apis/api/geocoding-backend.googleapis.com/metrics?project=cambodian-express)、A、K |
| 02 / P0 | 13 个 API key 中 5 个未设置任何限制；其余也有仅限制 API、未限制应用的情况。建立应用/负责人/环境映射，再逐个收紧与监控 | 费用防护；本次不能证明存在盗用。限制误配会中断业务，不直接批量改 key | K |
| 03 / P1 | Translate：查明 9 月来源，核对 10 月无收费行是否为业务调整；补去重、内容哈希和失败重试上限 | 9 月 $287.21；若持续不再调用则较 9 月减少该费用，**属于趋势，不重复算新增工程收益** | A、K、B |
| 04 / P0 | TMS 日志写入减量：先定位重复大响应、原文保留需求与审计字段；对历史清理设每日上限、binlog余量/锁等待停止阈值 | 不直接承诺立即省钱；避免 95.4% 磁盘继续自动扩容 | Q、日志计划 |
| 05 / P2 | `tms-db`：克隆压测 6 核/39 GiB，再视指标评估 4 核/26 GiB；配套缓冲池、慢查询和连接配置 | 计算费理论省 **$177–355**；高峰 CPU/缓存命中率、读 I/O、p95/p99 延迟不通过则保留原规格 | Q → `tms-db` → Query insights/Edit |
| 06 / P2 | 清理/重建后测算 Cloud SQL 最小安全盘，再执行有资格的存储缩容或迁移 | 每 100 GiB **$23.80**；目标额以克隆实测为准，暂不把全部日志表容量当节省 | Q |
| 07 / P1 | `tms-uat-db`：找出约 73 个平均连接的所有者；补可恢复备份；可按测试时段停，彻底退役才删除盘 | 全月停止约省 **$69** 计算；退役另省 **$28.80** 存储；按工作时段仅部分节省 | Q → `tms-uat-db` |
| 08 / P2 | TMS VM：压测 E2 custom 4 核/24 GiB，调整 JVM 堆并验证原 OOM/FD/超时问题；保存旧规格回滚 | 约 **$159** 计算费，尚未实施或证明压测可通过 | V → TMS |
| 09 / P2 | OTWMS：先修复/固化日志轮转、镜像与临时文件；压测 E2 2 核/16 GiB | 约 **$69** 计算费；不能按当前新实例 81 小时数据声称已有 30 天稳定性证据 | V → 实例组 `otwms-group` |
| 10 / P1 | `tms-uat`、`otwms-uat`、`toucha-uat`：核对测试、夜间任务、外部回调和发布日历，决定定时开关 | 三台计算全月约 $120.69；若每月仅 22 天×8 小时运行，约省 **$91.59**，磁盘/LB 仍收费 | V → Instance schedules |
| 11 / P1 | `toucha-uat` 如必须常开，采用官方建议保留约 7.75 GiB 内存、降低 CPU | 官方投影 **$17.93**；与 10 的该实例时段收益互斥/需重算 | V → Recommendations |
| 12 / P2 | `wms-db` 保留 4 CPU，验证能否 32→24 GiB；核查 Jenkins 构建峰值 | 约 **$21**；与 Jira/Bitbucket/MySQL 共机，不能直接缩到 16 GiB | V → `wms-db` |
| 13 / P1 | `nacos` 未挂载的 100 GB balanced 盘：确认恢复用途与现有备份，按批准方案释放 | 原盘单价粗估 $11；官方“快照后删除”**净投影约 $4.74**，本清单采用净值 | D → `nacos` |
| 14 / P2 | WMS/cp：迁移后释放 VM/盘，或保留实例并迁至较小盘 | 全释放约 **$41.49**；600→100 GB 仅盘约 **$22**；互斥，不应重复相加 | V/D、[专项估算](../otwms-wms-server/MIGRATION_COST_ESTIMATE_2026-10-24.md) |
| 15 / P1 | 核查 `nacos-lb`、`ngrok-lb`、`chatwoot-uat-lb` 的负责人、后端和 DNS；确认退役后清理各自 HTTP/HTTPS 规则 | 3 对固定规则约 **$43.80**；不能把失败请求当零业务，需先确认 | L |
| 16 / P2 | 整合其他多域名入口；对 UAT 停用后的规则、代理、地址、后端逐项核对，保留正在用的证书/CDN/路由 | 现有档位每少一对规则约 **$14.60**；与 15 重叠部分不再加。全项目 9 月固定规则共 **$218.87** | L |
| 17 / P1 | 完成 `ce-tms` 两年前对象用途和引用清单，先归档/恢复演练，再按批准前缀处理 | 已量化旧容量按标准存储约 **$50.6**；归档/删除为替代方案，不叠加；操作费另计 | G → `ce-tms`、J |
| 18 / P1 | 检查 Storage Intelligence 的实际使用者；分析完成后选择关闭 Standard 或收窄桶范围 | 9 月 **$36.09** 对象管理费；若保留功能，仅删除旧对象也会降低其对象计费，但不能再与全关闭收益相加 | I |
| 19 / P1 | Insights 数据集 `project_2026_01_12_20_39_03` 保留期当前 90 天；评估 7–30 天或停止不需要的数据集刷新 | 9 月 **$17.65**，降至 30 天粗估省约 $11.8；完全停止/清理才可能接近全额，历史数据在到期前仍可能收费 | J → 数据集详情 |
| 20 / P2 | `ce-fileserver`/前端桶：按新旧容量、软删除、发布引用制定生命周期；`otwms-frontend` 软删除当前 90 天 | 旧 fileserver 对象不到 $1/月；不是一律 Delete(age>730)。90 天软删除当前仅约 0.1 GiB，不夸大其节省 | G |
| 21 / P1 | Redis `otwms-uat` 随测试环境退役或迁移；保留恢复/配置方案 | **$47.45**；不能通过停止调用或禁用 Redis API 来停止资源计费 | R |
| 22 / P2 | Redis `tms-redis` 评估专用轻量替代；队列、锁、重启恢复和持久性验收后切换 | 原托管费 **$47.45**，扣替代实例/运维成本；不能直接清空或并入测试 | R |
| 23 / P1 | 监控：按 agent/metric 找出高基数或无用途的付费指标；保留故障与容量告警 | 9 月 **$36.64**，10 月趋势已下降；新增省额需按当期算，初步目标 $25/月 | M |
| 24 / P3 | 快照/镜像归档，确认旧 `tms-customer-for-uat`、旧镜像与模板的恢复关系 | 存储仅数美元；没有恢复替代就保留 | S、V → Instance templates |
| 25 / P3 | 清理空 GKE/旧目标为 0 的 `tms-group` 的残留引用；核对所有公网 IP 与 NAT 用途 | GKE 当前净 $0；实例组本身无活跃 VM，不把模板/目标 0 当运行费 | C、V、L |
| 26 / P1 | 完成 VM 时段/入口整合后再核对公网 IP、NAT 和 Cloud Armor 策略 | VM IPv4 9 月全项目 $21.54；只有实际释放/变更计费状态才降低，不能将所有 19 个地址都算闲置 | V、L、B |
| 27 / P0 | 配税前约 $1,818 的预算、50/75/90/100% 告警；按服务分别设负责人和周度费用检查 | 管理措施，**不产生直接节省、不自动限制消费** | U、B |
| 28 / P2 | 降配后运行稳定、工作负载长期保留时才评估承诺折扣 | 当前区域计算承诺列表为空；先定最终容量再签，避免把将迁走的资源锁成长期费用 | B → CUD analysis |

Geocoding 优化先做去重、触发条件和重试治理；缓存遵守服务允许的字段和期限，坐标可临时缓存最多 30 天，不采用无期限保存全部响应的方案。[服务条款](https://cloud.google.com/maps-platform/terms/maps-service-terms)。

## 6. 执行顺序、验收与回滚

### 第一批：费用归属和低风险候选（建议 1 周内）

- [ ] 01/02/03：给 Geocoding、Translate 的 key 标记来源与负责人，核实每日用量；先告警，再对测试/重复调用做限制。
- [ ] 13/15：核实未挂盘与 3 套疑似旧入口；特别检查历史域名、外部调用和 DNS，形成逐项退役审批表。
- [ ] 17/18/19：保存这次存储年龄汇总；先明确分析功能是否有持续用途，再选关闭或收窄；不要先关闭分析再失去归档依据。
- [ ] 10/07/21：与测试使用方确认运行时段，生成 VM/数据库/Redis 各自的可恢复方案。测试库备份当前关闭，先补恢复能力。
- [ ] 27：建立预算和每周费用基线。

### 第二批：生产性能与数据治理（建议 2–4 周）

- [ ] 对 TMS VM、OTWMS VM、Cloud SQL 分别做压测和恢复演练；一次只改一个维度，不能同时缩 VM、数据库和 Redis 后无法归因。
- [ ] TMS VM 重点检查 JVM 堆、GC、FD、任务峰值和原超时；OTWMS 先验证日志修复已在当前模板生效。
- [ ] SQL 在克隆环境重建候选表，记录实际大小、耗时、锁与额外空间；以实测制定缩盘目标。生产约 57.5 GiB 余量不适合直接尝试 716 GiB 重建。
- [ ] 对象归档先做小范围导出、校验和恢复抽查，再处理已获准范围；保留终态、结算、客服和报表追溯依赖。
- [ ] 入口整合必须验证 HTTPS、证书续期、CDN、健康检查、API 和旧域名兼容；保留原 URL map/证书配置与 DNS 回滚值。

### 成功标准

- 业务：关键接口、夜间任务、报表/打印、登录和旧附件访问通过；p95/p99 延迟、错误率、GC/重启、数据库读 I/O 无持续劣化。
- 数据：截止边界/用途/容量可追踪，归档校验通过，可按清单恢复；只清理批准的类别。
- 资源：核对计费规格、已分配盘容量、转发规则和实际存储量；不把 `DELETE` 成功或 VM 停止当作全部费用停止。
- 财务：新方案稳定后，以后续两个完整账期验收税后 ≤$2,000；每周记录实付、预测和相对 9 月变化。重建/迁移期间的双实例、备份、查询和出流量作为一次性费用单列。
- 恢复：VM 回原规格并恢复 JVM/模板；数据库恢复可能需新实例，已提交删除不能直接事务撤销；归档可在约定时间内找回对象。

## 7. 证据、限制与复用

- 控制台直接查看：9 月服务/SKU 报表、10 月趋势、VM 列表与官方降配提示、SQL 30 天图、API 30 天用量、存储桶、Storage Intelligence/Insights、负载均衡列表。
- API/CLI：9 VM、10 磁盘、45 快照、3 镜像、19 个地址（16 全局/3 区域）、33 条转发规则、2 SQL、3 Redis、17 bucket、1 个节点组为 0 的 GKE 集群、3 个 managed groups。19 个地址均有引用；并非闲置地址清单。
- 30 天监控和只读 SQL/对象年龄汇总见 [证据 JSON](records/cost-audit-2026-10-24.json)。数据库只查表空间/元数据和索引首尾时间，没有读取客户报文或运行大表全量计数。
- 两年前对象按创建/更新时间，不等同于两年未访问；尚未与业务表全量对账。Insights 的 `live_or_noncurrent` 未进一步区分当前版本和非当前版本；实际清理前须精确列出版本与引用。
- 未确认事项：Geocoding/Translate 每个 key 的业务归属；所有对象/旧入口的业务所有者；全部应用的分钟级内存尖峰和压测结果；数据库重建实际可回收量。没有将这些不确定性写成可直接停用结论。
- 复用：新增默认只读 [cloud_cost_audit.py](scripts/cloud_cost_audit.py)，保留 [对象年龄汇总 SQL](scripts/storage_age_summary.sql)。脚本运行完成，无采集失败；不新增重复 Skill。对象年龄查询先 dry-run，执行时硬限制 55 GB 计费扫描量，查询仅返回按桶的数量/容量汇总。
- 本文替代 [10 月 17 日初步计划](COST_REDUCTION_PLAN_2026-10-17.md) 中有关资源利用率、旧数据、GKE 净费用和存储缩容的未核实假设；单实例 WMS 成本估算另见其子项目。
