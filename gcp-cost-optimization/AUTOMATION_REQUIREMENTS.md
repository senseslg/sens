# Skill 与脚本需求

2026-10-26 复用评估：已有云审查与服务器检查工具，当前仅完成规划，暂不新建重复 Skill/脚本。后续在实际重复检查形成稳定步骤后按需新增。

## 优先复用

| 场景 | 现有入口 | 使用要求 |
|---|---|---|
| 云资源与近 30 天指标 | [cloud_cost_audit.py](../google-cloud/scripts/cloud_cost_audit.py)、[Runbook](../google-cloud/RUNBOOK.md) | 先检查当前参数/权限与采集范围，核对所有失败项；本轮未运行 |
| 对象年龄汇总 | [storage_age_summary.sql](../google-cloud/scripts/storage_age_summary.sql) | 核对数据集和冻结日期，先 dry-run 并限制计费扫描量 |
| 服务业务健康 | [服务器索引](../SENS_SERVER.md) 及所属服务 Runbook | 读取当前正式入口，只运行适用的只读检查 |
| OTWMS 磁盘风险 | [check_disk_pressure.py](../otwms-server/scripts/check_disk_pressure.py) | 核对活动实例；不调用恢复/截断脚本作为巡检 |

## 后续候选

- API key 脱敏归属清单：只输出 key 资源标识、应用/API 限制、环境与用量，禁止读取/输出 key 值。
- 每次变更前后指标对比：统一时间窗口、错误/缺失状态、业务检查与原清单 ID。
- 成本台账汇总：区分净节省、自然趋势、互斥方案、双运行费用及两个完整账期。

候选均未实现；根据首轮实际取证验证需求，能复用就不重写。

## 新工具约定

- 脚本放 `scripts/`；项目专用 Skill 放 `skills/<name>/SKILL.md`，创建时读取 `skill-creator`。
- 默认只读，参数化项目/资源/时间/输出位置；变更工具单独实现且默认 dry-run。
- JSON 输出包含采集时间、来源、成功/失败/缺失状态；退出码 0=完整成功，2=部分失败，1=失败。
- 不硬编码凭证或生产服务器地址；异常只报告，不自动修复。说明调用频率、超时、成本和边界。
- 新工具须按实际风险验证，记录验证结果与适用限制后再作为固定流程；不自动安装到全局或创建定时任务。
