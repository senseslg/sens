# AGENTS.md — ali_oss

所有 AI agent 在本项目每次会话都必须遵守。每条 1–3 行并链接归宿。`CLAUDE.md` 只引用本文件。

> 基于 [sens_ai_agent_constraints](/Users/lingang/sens_ai_agent_constraints/NEW_PROJECT.md) · agent-framework: v0.3.1
> 优先级：本文件 > 框架规则 > agent 默认习惯。本文件未覆盖的情况按框架 [AGENTS.md](/Users/lingang/sens_ai_agent_constraints/AGENTS.md) 与 [constraints](/Users/lingang/sens_ai_agent_constraints/docs/constraints.md) 执行。

## 通用规则

- 开始前按 [PROJECT_READ_FIRST.md](PROJECT_READ_FIRST.md) 读取上下文；已记录的信息不要求用户重复。
- 先确认目标、范围、完成标准、授权边界；可安全推进时写明假设继续，会改变方向时再问。
- 任务匹配 [SKILL.md](SKILL.md) 中的流程时先加载；playbook 不替代读取当前代码和真实状态。
- **只读优先**：生产、数据库、服务器默认只读诊断；依赖字段名或线上值前先查结构。
- **高影响操作需明确授权**：外部发送、生产写入、部署/重启、删除/覆盖/批量修改、权限/DNS/防火墙变更、git push。
- **写操作四件套**：变更前状态、目标核对与影响行数、回滚方案、变更后验证。
- 事实 / 推断 / 建议 / 决定分开表达。
- 环境失败（沙箱、网络、DNS）不盲重试，改用最窄的权限升级或替代通道。
- 验证与改动面匹配；只汇报实际运行过的命令和结果。
- 会话开始时检查 [todos/TODO.md](todos/TODO.md)，提醒过期、将到期、停滞的待办；完成时新增或关闭待办。
- 完成时更新记录、迭代日志加一行、做复用评估并写进交付说明。
- 文档简短可扫描，先结论；一个事实一个归宿；描述当前状态。
- 禁止提交或输出凭证；用环境变量名或配置路径引用。

## 框架流程（按需加载）

| 场景 | Skill |
|---|---|
| 数据库诊断或写 SQL | [db-ops-debug](/Users/lingang/sens_ai_agent_constraints/skills/db-ops-debug/SKILL.md) |
| 部署、重启、配置、清理等生产变更 | [prod-change-control](/Users/lingang/sens_ai_agent_constraints/skills/prod-change-control/SKILL.md) |
| 线上故障 | [incident-response](/Users/lingang/sens_ai_agent_constraints/skills/incident-response/SKILL.md) |
| 提交 / 推送前 | [pre-push-checks](/Users/lingang/sens_ai_agent_constraints/skills/pre-push-checks/SKILL.md) |
| 待办记录与跟进 | [todo-tracking](/Users/lingang/sens_ai_agent_constraints/skills/todo-tracking/SKILL.md) |
| 任务收尾 | [task-closeout](/Users/lingang/sens_ai_agent_constraints/skills/task-closeout/SKILL.md) |
| 沉淀 skill / 脚本 | [skill-authoring](/Users/lingang/sens_ai_agent_constraints/skills/skill-authoring/SKILL.md) |

框架脚本：`python3 /Users/lingang/sens_ai_agent_constraints/scripts/check_docs.py --root .` · `python3 /Users/lingang/sens_ai_agent_constraints/scripts/todo_report.py --root .`

跨项目通用的经验回流到框架（见 [经验回流](/Users/lingang/sens_ai_agent_constraints/NEW_PROJECT.md)），项目特有的留在本项目。

## 项目约定

- 继承根仓库 [PROJECT_READ_FIRST.md](../PROJECT_READ_FIRST.md) 的简洁记录与安全规则；本子项目只记 OSS 管理相关事实。
- **控制台只读**：经 Chrome 查看阿里云控制台只读收集信息；登录、MFA、验证码由用户本人完成，agent 不输入密码。
- **写操作需逐项授权**：创建/删除 Bucket、改 ACL/Policy/CORS/生命周期/防盗链/版本控制、删除或覆盖对象、改 RAM/AccessKey，均按“写操作四件套”执行。
- 受保护桶 `cambodianexpress-ccsl`、`ccsl-mallgogo`、`ceccsl`、`uat-mallgogo` 写操作须 `--confirm-bucket`；生产与 UAT 不混用；static CDN 证书链路主记录在 [otwms-ce-lb/STATIC_OSS_SSL.md](../otwms-ce-lb/STATIC_OSS_SSL.md)，此处只链接。
- OSS 凭据仅存 `.local/credentials.json`（0600，gitignore），不得提交或输出；证书/CDN 用户 `power-application-user` 不用于 OSS（索引见 `/Users/lingang/internationl_ali_cloud/CREDENTIALS.md`）。
- 不记录账单金额以外的支付信息；对象清单只记前缀与用途，不复制业务文件内容。

## 常用命令

`python3 scripts/oss.py <cmd>`（见 [RUNBOOK.md](RUNBOOK.md)）· `python3 -m unittest discover -s tests`
