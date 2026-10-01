# otwms-server

OTWMS 后端、前端、构建发布、XXL-JOB 和相关 Google Cloud 资源的故障定位记录。这里的 `server` 主要指运行 `BladeX.jar` 的 OTWMS 后端体系，同时记录直接影响 OTWMS 业务的前端存储事故；它不是 `wms-db` 上的 XXL-JOB 管理后台源码。

## 阅读顺序

1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：当前状态、风险和下一步。
2. [SOURCE_DEPLOYMENT_MAP.md](SOURCE_DEPLOYMENT_MAP.md)：Bitbucket、Jenkins、生产实例和 JAR 的精确映射。
3. [SOURCE_CODE_GUIDE.md](SOURCE_CODE_GUIDE.md)：前后端技术栈、包结构、XXL-JOB 清单、故障相关源码位置和源码风险。
4. [INCIDENT_2026-08-17_DAILY_BILL_QUERY_TIMEOUT.md](INCIDENT_2026-08-17_DAILY_BILL_QUERY_TIMEOUT.md)：任务 13 查询超时事故。
5. [INCIDENT_2026-08-22_UAT_I18N_LIFECYCLE_DELETE.md](INCIDENT_2026-08-22_UAT_I18N_LIFECYCLE_DELETE.md)：UAT 前端 i18n 被 Lifecycle 删除及软删除恢复。
6. [INCIDENT_2026-09-17_TMS_OUTAGE.md](INCIDENT_2026-09-17_TMS_OUTAGE.md)：OTWMS 受 TMS 中断影响；TMS 故障主记录见 [`tms-server`](../tms-server/README.md)。
7. [INCIDENT_2026-09-21_EXPORT_PRINT_DISK_FULL.md](INCIDENT_2026-09-21_EXPORT_PRINT_DISK_FULL.md)：Daily Report 导出与 Order Print 因磁盘/inode 满载失效。
8. [RUNBOOK.md](RUNBOOK.md)：SSH、日志、源码、构建产物和 Cloud Storage 的安全核对方法。
9. [reference/README.md](reference/README.md)：可复用诊断参考。

## 当前重点

- 生产根盘已从容量/inode 100% 紧急恢复到 22%/2%，导出与打印业务恢复；截至 `master` `5ba65f13f`（2026-09-22），XXL-JOB 保留期与 POI `dispose()` 仍未修复，日志轮转和实例模板容量也待处理。
- 日账单查询分批修复已于 2026-08-17 经 PR #2976 合并到 `master`；生产 JAR 是否包含该提交未核对，任务 13 尚未重跑。
- 修改前确认 `2026-08-15` 日账单是否存在部分结果，以及任务重跑是否幂等。
- 通过 Bitbucket 提交、Jenkins 构建和受控生产发布完成修复，不直接修改 Jenkins 工作区或生产 JAR。
- `otwms-frontend-uat/i18n/` 已从 7 天软删除保护中恢复；桶级 90 天 Lifecycle 已移除，重新配置前必须限定前缀并评估业务保留期。

## 本地源码

| 仓库 | 本地目录 | 当前分支 | 2026-10-01 HEAD |
|---|---|---|---|
| `OTWMS/otwms-backend` | `otwms-server/otwms-backend/` | `master` | `5ba65f13f` |
| `OTWMS/otwms-frontend` | `otwms-server/otwms-frontend/` | `master` | `4ec71efe6` |

两个目录是独立 Git 仓库，并由本目录 `.gitignore` 排除，不进入父级 `sens` 文档仓库。

## 安全边界

- 默认只读检查；部署、重启、数据库写入和任务重跑需要单独授权。
- 不保存密码、Token、私钥、完整数据库连接串或业务 shipment code。
