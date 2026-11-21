# OTWMS 开发上线工作流

适用于 `OTWMS/otwms-backend`（前端同理，替换任务名）。参考 `new_ccsl/GIT_WORKFLOW.md` 制定，2026-11-21 起执行。合并与部署由用户在 Bitbucket / Jenkins 完成；agent 负责开发、部署前后处理、测试核对和记录。**写库（UAT 与生产）每一步都需用户当次授权。**

## 仓库边界

- 公司仓库只放功能代码和对应测试；提交信息以 Jira 号开头（如 `CE-2644 …`），不写运单号、个人排查过程。
- 个人记录（事件、Runbook、本文件）只在个人仓库 `sens`（GitHub）。公司 checkout 内的本地文件用 `.git/info/exclude` 排除，不改公司 `.gitignore`。
- 提交前逐个确认暂存文件，不用 `git add -A`。

## 流程

| 步骤 | 环境 | 内容 |
|---|---|---|
| 1 建单 | — | `wms-db/jira-service` 在 CE 项目建单（模块 OTWMS后端/前端，先 `dry_run`），用完即停服务 |
| 2 开发 | 本地 | `git fetch` 后从 `origin/master` 用 worktree 开 `fix/CE-xxxx-简述` 或 `feature/…`（目录 `otwms-server/otwms-backend-CE-xxxx/`，父仓库已忽略）；去掉对 master 的上游跟踪 |
| 3 本地验证 | 本地 | 本机缺依赖**不做完整编译**；只做独立单测、API/版本核对，交付时注明“待 UAT 构建验证” |
| 4 提交推送 | — | 用户确认后推送功能分支；用户在 Bitbucket 合并到 `qa` |
| 5 确认 UAT 版本 | UAT | 用户在 Jenkins 部署 `otwms/uat/otwms-backend-uat`；agent 用 `jenkins_builds.py list/log` 核对构建结果和 `Checking out Revision`，并 `git merge-base --is-ancestor <提交> origin/qa` |
| 6 UAT 前后处理 | UAT | 需要的 SQL（DDL、配置）在部署前/后执行并只读核对；数据源取 `application-test.yml` |
| 7 UAT 业务测试 | UAT | 只测本人分支（`origin/qa` 中未进 master 的本人提交）；按业务流程验证，并用数据库核对结果和“不应变化的数据” |
| 8 验收报告 | — | 每个用例：操作、样本、预期、实际、结论；无法覆盖的部分单列 |
| 9 建议上线 | — | 告诉用户合并哪个**功能分支**到 `master`（不合 qa），列出生产前后处理 |
| 10 生产前后处理 | 生产 | 用户授权后执行，执行后只读核对；删除类操作再次确认 |
| 11 生产检查 | 生产 | 用户部署 `otwms/prod/otwms-backend` 后：核对构建检出提交；只读查库；需要时经授权 SSH 读任务日志（脱敏） |
| 12 收尾 | — | Jira 关闭（jira-service `/requirements/{key}/close` 先 `dry_run`，解决结果“完成”）；更新事件记录、`PROJECT_ITERATION_LOG.md`，可复用操作整理为脚本 |
| 13 复查 | 生产 | 上线后约 24 h、48 h 只读复查，结果写入事件记录并勾掉待办 |

## 环境要点

- **数据库**：UAT 用 `application-test.yml`，生产用 `application-prod.yml`（共享 Cloud SQL `tms-db`，schema `otwms` 与 `tms_uat`；`tms_uat` 名字不代表 UAT）。连接后先确认主机/库，再操作；只读会话加 `max_execution_time`，大表先看索引和 `EXPLAIN`。
- **生产写库**：事务内执行，条件限定当前值，校验影响行数与预期一致才提交，否则回滚；先导出变更前的值到临时目录。
- **服务器**：生产实例 `otwms-group-*`（名称会变，`gcloud compute instances list` 确认），任务日志 `/tmp/<日期>/<log-id>.log`，见 [Runbook](RUNBOOK.md#任务日志)。`otwms-uat` 当前账号 SSH 被拒（publickey），UAT 进程/日志需用户提供或授权。
- **XXL-JOB 任务**：UAT 与生产任务启停状态可能不同。2026-11-21 发现 UAT `syncShipmentJobHandler` 未运行（同步水位停在 08-31），测试依赖定时任务时先确认 UAT 任务已启用或请用户手动触发。
- **Jenkins**：`otwms/uat/otwms-backend-uat`、`otwms/prod/otwms-backend`，前端 `otwms-frontend-uat`、`otwms-frontend-prod`；只读脚本 `jenkins-service/scripts/jenkins_builds.py`。
