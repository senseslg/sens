# CCSL 提交作者 SiGentIsHere 核对（2026-11-02）

## 结论

用户在 CCSL 后端分支/提交图中看到的 `SiGentIsHere` 是 Git 提交作者名，当前 Bitbucket 用户管理页没有匹配用户。现有证据表明这些提交与 YUTH 的开发活动高度相关，但不能仅凭可自行填写的 Git 作者信息断言自然人身份，不能据此判断出现陌生登录账号或入侵。

## 已核实证据

- 仓库：`CCSL/ccsl-backend`，服务器只读定位到仓库 ID `181`。
- 提交 `96cc5041a3e4ba926bb692bce9dd04d599bb4308`：作者与提交者均为 `SiGentIsHere <darayuthchea1603@gmail.com>`；时间为 2026-11-02 17:27:19 +0700；主题 `save deliveryer and warehouse into database`。
- 提交 `d533617fb10570fc0c1cf423e38351cceb9284ed`：同一作者/提交者与邮箱；时间为 2026-11-02 17:59:02 +0700；主题 `Merge branch 'feature/dws-phnInbound'`。
- [PR #3727](https://code.cambodianexpress.com/projects/CCSL/repos/ccsl-backend/pull-requests/3727/overview) 包含前一提交，由已登录用户 `YUTH (yuth)` 创建并合并，从 `bugfix/CCSL-2794` 到 `qa`；合并提交 `c25e68107f8b605a4b715e063cd0021eda5096c9`。
- 提交图中 `SiGentIsHere` 不带用户主页链接，而 YUTH 的操作关联 `/users/yuth`。Git 作者/提交者字段与认证推送账号是不同概念，前者不需要管理员创建同名用户。
- 当前保留的审计/应用日志未匹配此名字；推送审计未匹配以上两条完整提交哈希。实际推送认证账号本次尚未直接确认；PR 创建/合并账号已经确认。

## 后续处理

可请 YUTH 确认本机 Git `user.name`、`user.email` 是否为上述身份；如团队需要统一显示，由本人调整后续提交的 Git 身份。未修改用户、权限、Git 配置或历史提交，也不将该昵称登记为新的 Jira 经办人。
