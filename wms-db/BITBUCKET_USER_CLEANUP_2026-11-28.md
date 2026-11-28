# Bitbucket 用户清理（2026-11-28）

## 结论

- 已移除 `cdp25417`（显示名 CE Probe，`cdp25417@gmail.com`）：Jira 审计显示 2026-11-28 11:47（UTC+7）由 `sens` 删除；Bitbucket 11:54 的增量同步未带走删除，12:0x 在 Bitbucket「User Directories → JIRA Server → Synchronise」手动同步后，用户页显示不存在。
- 该账号 2026-11-27 20:47 在 Jira 创建，审计**无操作人**，且 Jira 运行模式为「开放」（Public）：任何人可自助注册，自动进 `jira-software-users`，再同步到 Bitbucket 并带 PROJECT_CREATE 权限。

## 用户与权限结构

- Bitbucket 4.0.2 用户目录：`JIRA Server`（Crowd，读 `issue.cambodianexpress.com`，每小时增量同步，只读）42 人；`Bitbucket Internal Directory` 2 人（`jenkins`、`yuth`）。
- Jira 来的用户只能在 Jira 停用/删除；Bitbucket 内只能改组和权限。删除后若 Bitbucket 未消失，手动 Synchronise。
- Bitbucket SYS_ADMIN：`sens`、`huzw`、组 `jira-administrators`。

## 最高权限持有人（2026-11-28）

- Jira 系统管理员 = 组 `jira-administrators`：启用 `sens`、`daniel.zhou`、`milf`；停用 angel.yu、david.va、heidi.lei、max.huang、tanjia。
- Bitbucket SYS_ADMIN：`sens`、`huzw`、组 `jira-administrators`（同上）。
- Bitbucket 无匿名访问：公开项目 0、公开仓库 0，匿名 API 可见仓库 0。FLUT、INFRA、OTWMS、TMS 四个项目给「所有登录用户」开了默认权限。

## 登录白名单（2026-11-28 用户决定）

允许：sens、BRIAN、ceck、daniel.zhou、huzw、longmh、milf、yuth（按用户给的 8 个邮箱核对）。
- Jira 已停用（可恢复）：GUD7XY、rschauditqrnht2is、rt20261027080120a3ce6f83、Thyna、cyj、darvis.clawd、mark、milo、tsw；scott 处理后也已停用。Bitbucket 手动同步后启用账号只剩白名单 + jenkins。
- `scott`：CE 项目 4 个组件（CE.CCSL、CE客户端APP、OTWMS前端、TMS）负责人已按用户决定改为 `huzw`（CE.CCSL、TMS 默认经办人为组件负责人，新问题会自动分给 huzw）；名下 83 个未解决问题（TOUCHA、CE、CCSL）已按用户决定全部改派给 `sens`，回查剩余 0；随后已停用。
- `jenkins`（Bitbucket 本地账号）按用户决定保留：32 个 Jenkins 任务全部用它（凭据 `Bitbucket`）经 HTTPS 拉代码。
- 停用账号遗留的 8 个未解决问题（darvis.clawd 4、milo 3、tsw 1）已改派 `sens`；10 个停用账号名下未解决问题回查为 0。mark/milo/tsw 停用前近 30 天有活动。
- 停用账号无法自行恢复：Jira 拒绝登录，Bitbucket 同步后同样拒绝；只有 Jira 管理员（sens、daniel.zhou、milf）可重新启用，审计日志可查。

## 风险与待办

- [x] 2026-11-28 按用户授权将 Jira 运行模式改为「私有」；匿名访问注册页显示「不能注册该Jira站点，因为这是一个私有站点」。回滚：系统 → 一般设置 → 编辑设置 → 运行模式。
- [ ] 核实其它近期非真人名账号：`ceck`（11-26）、`rt20261027080120a3ce6f83`（10-27）、`rschauditqrnht2is`（09-22）、`GUD7XY`（08-28），可用 Jira 审计 `/rest/api/2/auditing/record?filter=<用户名>` 看创建人。
- [ ] 检查 `jira-software-users` 在 Bitbucket 的全局权限是否需要 PROJECT_CREATE。
