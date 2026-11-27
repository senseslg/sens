# 待办

记录、跟进、更新待办事项。看板只放未结束的事项，结束后归档。项目整体状态仍在 `records/projects/`，这里只管行动项。

## 结构

| 位置 | 内容 |
|---|---|
| [TODO.md](TODO.md) | 当前看板：所有未结束待办，一行一项 |
| `items/T-xxx-<slug>.md` | 可选：多步推进、需保留进展或背景较多的待办详情 |
| `done/YYYY-MM.md` | 按结束月份归档的 `completed` / `cancelled` 事项 |

## 字段

| 字段 | 规则 |
|---|---|
| ID | `T-001` 递增，永不复用；`python3 /Users/lingang/sens_ai_agent_constraints/scripts/todo_report.py --root .` 给出下一个可用 ID |
| 优先级 | `P0` 今天必须处理 · `P1` 本周 · `P2` 有空再做 |
| 事项 | 动词开头，一句话能判断是否完成 |
| 状态 | `proposed` 待确认 · `active` 推进中 · `waiting` 等人/等时间 · `blocked` 无法继续 |
| 负责人 | 用户、agent 或具体人名；不确定写 `待定` |
| 期限 | `YYYY-MM-DD`；没有明确期限写 `—`，不虚构 |
| 下一步 | active：下一个具体动作 · waiting：在等谁/什么 · blocked：解除条件 |
| 更新 | 最后一次修改该行的日期 |
| 详情 | `items/` 文件或相关记录链接；没有写 `—` |

## 操作

1. **新增**：用户提到“待办 / 之后 / 记得 / 跟进”，或任务结束仍有未完成事项 → 加一行。用户确认的写 `active`/`waiting`，agent 的建议写 `proposed`。
2. **更新**：状态或下一步变化时改该行并刷新“更新”日期。需要保留过程时，在 `items/` 文件的 `## 进展` 下追加一行（日期 + 一句话，最新在上）。
3. **结束**：完成标准满足 → 从看板删除，追加到 `done/<当月>.md`，写结果和验证；取消同样归档并写原因。
4. **跟进**：会话开始时运行 `python3 /Users/lingang/sens_ai_agent_constraints/scripts/todo_report.py --root .`，把过期、3 天内到期、14 天未更新、`blocked` 缺解除条件的事项在回复开头简短提醒。

## 规则

- 看板保持短；超过约 30 项先清理 `proposed` 和过期项。
- 一个待办只在看板出现一次；详情写进 `items/`，看板只留一句话和链接。
- 不写凭证、不复制聊天全文。
