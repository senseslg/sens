# otwms-server

OTWMS Java 后端的源码、构建、生产部署、XXL-JOB 执行和故障定位记录。这里的 `server` 指运行 `BladeX.jar` 的 OTWMS 后端体系，不是 `wms-db` 上的 XXL-JOB 管理后台。

## 阅读顺序

1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：当前状态、风险和下一步。
2. [SOURCE_DEPLOYMENT_MAP.md](SOURCE_DEPLOYMENT_MAP.md)：Bitbucket、Jenkins、生产实例和 JAR 的精确映射。
3. [INCIDENT_2026-08-17_DAILY_BILL_QUERY_TIMEOUT.md](INCIDENT_2026-08-17_DAILY_BILL_QUERY_TIMEOUT.md)：任务 13 查询超时事故。
4. [RUNBOOK.md](RUNBOOK.md)：SSH、日志、源码与构建产物的只读核对方法。
5. [reference/README.md](reference/README.md)：可复用诊断参考。

## 当前重点

- 在 `TmsShipmentRevenueCostServiceImpl.getShipmentRevenueCosts()` 中对 shipment code 分批查询，避免超大 `IN` 触发全表扫描。
- 修改前确认 `2026-08-15` 日账单是否存在部分结果，以及任务重跑是否幂等。
- 通过 Bitbucket 提交、Jenkins 构建和受控生产发布完成修复，不直接修改 Jenkins 工作区或生产 JAR。

## 本地源码

| 仓库 | 本地目录 | 当前分支 |
|---|---|---|
| `OTWMS/otwms-backend` | `otwms-server/otwms-backend/` | `master` |
| `OTWMS/otwms-frontend` | `otwms-server/otwms-frontend/` | `master` |

两个目录是独立 Git 仓库，并由本目录 `.gitignore` 排除，不进入父级 `sens` 文档仓库。

## 安全边界

- 默认只读检查；部署、重启、数据库写入和任务重跑需要单独授权。
- 不保存密码、Token、私钥、完整数据库连接串或业务 shipment code。
