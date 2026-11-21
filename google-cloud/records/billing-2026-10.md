# 2026 年 10 月账单明细（税前）

来源：Chrome 控制台 Billing → Reports，`Last month`，按 Service 和 SKU 分组，读取于 2026-11-21（UTC+7）。期间 2026-10-01 至 10-31。报表未显示税额；9 月发票税率为 10%。

## 按服务

| 服务 | 使用费 | 抵扣 | 小计 |
|---|---:|---:|---:|
| Cloud SQL | $1,143.78 | — | **$1,143.78** |
| Compute Engine | $1,155.53 | -$115.32（持续使用折扣） | **$1,040.21** |
| Geocoding API | $622.74 | — | $622.74 |
| Networking | $299.95 | -$27.53 | $272.42 |
| Cloud Storage | $154.37 | — | $154.37 |
| Memorystore Redis | $145.08 | — | $145.08 |
| Cloud Monitoring | $38.74 | — | $38.74 |
| Storage Insights | $18.23 | — | $18.23 |
| Cloud Logging（新增） | $10.82 | — | $10.82 |
| VM Manager、GKE 控制平面等 | — | 全额抵扣 | $0 |
| **合计** | | 抵扣共 -$223.95 | **$3,446.41** |

与 9 月相比下降 $453.78（-11.63%），主要原因是 Translate（Neural Translation）减少 $381.22，10 月为 $0。

## Cloud SQL 和 Compute 主要 SKU

| SKU | 用量 | 小计 | 折算单价 |
|---|---:|---:|---:|
| SQL Zonal RAM | 41,478 GiB·h | $406.48 | $0.0098/GiB·h |
| SQL Zonal vCPU | 6,696 h | $387.03 | $0.0578/h |
| SQL SSD 存储 | 1,376.7 GiB·月 | $327.65 | $0.238/GiB·月 |
| SQL 备份 | 199.26 GiB·月 | $22.32 | |
| C2 Core | 8,928.82 h | $299.47（已扣折扣） | |
| C2 RAM | 35,715 GiB·h | $160.52（已扣折扣） | |
| E2 Core | 7,066.66 h | $190.16 | $0.0269/h |
| E2 RAM | 40,170.68 GiB·h | $144.85 | $0.0036/GiB·h |
| E2 Custom Core / RAM | 744 h / 1,488 GiB·h | $21.02 / $5.63 | |
| Balanced PD | 600 GiB·月 | $66.00 | $0.11 |
| Standard PD | 1,300 GiB·月 | $57.20 | $0.044 |
| 出网到亚太 | 510 GiB | $61.21 | |
| VM 外部 IP | 5,207 h | $22.31 | |
| 快照、镜像 | — | 约 $10.2 | |

其他较大的 SKU：
- 负载均衡转发规则附加费：$208.32
- 最低收费：$18.60
- Redis Basic M1：$145.08
- 标准存储 5,656 GiB：$113.12
- Storage Intelligence：$35.97
- Cloud Armor：$15 + $6 + $2.15

Geocoding 10 月共 143,185 次。
