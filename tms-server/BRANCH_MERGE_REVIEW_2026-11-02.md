# TMS master / qa 合并排查（2026-11-02）

## 当前结论

未发现近期以 master 为来源、qa 为目标的独立 PR；最近合并提交的标题均为 `feature/ccsl-tms-otwms → qa`。但功能分支与当前 master 指向同一提交，因此图上同时出现 master 标签，代码内容上该次合并确实包含当前 master。

未发现 qa 被直接重置成 master 或整体替换：最新 qa 是双亲合并提交，保留原 qa 为第一父提交。UAT 已由 yuth 手动构建部署；生产 Jenkins 最近构建仍为 10 月 15 日，未见本批代码通过该任务上线。主要风险是业务回归与下一次生产发布，不应仅凭合并方向直接回退分支。

## 分支证据（只读快照）

仓库 `TMS/tms-server`，Bitbucket 服务端裸仓库 ID `1`。本次没有克隆、切换、合并、重置、推送或修改仓库。

| 分支/基线 | 提交 |
|---|---|
| master | `d4883e04db4b25e5001b2606a168c1cfd9eda9a0` |
| feature/ccsl-tms-otwms | 同上 |
| qa | `6dc34972e8418e4fed3cd4807c30ae4950b58cbc` |
| qa 合并前第一父提交 | `8d8f83844c26218f2cae4f3db438b32afb3ac56b` |
| qa 合并的第二父提交 | `d4883e04db4b25e5001b2606a168c1cfd9eda9a0` |
| 最近生产构建源码 | `4efc64243aa6dd3a6b08865c985bf9d34720d780` |

- 最新 qa 合并时间 2026-11-02 12:27:24 +0700，Git 作者名 SiGentIsHere；上一条 master 提交为 12:27:07 +0700。Git 作者名不能替代认证推送人证据。
- `master` 是 `qa` 的祖先；`master...qa` 的独有提交计数为 `0 / 421`。421 是多年累计的 qa 独有历史（含合并提交），不是这一次新引入 421 个功能。
- 最新一次 qa 合并相对第一父提交：5 文件，+146/-8 行，包含测试文件和测试依赖；不是全仓库覆盖。
- qa 与 master 的当前树差异：40 文件，+675/-90 行，仍保留 QA 特有差异。这不等于已验证所有 QA 功能完好。
- 当前 master 比最近生产构建多 40 个提交，树差异 19 文件、+614/-30 行。尚未确认 master 分支引用何时、由谁推进到该位置；仓库未返回可用 master reflog，不凭提交日期认定推送时间。

链接：[分支列表](https://code.cambodianexpress.com/projects/TMS/repos/tms-server/branches)、[最新 qa 合并](https://code.cambodianexpress.com/projects/TMS/repos/tms-server/commits/6dc34972e8418e4fed3cd4807c30ae4950b58cbc)。

## 部署影响

| 项目 | UAT | 生产 |
|---|---|---|
| Jenkins | TMS / uat / tms-uat #868 | TMS / prod / tms-prod #458 |
| 构建开始（金边） | 2026-11-02 12:27:41 | 2026-10-15 07:15:11 |
| 实际检出 | qa `6dc34972…` | master 历史提交 `4efc6424…` |
| 触发类型 | UserIdCause，yuth | UserIdCause，Milo |
| 构建结果 | SUCCESS，日志包含部署脚本及 Tomcat started | SUCCESS，日志包含部署脚本及 Tomcat started |
| Maven | `clean package -f TmsParent -DskipTests=true -P uat` | `clean package -f TmsParent -P gcp` |
| 产物路径 | `gs://cambodian-express/packages/uat/ROOT.war` | `gs://cambodian-express/ROOT.war` |
| 目标实例 | tms-uat | tms-instance-template-20251103-082933 |

- 最新任务配置未见触发器；#868 的记录明确是用户发起，不能说本次是 master 合并自动触发生产部署。
- UAT #865–#868 分别检出对应 qa 合并提交并报告 SUCCESS；不能把反复构建成功当作业务回归完成。
- 两个入口当前均跳转登录页并返回 200；这是入口检查，不代表取件、入库、回传、状态及金额正确。
- 未比对运行中 WAR 与构建产物校验值，也未排除绕过 Jenkins 的人工部署；生产结论限定为已检查发布记录。没有触发任何构建、部署或重启。

## 业务风险判断

| 风险 | 评估 |
|---|---|
| qa 被整条覆盖 | 未发现；合并保留前序 qa，当前仍有 QA 独有树差异，不建议仅据图形回退 |
| UAT 业务变化 | 已发生代码部署，中等关注；需业务联调确认，不能视作仅历史图变化 |
| 重复取件回传 | 最新代码把 `if (!isCcslLocal || isOtwmsNative)` 改成 `if (!isCcslLocal && !isOtwmsNative)`，扩大回传范围；并在 `shipmentPickupConfirm` 重新调用 `handlePickupConfirm(order)`。上一版注释说明 OTWMS 已负责通知并为避免重复移除了该调用，因此存在重复通知风险；未核实 OTWMS 当前行为，尚不能定性实际重复故障 |
| 自动化验证不足 | 最新增加 JUnit/Mockito 和取件测试，但 UAT 构建明确跳过测试；本次未运行 TMS 测试或发送业务请求 |
| 下一次生产发布 | 重点关注：生产任务读取当前 master，将纳入比最近生产构建新增的 40 个提交，而非继续使用已上线旧提交；涉及 CCSL/TMS/OTWMS 流程及配置，应先完成联调和发布范围确认 |

建议先固定本次候选提交并由负责人确认 master 与功能分支同指向是否符合预期；围绕 CE/CC 单、来源 100/110、正常/重复取件确认、入库状态、金额/COD 回传与重复通知做 UAT 回归，再决定生产发布。若确需撤销某项改动，应针对具体提交设计补偿提交或回退方案，不直接强推重置 qa/master。

本次是只读排查，未新增 Skill 或自动修复脚本；分支比对与 Jenkins 核对流程由现有 Runbook 承载。
