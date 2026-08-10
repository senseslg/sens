# cngg-project Overview

> 菜鸟裹裹（CNGG）与 CE/CCSL 国际直邮及集运业务对接。

- 状态：`in-progress`
- 负责人：待确认（来源未记录本机负责人）
- 建立日期：`2026-08-06`
- 最近更新：`2026-08-06`

## 目标

菜鸟裹裹负责消费者侧下单、国内揽收协同、支付及物流详情展示；CE/CCSL 负责国际段订单承接、仓内操作、国际运输、末端配送，以及重量、尺寸、费用、运单号和物流轨迹回传。项目目标是让双方系统通过标准接口完成直邮和集运两类业务的下单、实操回传、异常处理和轨迹同步。

## 完成标准

- [ ] 三类订单（直邮 `orderType=0`、集运一段包裹 `orderType=1`、集运合包 `orderType=2`）可按确认范围完成创建或幂等更新，双方业务单号关系可查询。
- [ ] 集运一段包裹可预报、入仓、上架、异常处理并参与合法合包；无预报包裹可完成认领闭环。
- [ ] 合包订单正确关联子包裹，非法状态、重复合包和跨客户合包被拦截。
- [ ] 外部接口失败不丢失仓内操作结果，失败任务可自动重试并可人工处理。
- [ ] 所有入站/出站调用、人工操作、费用及状态变化均可审计和对账。
- [ ] 所有 CNGG → CCSL 入站请求先生成 `external_interface_log` 请求记录，业务处理结束后补齐响应、耗时、状态和异常信息。
- [ ] 轨迹 action 映射通过双方确认用例，重复回传不产生重复节点。
- [ ] 联调环境与生产环境配置隔离，代码和文档中不存在明文密钥。

## 范围

### 包含（本期）

- 集运业务：一段包裹预报、无预报拉单认领、上架、异常、合包出库、费用回传。
- 接口：`GG_INTER_CREATE_ORDER`、`GG_INTER_MODIFY_ORDER`、`GG_INTER_OPERATE_ACTION`、`TRACEPUSH`、`GG_INTER_PARCEL_PULL`。
- 菜鸟公共协议（签名、幂等、标准响应）、接口日志和执行结果补偿机制。
- 数据落地：复用 `external_interface_log`、`order_list`、`parcel_list`、`cus_address`、`modify_apply`、`modify_apply_item`、`order_list_log`、`parcel_list_log`。

### 不包含（本期）

- 直邮业务开发（预计 2026-08 底至 09 月初随集运稳定后接入，接口内容已在 [INTERFACE_SPEC.md](INTERFACE_SPEC.md) 中一并记录，便于下一期直接复用）。
- `GG_INTER_ORDER_NOTICE`（支付通知，协议必接但业务范围本期不涉及）。
- `GG_INTER_LINE_RULE_QUERY`（线路规则查询）、`trace_info_query`（轨迹主动查询）、`GG_INTER_UPLOAD_CLEARANCE`（报关文件上传）。
- 集运取消合包（`GG_INTER_MODIFY_ORDER` type=5）是否本期上线以业务确认结果为准，暂不默认包含。

## 系统与数据关系

当前组件图只表达已经确认的系统边界、接口方向和数据库范围，不提前展开尚未确认的全部业务调用链：

- CNGG → CCSL：`GG_INTER_CREATE_ORDER`、`GG_INTER_MODIFY_ORDER`。
- CCSL → CNGG：`GG_INTER_OPERATE_ACTION`、`GG_INTER_PARCEL_PULL`、`TRACEPUSH`。
- CNGG → CCSL 的请求必须先进入 `external_interface_log` 接口审计链路，再进入订单、包裹、地址或修改业务处理。
- 组件图：`/Users/lingang/Downloads/sens-workspace/Plantuml/cngg_interface_data_component.puml`。

| 数据表 | 当前用途 |
|---|---|
| `external_interface_log` | 记录入站接口地址、请求时间、请求头/体、方法、状态、响应、耗时、异常、授权标识和来源 IP |
| `order_list` | 承载直邮订单和集运合包订单的内部订单数据 |
| `parcel_list` | 承载集运一段包裹、国内运单、仓内状态、重量和尺寸等数据 |
| `cus_address` | 承载直邮或集运合包收件地址及客户地址关系 |
| `modify_apply` | 保存订单或包裹修改/取消申请主记录及审批信息 |
| `modify_apply_item` | 保存每个修改字段的原值和现值 |
| `order_list_log` | 保存订单维度的动作、备注和操作审计 |
| `parcel_list_log` | 保存包裹维度的动作、备注、操作人和快递单号审计 |

## 当前状态

需求已梳理完成，处于开发拆分与联调准备阶段。集运优先，直邮随后；开发优先节点为 2026-08-15 至 2026-08-20，线上分国家放量为 2026-08-20 至 2026-08-25。技术白皮书（V1.1，2026-08-05）已明确合包指令不再重传商品信息、无预报拉单改为“同步返回归属 + 异步下发预报”。接口与数据关系图已调整为组件图样式，并明确两个 CNGG 入站接口先进入 `external_interface_log`。详细接口规格见 [INTERFACE_SPEC.md](INTERFACE_SPEC.md)，未决事项见 [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)。

## 重要决定

| 日期 | 决定 | 依据或影响 |
|---|---|---|
| 2026-07-29 | 首期只上线集运业务，直邮随后上线 | 降低联调范围，符合开发时间紧迫（2026-08-15 至 2026-08-20）的约束 |
| 2026-07-29 | 优先对接必填接口，`GG_INTER_ORDER_NOTICE` 等非必须接口可暂缓 | 支付通知涉及 2C 实时支付，本期业务模式不依赖 |
| 2026-08-04 | 集包规则：仅快递小件集包，单件大于 0.2 立方的大货不参与集包，直接按直邮处理；小件入库满 48 小时无其他包裹合并则自动强制合包 | 避免大货占用集运出库时效，简化集包判断 |
| 2026-08-04 | 计费与结算：集包件按快递小件标准向用户收费；结算金额拆分为“运费”和“税金代缴”，服务商仅对运费部分开具增值税普通发票 | 满足上市公司合规要求 |
| 2026-08-05 | 合包指令（`orderType=2`）不再透传商品信息，必须复用对应一段预报（`orderType=1`）保存的商品明细 | 白皮书 V1.1 变更，减少重复传输和口径不一致风险 |
| 2026-08-05 | 无预报拉单（`GG_INTER_PARCEL_PULL`）逻辑调整为：同步仅返回 `belongsToGG`，`true` 时裹裹再异步下发完整预报 | 白皮书 V1.1 变更；接收方需注意避免在预报到达前提前写入数据导致冲突 |
| 2026-08-05 | 直邮场景不再走“下单后更新运单号”，改为下单时直接传最终运单号 | 简化直邮 `GG_INTER_MODIFY_ORDER` type=3 场景，下一期开发时按新方式实现 |
| 2026-08-06 | 所有 CNGG → CCSL 请求统一先进入 `external_interface_log` 审计链路 | 当前入站范围为创建/合包和修改/取消；需要统一覆盖菜鸟 SDK Receiver，并将请求日志与业务处理结果关联 |
| 2026-08-06 | 接口与数据关系图采用组件图，不再采用类图 | 当前图表达系统边界、接口方向与数据依赖，不表达面向对象的属性和方法 |

## 行动项

| 状态 | 行动 | 负责人 | 时间 |
|---|---|---|---|
| 待办 | 完成菜鸟公共协议（签名、幂等、标准响应、接口日志）后端基础能力 | 待确认 | 2026-08-15 前 |
| 待办 | 让菜鸟 SDK 入站 Receiver 统一接入 `external_interface_log`，请求进入时落日志，处理结束后回写响应、耗时、状态和异常 | 待确认 | 2026-08-15 前 |
| 待办 | 完成 `GG_INTER_CREATE_ORDER` 三种 `orderType` 的创建与幂等更新 | 待确认 | 2026-08-15 至 2026-08-20 |
| 待办 | 完成 `GG_INTER_MODIFY_ORDER` 集运一段包裹取消（type=4） | 待确认 | 2026-08-15 至 2026-08-20 |
| 待办 | 完成 `GG_INTER_OPERATE_ACTION` 出站回传：`CS_PUTAWAY`、`CS_EXCEPTION`、`CS_OUTBOUND`、`CS_RETURN_SERVICE_FEE` | 待确认 | 2026-08-15 至 2026-08-20 |
| 待办 | 完成 `TRACEPUSH` 节点映射配置与幂等重试 | 待确认 | 2026-08-15 至 2026-08-20 |
| 待办 | 完成 `GG_INTER_PARCEL_PULL` 无预报拉单同步归属判断 + 异步认领闭环 | 待确认 | 2026-08-15 至 2026-08-20 |
| 待办 | 获取国际产品编码（`productCode`）与 CE 产品的完整映射列表 | 待确认（商务/CP 提供） | 待确认 |
| 待办 | 确认地址区域语言映射方案（优先菜鸟地址库 ID，缺失时确认中/英/当地语言） | 待确认 | 待确认 |
| 待办 | 获取菜鸟标准物流节点及异常节点对照文件（钉钉文档，菜鸟直接提供） | 待确认 | 待确认 |
| 待办 | 分国家灰度放量前完成集运全链路联调 | 待确认 | 2026-08-20 前 |

## 风险与依赖

- 技术白皮书仍在更新（当前 V1.1，2026-08-05），字段和流程可能继续变化，开发前需再次核对最新版本。
- `productCode` 依赖商务提供的完整产品/报价列表，缺失映射时下单会被拒绝，需提前锁定。
- 无预报拉单的“先同步返回归属、再异步下发预报”时序要求接收方避免在预报到达前提前写入数据，需要设计层面明确防冲突方案。
- 直邮和集运共用部分接口字段但业务规则不同（如 `pickUpMailNo`、`productCode` 是否必传随 `orderType` 变化），实现时需按类型严格校验，避免相互污染。
- `external_interface_log` 当前没有独立的 `msg_id`、`msg_type` 和业务对象字段，不能仅靠原始请求体高效完成接口幂等与业务检索；是否扩表或新增专用幂等关系表需要技术评审。
- 现有通用 AOP 主要覆盖 `ExternalApi`、PDD 和 Shopee 接口，菜鸟 Link SDK Receiver 需要统一拦截器或显式日志封装，不能假定会自动写入 `external_interface_log`。
- `external_interface_log` 含请求体、响应体、错误堆栈和 `auth_code`，可能包含签名、电话和地址等敏感数据；必须明确脱敏、加密、访问权限和保留周期。
- 开发时间紧（2026-08-15 至 2026-08-20 为主要节点），若产品映射、地址语言方案或节点对照文件未按时到位，可能影响联调和放量节奏。

## 相关资料

- [INTERFACE_SPEC.md](INTERFACE_SPEC.md)：接口清单与字段级规格。
- [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)：待确认事项结论、会议纪要摘要。
- 业务时序图：`/Users/lingang/Downloads/sens-workspace/Plantuml/cngg_business_workflow_seq.puml`
- 接口方向与数据关系组件图：`/Users/lingang/Downloads/sens-workspace/Plantuml/cngg_interface_data_component.puml`
- 数据库字段记录目录：`/Users/lingang/Downloads/菜鸟裹裹接口`
- 来源：Anytype `sens` 空间 Task「菜鸟裹裹项目开发需求」、Page「菜鸟裹裹接口文档」（读取时间 2026-08-06）。
