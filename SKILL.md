# Project Skills

本文件是当前仓库的可复用工作流程索引。开始前先阅读 `PROJECT_READ_FIRST.md`，再按任务类型打开对应参考文件。

## Available skills

| 流程 | 文件 | 使用场景 |
|---|---|---|
| 长期沟通与上下文沉淀 | [reference/communication-protocol.md](reference/communication-protocol.md) | 从自然语言沟通中提炼事实、决定、行动项、风险和待确认事项 |
| 记录维护 | [reference/record-maintenance.md](reference/record-maintenance.md) | 新建或更新总览、迭代日志、项目、每日或会议记录 |
| 工作项生命周期 | [reference/work-item-lifecycle.md](reference/work-item-lifecycle.md) | 接收、推进、暂停、完成或归档一个持续工作项 |
| CCSL 服务器基线 | [new-ccsl-server/scripts/server_baseline.py](new-ccsl-server/scripts/server_baseline.py) | 通过 SSH 或服务器本机采集脱敏的系统、磁盘、服务、端口与 Java 基线 |
| CCSL Jenkins 发布验证 | [new-ccsl-server/scripts/verify_deployment.py](new-ccsl-server/scripts/verify_deployment.py) | 核对产物、进程启动时间、端口、HTTP 入口和发布后致命日志信号 |
| OTWMS 磁盘压力巡检 | [otwms-server/scripts/check_disk_pressure.py](otwms-server/scripts/check_disk_pressure.py) | OTWMS 导出、打印或任务写入异常时，只读检查容量、inode、大日志、临时文件和 HTTP |
| OTWMS 磁盘修复专项回归 | [otwms-server/scripts/verify_disk_fixes.py](otwms-server/scripts/verify_disk_fixes.py) | 本地验证 POI 清理、旧版 Logback 轮转 XML 和巡检分级，不连接业务服务；不替代完整构建 |
| Jira 解决日期报表导出 | [wms-db/jira-service/RUNBOOK.md](wms-db/jira-service/RUNBOOK.md) | 用 export_report.py 按月份或日期区间生成 8 列 CSV；需本机 API 服务，暂未生成独立 Skill |

## 使用规则

- 所有流程说明和执行记录必须简短、明确、可快速扫描；先给结论和适用场景，再给必要步骤与边界。
- Playbook 提供默认顺序，但不能替代读取当前文件和核对真实状态。
- 新流程只有在重复出现并形成稳定步骤后才加入本索引。
- 一次性任务留在对应记录中，不包装成通用流程。
- 如果实际做法与 playbook 不一致，先确认原因，再更新文档或明确例外。
- 稳定且会重复执行的命令流程应实现为项目内 Python 脚本；脚本默认只读、脱敏、参数化，并用退出码或 JSON 提供可复核结果。
- 生产服务器地址和凭证不得硬编码到脚本。需要修改远端状态的自动化必须与只读检查分离，并明确授权、影响与回滚。
