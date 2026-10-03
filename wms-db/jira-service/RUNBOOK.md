# Jira 需求服务 Runbook

适用于本机服务 0.3.0。当前能力与验证边界见 [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)。

## 启动与认证

```bash
cd /Users/lingang/sens/wms-db/jira-service
python3 -m pip install -r requirements.txt
python3 setup_local.py
# 在本机编辑 .local/config.json，填写 JIRA_PASSWORD；不要在聊天或 Git 中保存密码。
python3 run.py
```

- 当前环境已安装 FastAPI/uvicorn，无需重复安装。
- 配置在 Git 忽略的 `.local/config.json`，权限必须为 `600`；初始化生成本地服务密钥，不修改 Jira 账号。默认用户名 `sens`。
- 接口地址 `http://127.0.0.1:8765`，交互文档 `/docs`。点击文档页面 Authorize，填入配置中的 `JIRA_SERVICE_API_KEY`；该密钥只用于本地服务，不是 Jira Token。
- 部署位置：用户本机 Mac 的 `/Users/lingang/sens/wms-db/jira-service`，通过 HTTPS 调用 GCP 上的 Jira；不在 `wms-db` 或其他生产服务器部署。当前为终端进程，休眠期间不可用，关机或进程退出后需重新启动；未配置常驻服务。
- 所有业务接口需要 `X-API-Key`，仅健康与接口说明无需认证。仅监听本机，暂不对外发布。
- 可用同名环境变量覆盖文件配置；`JIRA_SERVICE_PORT` 可调整端口。

## 接口

| 方法与路径 | 用途 |
|---|---|
| `GET /health` | 本地健康和凭据是否配置；不代表 Jira 健康 |
| `GET /projects` | 当前账号可见项目 |
| `GET /projects/{project}/metadata` | 类型、创建字段、必填项及允许值；可传 `issue_type_id` |
| `GET /fields` | Jira 字段目录 |
| `GET /resolutions` | Jira 解决结果目录 |
| `POST /requirements` | 默认预检查；`dry_run=false` 才提交，需 `Idempotency-Key` |
| `POST /requirements/query` | JQL 分页查询和项目/状态/类型/经办人计数 |
| `POST /requirements/export` | CSV 导出，默认自选字段；`all_fields=true` 获取全部 API 字段 |
| `POST /reports/resolved/export` | 按解决日期导出周报/月报固定 8 列 |
| `GET /requirements/{issue_key}/transitions` | 当前状态和账号允许的工作流动作/字段 |
| `POST /requirements/{issue_key}/close` | 预检查或提交结束状态转换，并在同一次请求记录原因 |

### 创建请求

以下为 CCSL 任务示例（2026-10-03 的字段快照）；使用前查询 metadata 获取真实类型及必填项，不预设任务或故事。描述建议包含背景、路径、目标行为、验收条件和范围。

```json
{
  "project": "CCSL",
  "issue_type_id": "10300",
  "summary": "替换为真实需求标题",
  "description": "h3. 背景\n...\nh3. 目标行为\n...\nh3. 验收条件\n...",
  "assignee": "sens",
  "labels": [],
  "extra_fields": {"reporter": {"name": "sens"}},
  "dry_run": true
}
```

支持 `assignee`（用户名）、`priority_id` 和自定义字段 `extra_fields`。预检查只校验字段存在性和必填项，实际值及权限由 Jira 提交时校验。

CCSL 当前“任务”类型 ID 为 `10300`，报告人必填；例如 `extra_fields: {"reporter": {"name": "sens"}}`。其他项目仍需查询 metadata。

实际提交时为该逻辑请求选一个唯一 `Idempotency-Key`，之后重试保持同键和同内容。服务保存摘要、状态和需求编号，不保存完整需求正文。相同键成功重试返回原编号，不再创建；内容不同返回 409。超时或崩溃可能留下 `pending/unknown`，此时先查 Jira，不能换键直接重试。首版尚无人工核对后的恢复接口。

### 关闭或不做

先 GET transitions，选择实际允许的动作，并确认解决结果。接口不自动猜测状态 ID，不删除需求；仅允许结束类别的目标状态。`wont_do` 不允许采用“完成/已修复”等解决结果。

CCSL-2679 当前只读检查显示：关闭动作 `2`，目标状态 `6`（已关闭），解决结果 `10001`（Won't Do）。ID 是该需求当前工作流快照，其他项目/状态必须重新查询。

```json
{
  "transition_id": "2",
  "reason": "填写用户决定不做的实际原因",
  "intent": "wont_do",
  "resolution_id": "10001",
  "expected_status_id": "1",
  "dry_run": true
}
```

仅 `dry_run=false` 会写入，实际提交必须带 `Idempotency-Key` 和预检查得到的 `expected_status_id`。原因以备注与状态转换一起提交；成功后核对状态和显式解决结果。状态变化返回 409，超时不自动重试。提交前查询不能完全消除 Jira 并发变更，最终规则由 Jira 校验。

`intent=close` 用于明确关闭；需要报告用户确认的解决结果，不能把“不做”当作完成。工作流可能有自定义后置动作；读回不匹配时明确返回 `verified=false`，先人工核对。此功能开发授权不等于授权取消任意需求，实际操作需用户指定编号与原因。

### 汇总与 CSV

```json
{
  "jql": "project = CCSL AND resolution = Unresolved ORDER BY key ASC",
  "limit": 1000,
  "fields": ["summary", "description", "status", "assignee", "created"],
  "column_names": {"key": "需求编号", "summary": "标题", "description": "描述"},
  "all_fields": false
}
```

上例用于 export；query 使用 `jql`、`limit`、`fields`。`all_fields=true` 忽略字段选择，列名包含 Jira 名称和字段 ID，避免同名字段混淆。复杂对象/数组保留为 JSON。CSV 使用 UTF-8 BOM，处理逗号、换行与公式注入。

**与后台 CSV（所有域）的区别：** 这是全部 API 字段 CSV，不保证与后台导出的列、人员显示格式、评论和变更历史完全一致。后台格式对齐需拿实际样本验证，尚未完成。

默认上限 1000，最大 10000；query 会明确标记截断，export 遇到截断拒绝下载，避免误当完整数据。汇总仅统计已返回条目。未指定排序时补充 `ORDER BY key ASC`；分页不提供事务快照，并发修改可能影响结果。按用户约定，后续导出统一保存在 `/Users/lingang/Downloads`（脚本默认 `~/Downloads`），按内部业务数据管理，不放入仓库。

## 验证与故障处理

```bash
python3 -m unittest discover -s tests -v
```

测试使用模拟 Jira，不会创建或关闭真实需求。最近结果为 18 项通过，覆盖认证、创建字段与幂等、超时及读回、分页/截断/CSV、关闭状态及解决结果校验、原因备注与转换同请求、转换幂等和 Jira 204 空响应。

- 401：区分本地 `X-API-Key` 与 Jira 账号认证；不要打印密钥、密码或 Authorization。
- 创建字段错误：重新获取项目 metadata，确认报告人、自定义必填字段及权限。
- 409：核对请求内容、幂等键和当前状态；不要更换键绕过未知提交结果。
- 提交超时或 `verified=false`：先按编号/标题查询 Jira 核对；已返回编号时不要重复创建。当前没有人工核对后的幂等恢复接口。
- CSV 422 截断：缩小 JQL 范围或分批导出；每批确认完整性，并留意分页期间的数据变化。
- `/health` 只表示本地服务和配置状态；真实连通性应通过认证后的只读项目/查询接口确认。

服务代码或配置修改后重启终端进程；导出脚本修改无需重启服务。`.local/requests.sqlite3` 是防重状态，应保留，不要通过删除数据库解决失败请求；后续业务导出放在 `/Users/lingang/Downloads`，两者均不提交 Git。旧 `exports/` 仍保持 Git 忽略。

## 周报/月报：按解决日期的精简 CSV

`POST /reports/resolved/export` 默认读取当前账号可见的全部项目，仅请求 7 个 API 字段（问题关键字由 issue key 提供），不读取描述、评论和其他自定义字段。可通过 `projects` 限定项目，空数组表示全部可见项目。

```json
{
  "start_date": "2026-09-01",
  "end_date": "2026-10-01",
  "timezone": "Asia/Phnom_Penh",
  "projects": [],
  "limit": 10000
}
```

区间包含起始日、不包含结束日；周报使用同一接口指定一周边界。接口读取 Jira 账号时区，将区间转换为该时区的 JQL 时间，再逐条检查返回时间，避免月底跨时区误选。输出固定顺序如下：

| 报表列 | API 来源 | 输出形式 |
|---|---|---|
| 问题关键字 | issue key | 如 CCSL-2679 |
| 概要 | summary | 文本 |
| 问题类型 | issuetype.name | 类型名称 |
| 经办人 | assignee.name | 用户名；未分配为空 |
| 已解决 | resolutiondate | 指定时区 `YYYY-MM-DD HH:mm:ss` |
| 报告人 | reporter.name | 用户名 |
| 创建时间 | created | 指定时区 `YYYY-MM-DD HH:mm:ss` |
| 项目名称 | project.name | 项目显示名称 |

2026-10-03 已通过原生“CSV（所有域）”单条样本核对：原生创建列名为“创建日期”，本报表按用户要求命名“创建时间”；经办人/报告人为用户名。这里按用户业务约定将“已解决”用于发版时间，但数据源仍是 Jira 解决日期，不额外验证实际部署或版本发布时间，也不排除 Won't Do 等解决结果。

九月实测导出 152 条：CE 8、CE_CCSL 37、新代购商城 105、TOUCHA 2；保存于 Git 忽略的 `exports/Jira-2026-09-已解决问题-月报.csv`。范围是账号当前可见且当前解决日期落入该月的问题，不是历史事件审计；重新打开而清空解决日期的问题不会被选中。分页无事务快照，重复编号、越界日期、缺失/无时区日期或超限会拒绝生成报表。

### 命令行导出

已提供 [export_report.py](export_report.py)，复用上述 API，不复制筛选或格式化逻辑，不直接读取 Jira 数据库。需先启动 `run.py`；脚本只向本机服务提交只读导出请求，读取本地服务密钥，不使用 Jira 密码。

```bash
cd /Users/lingang/sens/wms-db/jira-service
python3 export_report.py --month 2026-09
python3 export_report.py --start 2026-09-21 --end 2026-09-28 --project CCSL
```

- 默认生成 `/Users/lingang/Downloads/jira-resolved-起始日-结束日.csv`（使用当前用户的 `~/Downloads`）；可用 `--output` 指定新文件，已有文件拒绝覆盖。此前九月月报仍保留在原 `exports/` 路径。
- `--project` 可重复；默认全部可见项目。`--timezone` 默认 `Asia/Phnom_Penh`。
- 保存前检查 BOM、8 列名称、每行列数与接口返回条数；失败返回非零退出码。月份支持跨年，区间包含起始日、不含结束日。
- 周报暂沿用月报 8 列作为工具默认；用户尚未单独确认周报字段，不将此默认视为最终周报规范。

### 复用评估（2026-10-03）

**脚本：生成。** 月报/周报是重复任务，命令行入口避免每次临时编写 API 请求；月份、日期、项目、时区和路径均参数化。业务规则仍由 `reporting.py` 与报表接口维护。

**独立 Skill：暂不生成。** 当前工作只需日期/项目参数加固定 CSV 导出，已有服务、脚本和 Runbook 足够；避免另建一份相同规则。若后续确定周报差异、汇总口径、报告模板和校验步骤，形成跨任务的稳定编排流程，再评估 Skill。仓库流程索引仅链接本 Runbook，不安装新 Skill。
