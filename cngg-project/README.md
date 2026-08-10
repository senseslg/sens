# cngg-project

菜鸟裹裹（CNGG）与 CE/CCSL 对接国际直邮及集运业务的子项目记录。

## 阅读顺序

1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：目标、范围、当前状态、重要决定和行动项。
2. [INTERFACE_SPEC.md](INTERFACE_SPEC.md)：客户信息、接口方向、公共协议、优先接口字段规格和数据库表落地关系。
3. [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)：待确认事项、技术设计问题和会议纪要摘要。

## 当前结论

- 客户：`customer_code = CNGG`，`customer.id = 259444`，`blade_user.id = 198263`。
- 业务范围：集运（集包）优先接入，直邮下一期（预计 2026-08 底至 09 月初）接入。
- 本期必须对接的 5 个接口：`GG_INTER_CREATE_ORDER`、`GG_INTER_MODIFY_ORDER`、`GG_INTER_OPERATE_ACTION`、`TRACEPUSH`、`GG_INTER_PARCEL_PULL`。
- 接口方向：`GG_INTER_CREATE_ORDER`、`GG_INTER_MODIFY_ORDER` 为 CNGG → CCSL；`GG_INTER_OPERATE_ACTION`、`TRACEPUSH`、`GG_INTER_PARCEL_PULL` 为 CCSL → CNGG。
- 所有 CNGG → CCSL 的入站请求必须先进入 `external_interface_log` 审计链路，再路由到订单、包裹或修改业务处理。
- 当前数据落地范围涉及 8 张现有表：`external_interface_log`、`order_list`、`parcel_list`、`cus_address`、`modify_apply`、`modify_apply_item`、`order_list_log`、`parcel_list_log`。
- `GG_INTER_ORDER_NOTICE`（支付通知）协议要求必接，但业务范围本期不涉及，暂不纳入开发。
- 上线节奏：分国家放量 2026-08-20 至 2026-08-25；开发优先节点 2026-08-15 至 2026-08-20。

## 来源说明

内容整理自本机 Anytype `sens` 空间：

- Task「菜鸟裹裹项目开发需求」
- Page「菜鸟裹裹接口文档」（裹裹国际 CP 接入白皮书 V1.1，2026-08-05）

读取时间：2026-08-06。数据库表结构同时基于 `new_ccsl` 的只读 `information_schema` 核对结果和当前后端实体/日志代码整理。原始接口文档仍在更新中，本子项目仅反映读取时的快照，接口字段和业务规则以 Anytype 最新版本为准。

## 关联图表

- 业务时序图：`/Users/lingang/Downloads/sens-workspace/Plantuml/cngg_business_workflow_seq.puml`
- 接口方向与数据关系组件图：`/Users/lingang/Downloads/sens-workspace/Plantuml/cngg_interface_data_component.puml`
- 数据库字段记录目录：`/Users/lingang/Downloads/菜鸟裹裹接口`
