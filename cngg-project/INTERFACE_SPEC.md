# cngg-project 接口规格

技术依据摘要，用于开发前查阅。字段名和规则以 Anytype「菜鸟裹裹接口文档」（裹裹国际 CP 接入白皮书 V1.1，2026-08-05）为准；具体 CCSL 表名和字段需在开发前结合现有代码及数据库再次核实，本文档不替代数据库设计评审。

## 客户信息

| 项 | 值 |
|---|---|
| `customer_code` | `CNGG` |
| `customer.id` | `259444` |
| `blade_user.id` | `198263` |
| 客户组 | 暂无 |
| 联调面单号（`waybillNoCpCode`） | `LE37728530` |

## 物流业务信息

| 项 | 值 |
|---|---|
| 物流类型 | 直邮、集运（集包）；直邮下一期对接 |
| 物流包裹类型 | 集运小包、快运大货 |
| 集包逻辑 | 仅集运小包支持集包；最大集包天数 9999 天（无限，超时无强制拒绝规则，另见集包规则） |
| 集包规则（2026-08-04 会议确认） | 单件大于 0.2 立方的大货不集包，按直邮处理；小件入库满 48 小时无其他包裹合并则自动强制合包出库 |
| 物流产品 | 陆运、空运、海运 |
| 结算方式 | 记账 |
| 数据库参考表 | `external_interface_log`、`order_list`、`parcel_list`、`cus_address`、`modify_apply`、`modify_apply_item`、`order_list_log`、`parcel_list_log` |

## 接口方向与组件图

本期 5 个接口按真实调用方向分为两组：

| 方向 | 接口 | 入口要求 |
|---|---|---|
| CNGG → CCSL | `GG_INTER_CREATE_ORDER`、`GG_INTER_MODIFY_ORDER` | 必须先进入 `external_interface_log` 审计链路，再进行验签、幂等和业务处理 |
| CCSL → CNGG | `GG_INTER_OPERATE_ACTION`、`GG_INTER_PARCEL_PULL`、`TRACEPUSH` | 由内部业务事件生成出站请求；失败与重试状态独立于仓内业务结果保存 |

组件图：`/Users/lingang/Downloads/sens-workspace/Plantuml/cngg_interface_data_component.puml`。

## 公共协议

### CNGG 入站日志前置要求

`new_ccsl.external_interface_log` 为现有实际表。所有 CNGG → CCSL 请求在进入订单、包裹或修改处理前，必须先建立接口日志上下文；请求记录成功后再执行业务路由，处理完成后更新响应、耗时、状态和异常。日志写入失败时的接口处理策略需在开发评审中明确，不能静默丢失审计记录。

当前实际字段按数据库顺序如下：

| 字段 | 类型/索引 | 用途 |
|---|---|---|
| `id` | `bigint(20)`，主键，自增 | 日志主键 |
| `api_url` | `varchar(255)`，非空 | 接口地址或菜鸟服务路径 |
| `request_time` | `datetime`，非空，索引 `INTERFACE_LOG_N2` | 请求进入时间 |
| `request_header_parameter` | `varchar(2000)` | 请求 Header/查询参数摘要；敏感值需脱敏 |
| `request_body_parameter` | `longtext` | 原始或标准化请求体；电话、地址等敏感字段需脱敏或加密 |
| `request_method` | `varchar(10)` | 请求方式 |
| `request_status` | `varchar(10)`，索引 `INTERFACE_LOG_N3` | 请求处理状态；需统一成功、失败、处理中和结果未知的取值 |
| `response_content` | `longtext` | 返回报文或错误响应 |
| `response_time` | `bigint(20)` | 响应耗时，建议统一为毫秒，不得混用时间戳 |
| `stacktrace` | `longtext` | 系统异常堆栈，仅限授权排障人员访问 |
| `auth_code` | `varchar(200)`，索引 `INTERFACE_LOG_N1` | 授权/调用方标识；不得保存可直接复用的明文密钥 |
| `ip` | `varchar(40)` | 请求来源 IP |
| `create_user`、`create_dept`、`create_time` | 基础审计字段 | 创建审计 |
| `update_user`、`update_time` | 基础审计字段 | 更新审计 |
| `status`、`is_deleted` | `int(11)` | 通用状态和逻辑删除 |

现有后端的通用 `ExternalAspectConfig` 主要拦截 `ExternalApi`、PDD 和 Shopee API；既有菜鸟 Link SDK Receiver 存在显式写 `external_interface_log` 的代码。因此本项目不能假定新菜鸟 Receiver 会自动进入通用 AOP，需要统一 Receiver 拦截器/模板，或在每个 Receiver 中调用同一日志服务。

### 请求信封（GG → CP）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `from_code` | String(64) | 是 | 调用方编码（控制台 APPKEY 绑定资源编码） |
| `partner_code` | String(64) | 是 | 合作伙伴编码（CP 调用菜鸟内部系统的资源编码） |
| `msg_id` | String(64) | 是 | 请求唯一号 UUID，用于接口幂等 |
| `msg_type` | String(64) | 是 | 消息类型，即接口服务编码 |
| `data_digest` | String(1024) | 是 | 请求签名 |
| `logistics_interface` | String(2048) | 是 | 请求报文内容（XML/JSON） |

### 请求信封（CP → GG）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `to_code` | String(64) | 否 | 目的地编码 |
| `msg_type` | String(64) | 是 | 消息类型，即接口服务编码 |
| `data_digest` | String(1024) | 是 | 请求签名 |
| `logistics_interface` | String(2048) | 是 | 请求报文内容（XML/JSON） |
| `logistic_provider_id` | String(64) | 是 | 来源 CP 编码（控制台 APPKEY 绑定资源编码） |

### 通用返回结构

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `success` | Boolean | 是 | 成功标识 |
| `errorCode` | String(64) | 否 | 错误码 |
| `errorMsg` | String(64) | 否 | 错误信息 |
| `retryFlag` | Boolean | 否 | 是否可重试 |
| `result` | Object | 否 | 请求结果 |

## 接口清单（全量）

| ID | 接口 | 方向 | 是否必接 | 本项目用途 |
|---|---|---|---|---|
| 1 | `GG_INTER_CREATE_ORDER` | 菜鸟裹裹 → CE | 必接 | 直邮订单、集运一段包裹、集运合包订单预报 |
| 2 | `GG_INTER_MODIFY_ORDER` | 菜鸟裹裹 → CE | 必接 | 地址修改、取消、集运一段包裹取消 |
| 3 | `GG_INTER_OPERATE_ACTION` | CE → 菜鸟裹裹 | 必接 | 仓内实操、重量尺寸、费用、末端运单、异常和地址修改结果回传 |
| 4 | `GG_INTER_ORDER_NOTICE` | 菜鸟裹裹 → CE | 协议必接 | 支付通知，本期业务范围不涉及，暂不开发 |
| 5 | `TRACEPUSH` | CE → 菜鸟物流详情 | 必接 | 正常、异常、逆向及最终物流节点回传 |
| 6 | `GG_INTER_LINE_RULE_QUERY` | 菜鸟裹裹 → CE | 可选 | 本期不涉及 |
| 7 | `GG_INTER_PARCEL_PULL` | CE → 菜鸟裹裹 | 接口表可选，集运必接 | 无预报包裹同步判归属，异步下发完整预报 |
| 8 | `trace_info_query` | 菜鸟裹裹 → CE | 可选 | 本期不涉及 |
| 9 | `GG_INTER_UPLOAD_CLEARANCE` | 菜鸟裹裹 → CE | 可选 | 本期不涉及 |

本期优先开发顺序：`GG_INTER_CREATE_ORDER` → `GG_INTER_MODIFY_ORDER` → `GG_INTER_OPERATE_ACTION` → `TRACEPUSH` → `GG_INTER_PARCEL_PULL`。

## 接口与现有数据库表关系

下表只记录当前已经确认的职责，不提前替代后续数据库设计和字段映射评审。

| 表 | 主要来源接口/场景 | 当前数据职责 |
|---|---|---|
| `external_interface_log` | 所有 CNGG → CCSL 入站请求；本期为创建/合包、修改/取消 | 保存请求、响应、耗时、状态、异常和调用方审计，是入站业务处理前置链路 |
| `order_list` | `GG_INTER_CREATE_ORDER(orderType=0/2)`、合包出库结果 | CE 直邮订单或集运合包订单、内部状态和费用汇总 |
| `parcel_list` | `GG_INTER_CREATE_ORDER(orderType=1)`、`GG_INTER_PARCEL_PULL` 认领、`CS_PUTAWAY`、`CS_EXCEPTION` | 一段包裹、国内运单、仓内状态、重量、尺寸和货物属性 |
| `cus_address` | 直邮创建、集运合包、后续地址修改 | 保存收件地址及与客户/包裹的关系 |
| `modify_apply` | `GG_INTER_MODIFY_ORDER` | 修改或取消申请主记录，包含订单/包裹、原始状态、修改类型、审批和备注 |
| `modify_apply_item` | `GG_INTER_MODIFY_ORDER` | 每个修改字段的原值与现值，通过 `apply_id` 关联申请主记录 |
| `order_list_log` | 订单创建、合包、修改/取消及状态变化 | 订单维度操作审计 |
| `parcel_list_log` | 一段预报、认领、上架、异常、取消及状态变化 | 包裹维度操作审计，包含 `parcel_id` 与 `express_no` |

字段记录文件位于 `/Users/lingang/Downloads/菜鸟裹裹接口`。其中 7 张业务表已有独立 CSV 字段记录；`external_interface_log` 的实际字段在本文“CNGG 入站日志前置要求”中记录。

---

## 1. GG_INTER_CREATE_ORDER（创建订单/合包）

方向：菜鸟裹裹 → CE。同一 `orderId` + 同类型订单重复下发按覆盖更新处理，不同类型为新增。

### 请求核心字段

| 名称 | 类型 | 必填 | 描述 |
|---|---|---|---|
| `orderId` | String | 是 | 客户订单号，幂等字段；集运一段包裹预报时与 `parcelId` 一致 |
| `orderType` | Integer | 否 | 0-直邮（默认）；1-集运一段包裹预报；2-集运合包下单 |
| `pickUpMailNo` | String | 否 | 揽收段面单号，`orderType=0` 或 `1` 必传，合包不传 |
| `lpCode` | String | 否 | 裹裹 LP 单号，`orderType=0` 或 `2` 必传 |
| `parcelId` | String | 否 | 集运包裹 ID，`orderType=1` 必填 |
| `subParcelIdList` | List | 否 | 合包子包裹 ID 列表（元素为 `parcelId`），`orderType=2` 必填 |
| `productCode` | String | 否 | 国际产品编码，`orderType=0` 或 `2` 必传，一段预报不传；枚举：`CPCODE_P_H` 普货海运、`CPCODE_P_K` 普货空运、`CPCODE_T_H` 特货海运、`CPCODE_T_K` 特货空运，及对应大件后缀 `_D` |
| `parcelQuantity` / `declaredValue` / `declaredCurrency` / `pickupType` | — | 是 | 包裹数量、申报总价值（分）、申报币种、寄件方式（1 个人/2 公司） |
| `senderInfo` / `receiverInfo` | DTO | 是 | 寄件人/收件人信息，含姓名、国家、一至四级区划、详细地址、邮编、电话、邮箱；`receiverInfo.regionSecondCode` 为二级区划三字码 |
| `parcelInfoList` | List | 否 | 包裹商品信息，`orderType=0` 或 `1` 必传，`orderType=2` 不传，需从对应一段预报读取 |
| `parcelInfoList[].name/nameCN/desc/quantity/unit/declarationValue/declarationValueCurrencyType/originCountry/hsCode/includeBattery/goodsWeight/material/purpose` | — | — | 商品申报明细，`name` 要求叶子类目英文名，避免整段商品标题 |
| `addServiceInfoList` | List | 否 | 增值服务：`insuranceFee` 保费、`insuredValue` 保价货值 |
| `declarationDocumentList` | List | 否 | 申报材料（身份证 001、商务发票 501、购买证明 503），`documentUrl` 为 OSS 链接，有效期 3 天 |
| `accountInfo` | DTO | 否 | `accountId`、`subAccountId` |

### 返回字段

| 名称 | 类型 | 必填 | 描述 |
|---|---|---|---|
| `orderId` | String | 是 | 裹裹订单号回显 |
| `waybillNo` | String | 是 | CE 运单号，`orderType=0` 或 `2` 必传，一段预报可不传 |
| `waybillNoCpCode` | String | 是 | 运单号 CP Code（如 `LE37728530`），`orderType=0` 或 `2` 必传 |
| `parcelId` | String | 否 | `orderType=1` 时返回集运包裹 ID 回显 |

### 开发要点

- 按 `orderType` 路由至直邮、一段包裹、合包三种处理器；同订单同类型幂等更新，不同类型新增业务对象。
- `orderType=0/2` 校验 `lpCode`；`orderType=1` 校验 `parcelId`；`orderType=2` 校验非空 `subParcelIdList`。
- 合包场景不再透传商品信息（V1.1 变更），必须复用各一段预报保存的商品明细，并校验子包裹同属一客户、已上架、未被其他有效合包占用、无阻断异常。
- `productCode` 必须经线路映射配置转换为 CE 产品，未配置时拒绝创建并返回不可重试错误。
- 申报附件 URL 有效期 3 天，需要长期留存时异步下载至 CE 可控存储，保留原 URL、摘要和下载结果。

---

## 2. GG_INTER_MODIFY_ORDER（订单更新：修改/取消）

方向：菜鸟裹裹 → CE。

### 请求核心字段

| 名称 | 类型 | 必填 | 描述 |
|---|---|---|---|
| `orderId` | String | 是 | 裹裹订单号 |
| `type` | int | 是 | 直邮：1-修改订单（需开发联调）、2-取消订单、3-更新运单号（已确认改为下单直传最终运单号，可忽略）；集运：4-一段包裹取消（仓库需拒收）、5-取消合包（本期不上） |
| `feature` | ModifyFeature | 是 | 按场景区分直邮/集运字段，见下 |
| `accountInfo` | DTO | 否 | `accountId`、`subAccountId` |

`ModifyFeature`（集运场景，本期对接）：`cancelReason`、`cancelReasonCode`（取消时必传）、`needReturn`（是否需要退回）、`returnInfo`（`needReturn=true` 时必传，结构同 `ReceiverInfoDTO`）。

`ModifyFeature`（直邮场景，下一期）：`mailNo`（更新运单号）、`cancelReason`/`cancelReasonCode`、`receiverInfo`（修改收件人）。

### 返回

按场景异步通过 `GG_INTER_OPERATE_ACTION` 的 `MODIFY_R_ADDR_RESULT_NOTICE` 返回结果，本接口自身无同步业务结果示例。

### 开发要点

- 本期主要业务为一段包裹取消（type=4），修改收件人信息、取消订单等直邮场景为合包提供或下一期开发。
- 修改/取消前校验包裹当前节点：已出库、已交接承运商或进入不可逆状态时返回稳定业务错误，不执行部分修改。
- 一段包裹取消后需向仓内下发拒收/隔离标识，避免继续正常上架或参与合包。
- 修改/取消申请写入 `modify_apply`，字段级前后值写入 `modify_apply_item`；执行后的订单/包裹动作分别写入 `order_list_log` 和 `parcel_list_log`。
- 来源报文和接口响应保存在 `external_interface_log`，业务日志只保存可检索的业务摘要和关联主键，避免重复存储完整敏感报文。

---

## 3. GG_INTER_OPERATE_ACTION（操作回传，综合）

方向：CE → 菜鸟裹裹。应用场景：包裹进入揽收仓后 CP 侧实操回传节点，以及仓内增值服务费用项回传。暂不考虑拆包裹场景。

### 请求核心字段

| 名称 | 类型 | 必填 | 描述 |
|---|---|---|---|
| `orderId` | String | 是 | 裹裹订单号；一段包裹场景对应一段预报 `orderId`，合包场景对应合包 `orderId` |
| `operateTime` | String | 是 | 实操时间 `yyyy-MM-dd HH:mm:ss` |
| `operateActions` | List | 是 | 实操行为列表，可一次传多个，见下方 action 说明 |
| `feature` | OperationFeatureDTO | 是 | 按 action 类型填充对应字段块 |

### operateActions 取值（本期集运相关）

| action | 说明 |
|---|---|
| `CS_PUTAWAY` | 一段包裹上架，回传实重、体积重、计费重、计费类型、长宽高、货物属性 |
| `CS_EXCEPTION` | 异常通知（合包前拒收/退回、合包后异常、清关异常） |
| `CS_OUTBOUND` | 合包出库，回传重量、费用项、末端运单号，作为合包完成及计费依据 |
| `CS_RETURN_SERVICE_FEE` | 单独回传费用项，用于实操当下尚未产生的费用（超期仓储、派送、改地址等） |
| `WAREHOUSE_CHECK_BILL` / `UPLOAD_MAIL_NO` / `RETURN_SERVICE_FEE` / `RETURN_PACKAGE` / `MODIFY_R_ADDR_RESULT_NOTICE` | 直邮场景，本期不对接 |

`CS_EXCEPTION` 的 `exceptionDetails`（`ExceptionDetail` 结构）：

| 字段 | 说明 |
|---|---|
| `exceptionType` | `REJECT`（合包前拒收）、`RETURN`（合包前退回）、`CONSOLIDATION`（合包后异常）、`CUSTOMS_CLEARANCE`（清关异常） |
| `reasonCode` | `DAMAGED` 破损、`EMPTY_PACKAGE` 空包、`WET` 潮湿、`PROHIBITED` 禁运、`OVER_LIMIT` 超限（`REJECT`/`RETURN` 适用）；`CHANNEL_CHANGE` 更换渠道、`SPLIT_PACKAGE` 拆包、`SHORT_ITEM` 少件（`CONSOLIDATION` 适用）；`MISSING_DOCUMENTS` 材料缺失、`LOST` 丢件、`PENDING_TAX` 待缴税（`CUSTOMS_CLEARANCE` 适用）；`DAMAGED`/`PROHIBITED` 同时适用于 `CUSTOMS_CLEARANCE` |
| `reasonDesc` / `exceptionImgUrls` | 必填，异常原因描述与图片列表 |
| `exceptionParcelIdList` | 合包异常中少件、破损必传，标识具体子包裹 |
| `newProductCode` | 更换渠道场景必传 |
| `newWaybillNoList` | 拆包场景必传 |

`FeeDetail` 结构：`code`（费用编码）、`price`（单位人民币分）。

### 返回

同通用返回结构（`success`/`errorCode`/`errorMsg`/`retryFlag`）。

### 开发要点

- `CS_OUTBOUND` 回传即代表合包完成，作为计费依据；同一业务对象、同一 action、同一业务版本只允许一条有效回传，内容变化需新版本回传，不得覆盖审计记录。
- 相同费用编码不得重复累计；`GS_INBOUND`、`GS_SIGN`、`GS_MMPICKUP`、`G_SIGN` 及文档指定的 `G_FAILD` 兜底失败节点之后禁止新增费用。
- 费用项列表（直邮、集运）见文末附表，注明费用产生方（CP 回传 / 裹裹计算 / 本期线下）。

---

## 4. TRACEPUSH（物流轨迹回传）

方向：CE → 菜鸟物流详情。CP 有轨迹更新时以“单 + 轨迹维度”向菜鸟回传轨迹。

- 请求结构以菜鸟开放平台 `TRACEPUSH` 接口文档为准（`https://open.cainiao.com/api-doc/detail?category=logistics&type=express_new&apiId=TRACEPUSH`）。
- 节点映射流程：CP 提供完整物流轨迹说明文档（《菜鸟标准节点及异常节点》，钉钉文档），裹裹/CP 双方确认 action 映射后再开发回传。
- 异常节点：一级 action 固定为 `G_FAILD`，二级码为事件 code（如 `F0011`），并附事件发生原因；国际异常类节点含逆向物流，二级码定义见菜鸟异常节点文档（国内业务专用异常码不适用）。

### 开发要点

- 轨迹回传单位为“一个订单的一条轨迹”，正常、异常、逆向节点均需及时回传。
- 先维护 CE 节点到菜鸟 action/二级事件码的配置化映射，未配置节点禁止猜测，直接转人工处理。
- 以业务单号、轨迹编码、发生时间和接收方构成业务幂等键，避免重复推送。
- 成功后记录对方响应；超时或 `retryFlag=true` 进入共享执行结果中心重试。
- 履约考核（2026-07-29 会议）：需完整回传入库到签收的 12 个关键节点，完整性目标 98%，实操后 24 小时内回传目标 95%，未达标扣罚 2 元/单。

---

## 5. GG_INTER_PARCEL_PULL（无预报包裹拉单）

方向：CE → 菜鸟裹裹。仅支持集运场景。包裹送达仓库但裹裹从未下发预报时，CP 扫码调用本接口。

### 请求

| 名称 | 类型 | 必填 | 描述 |
|---|---|---|---|
| `mailNo` | String | 是 | 一段运单号 |
| `ownerlessCode` | String | 是 | 无主件码 |

### 返回（V1.1 变更后）

| 名称 | 类型 | 必填 | 描述 |
|---|---|---|---|
| `belongsToGG` | Boolean | 是 | 订单是否属于裹裹平台；为 `true` 时裹裹会异步发起完整预报 |

`mailNo`、`parcelId` 同步返回字段已废弃，不再依赖。

### 开发要点

- 同步响应只读取 `belongsToGG`；`true` 时等待菜鸟异步调用 `GG_INTER_CREATE_ORDER`（`orderType=1`）下发完整预报后完成认领。
- `belongsToGG=false` 时保留为非菜鸟无主件；接口超时或失败进入“归属待确认”，两种状态不得混淆。
- 等待预报超时不阻断仓库完成签收、称重、拍照和隔离上架，但不得进入正常合包；需提供超时提醒、拉单重试和人工认领审计。
- 接收方需注意避免在预报到达前提前写入数据导致冲突（2026-08-05 会议强调）。

---

## 费用项参考（附表摘要）

### 直邮费用项（下一期使用）

| CP 费用项 | 裹裹费用项 code | 计费规则 |
|---|---|---|
| 税费 | `duty_fee` | 裹裹计算，多退少补本期不上 |
| 偏远派送 | `remote_fee` | 裹裹计算 |
| 派送费 | `c2g_last_mile_fee` | 裹裹计算 |
| 加固包装 / 打木架 / 拆木架 / 防水包装 / 拆外包装 / 加泡沫棉 / 纸箱包装 / 吊装 / 其他包装类 / 特殊物品木架加固 / 超标大件费 / 验货拍照 | 对应 `c2g_*` / `carton_fee` / `over_length_overweight_surcharge_fee` | CP 回传 |
| 地址更改 / 上楼 / 超期仓储 / 二次派送 / 退仓销毁 | 对应 `address_change_fee` 等 | 本期线下 |

### 集运费用项（本期使用）

| CP 费用项 | 裹裹费用项 code | 计费规则 |
|---|---|---|
| 税费 | `duty_fee` | 裹裹计算，多退少补本期不上 |
| 国内超时仓储费 | `c2g_domestic_overdue_storage` | 裹裹计算 |
| 偏远派送 | `remote_fee` | 裹裹计算 |
| 超标大件费 | `over_length_overweight_surcharge_fee` | 裹裹计算 |
| 包装费（加固包装） | `c2g_reinforce_pack` | CP 回传，一段包裹上架完成时回传 |
| 派送费 | `c2g_last_mile_fee` | 裹裹计算 |
| 地址更改 / 上楼 / 超期仓储 / 退仓销毁 / 二次派送 | 对应 `address_change_fee` 等 | 本期线下 |

打木架费用标准化（2026-08-04 会议确认）：小件（0.2 方以下）100 元，大件 300 元。

## 状态与幂等规则

1. 所有 CNGG → CCSL 请求先进入 `external_interface_log` 审计链路；接口日志不等于幂等记录，日志写入后仍需先按 `msg_id` 防重复请求，再按 `orderId + orderType` 或轨迹业务键防重复业务处理。
2. 创建、修改、支付、实操和轨迹分别保存处理状态，避免一个接口成功掩盖另一个接口失败。
3. 状态推进单向且需校验前置条件；取消、退回、异常解除等通过明确事件转换，不直接改任意状态。
4. 外部响应超时按“结果未知”处理，先查询本地幂等记录再重试，不立即重复业务写入。
5. 仓内真实操作成功而外部回传失败时，本地业务状态保持成功，回传状态单独标记失败并补偿。
6. 同一费用项、同一轨迹、同一实操 action 的重复回调必须返回已处理结果，不得重复计费或重复生成记录。

## 相关图表

- 业务时序图：`/Users/lingang/Downloads/sens-workspace/Plantuml/cngg_business_workflow_seq.puml`
- 接口方向与数据关系组件图：`/Users/lingang/Downloads/sens-workspace/Plantuml/cngg_interface_data_component.puml`
