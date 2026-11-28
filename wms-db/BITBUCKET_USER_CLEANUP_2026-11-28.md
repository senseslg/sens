# Jira / Bitbucket 账号清理（2026-11-28）

## 当前状态

- **登录白名单**（用户决定）：sens、BRIAN、ceck、daniel.zhou、huzw、longmh、milf、yuth，另保留 Bitbucket 本地账号 `jenkins`（32 个 Jenkins 任务用凭据 `Bitbucket` 经 HTTPS 拉代码，停用即全部构建失败）。Jira 与 Bitbucket 启用账号已回查与此一致。
- **Jira 运行模式：私有**（原为「开放」，任何人可自助注册并自动同步进 Bitbucket）。匿名访问注册页已显示私有站点提示。回滚：系统 → 一般设置 → 编辑设置 → 运行模式。
- **已停用（可恢复，不是删除）**：GUD7XY、rschauditqrnht2is、rt20261027080120a3ce6f83、Thyna、cyj、darvis.clawd、mark、milo、tsw、scott。另 `cdp25417`（CE Probe，11-27 匿名注册）已由 sens 在 Jira 删除。
- **交接**：scott 负责的 CE 组件（CE.CCSL、CE客户端APP、OTWMS前端、TMS）负责人改为 `huzw`，其中 CE.CCSL、TMS 新问题默认分给 huzw；停用账号名下全部 91 个未解决问题改派 `sens`，回查剩余 0。其中原 scott 的 83 个按用户决定关闭：CE 21、CCSL 60 为「已关闭 / Won't Do」；TOUCHA-28、TOUCHA-30 因简化工作流不能选解决结果，转「完成」（结果=完成）并备注 Won't Do。
- sens 名下 2026-10-01 前创建的 32 个未解决问题按用户决定关闭：29 个「已关闭 / Won't Do」；TOUCHA-23、CFA-51、CFA-52（简化工作流）转「完成」并备注 Won't Do。sens 剩余未解决 7 个（均为 10 月后创建）。
- 全部未分配的 22 个未解决问题按用户决定关闭：CELSHOP 7、CE 1 为「已关闭 / Won't Do」（含 10-20 创建的 CELSHOP-1013）；TOUCHA 14 个转「完成」并备注 Won't Do。未分配未解决回查为 0。
- 2026-01-01 前创建的 56 个未解决问题（CE、CCSL）按用户决定关闭为「已关闭 / Won't Do」：成功 55；CE-2140（经办 milf，状态开放）对 sens 没有任何可用工作流操作，未关闭。全站未解决剩 52。
- 停用账号不能自行恢复；只有 Jira 系统管理员可重新启用，审计日志可查。

## 权限结构

- Bitbucket 4.0.2 用户来自两个目录：`JIRA Server`（Crowd，读 Jira，每小时增量同步，只读）和 Bitbucket 本地目录（仅 `jenkins`、`yuth`）。
- 最高权限：Jira 系统管理员 = 组 `jira-administrators`（启用：sens、daniel.zhou、milf）；Bitbucket SYS_ADMIN = sens、huzw、组 `jira-administrators`。
- Bitbucket 无匿名访问（公开项目/仓库均为 0）；FLUT、INFRA、OTWMS、TMS 给「所有登录用户」开了默认权限；`jira-software-users` 有建项目权限。
- Jenkins 授权为「登录即可做任何事」，37 个本地账号都是管理员（见 [jenkins-service](../jenkins-service/README.md)），本次未处理。

## 遗留风险

- Jenkins 37 个账号全为管理员，未按白名单清理。
- 停用前已打开的浏览器会话可能要到过期才失效；停用账号 SSH 密钥被拒绝属 Atlassian 一般行为，未实测。
- `ceck`（cydoo@qq.com）11-26 创建、名字不像真人，但在用户白名单内，按决定保留。

操作方法与坑见 [RUNBOOK：账号停用](RUNBOOK.md#jira--bitbucket-账号停用)。
