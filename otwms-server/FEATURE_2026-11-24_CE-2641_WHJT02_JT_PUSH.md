# 2026-11-24 CE-2641 WHJT02 推 J&T 下单规则

## 结论

WHJT02 门店经"操作 > 外部派送"推 J&T 下单接口时：推送重量 ≤10.1 推 `productType=TC`，否则推空；COD（瑞尔）按十位四舍五入到百位，0 推 0，0<COD<50 推 100。其他门店不变。UAT 验收通过，已合入 master `02f3315ed`（与 CE-2644 一起），**2026-11-24 15:49 生产部署（#200）**。

## 分支与提交（`bugfix/CE-2641`）

| 提交 | 作者 | 内容 |
|---|---|---|
| `eed46f11b`、`03fdd3aa7` | YUTH（SiGentIsHere） | 加 `productType`，按渠道名 `WHJT02` 推 TC；加 `[JT-Submit]` 日志 |
| `482d29600` | sens | 按登录门店识别 WHJT02；重量规则；COD 取整 |
| `ff68b2297` | sens | 0<COD<50 推 100 |

只改 `LogisticsInfo`、[`ExternalDeliveryManager`](otwms-backend/src/main/java/org/springblade/otwms/business/externaldelivery/manager/ExternalDeliveryManager.java)。

## 关键决定

- **WHJT02 识别**：改为登录用户 `shopCode == WHJT02`（`CommonConstant.CE_FRANCHISEE_SHOP`），与选 J&T 客户号同一条件，保证 TC/COD 与推送的 customerid 一致。原按渠道名判断：UAT 渠道只有 `JT`（门店 WHJT）、`BS`，没有叫 WHJT02 的渠道。
- **COD 只对 WHJT02 生效**（用户决定）。取整放在 `builderCod`，下单推送、`jt_cod` 存库、页面预览、改 COD（ORDERUPDATE）一致。
- **重量**按实际推送值（两位小数、截断）比较，10.109 → 10.10 → TC。

## J&T 账号与地址（启动脚本 `gs://cambodian-express/scripts/<env>/startup.sh`）

| 环境 | 主账号 | WHJT02 账号 | `jt.url` |
|---|---|---|---|
| 生产 | `J0086004000` | `J0086003863`（用户确认） | `genapi.jtexpresskh.com` |
| UAT | `J0086000286` | 未覆盖，代码默认 `J0086000316` | `test-genapi.jnt-express.com.cn` |

yml 中无 `jt.*` 配置，全靠启动参数/代码默认值。

## UAT 验收（2026-11-24，构建 #498，qa `0b96a8640`）

WHJT02 账号在 UAT 新建测试单（预付，J&T 汇率 4100），经"外部派送"提交，以 `external_delivery.push_content` 核对：

| 运单 | 重量 | 瑞尔 COD | productType | 推送 COD | J&T 单号 |
|---|---|---|---|---|---|
| CE24112600005 | 10.10 | 1148 | TC | 1100 | U01200634316 |
| CE24112600006 | 10.11 | 2050 | 空 | 2100 | U01201178506 |
| CE24112600007 | 5.00 | 0 | TC | 0 | U01200776506 |
| CE24112600008 | 25.00 | 41 | 空 | 100 | U01200962035 |

- 改 COD 推送：CE24112600005 改 0.29 USD（1189）→ `jt_cod` 1200，J&T 接受。
- 未测：非 WHJT02 门店对照（无账号；代码路径原样返回）。
- 遗留测试单 `CE24112600001~0004`（目的城市 `B01` 被判异常区域，未推送），留在 WHJT02，是否取消待用户决定。

## 过程问题

- qa 合并后 UAT #497 编译失败，原因在 CE-2644（见 [CE-2644 记录](INCIDENT_2026-11-21_SHIPMENT_REPORT_STATUS_SYNC.md)），修复后 #498 成功。
- qa、master 均由 agent 经 git 合并推送（用户授权），Bitbucket 无对应 PR。

## 待办

- [x] 生产部署：Jenkins #200（11-24 15:49）检出 `02f3315ed`、BUILD SUCCESS；实例组替换为 `otwms-group-8w54`，15:52 应用在处理请求，无异常/整批 `Error sync`。
- [x] 生产首单（只读，用户在 Chrome 登录 WHJT02）：CE24112600028，到付、COD 0、运费 2.28，重量 10.00；推送 customerid `J0086003863`、productType `TC`、itemsvalue 9300（2.28×4100=9348→9300），与 `jt_cod` 一致，J&T 单号已返回。
- [x] J&T 接口方反馈未收到 `productType=TC`：对方确认字段名应为 `expressTypeCode`（原字段被忽略，所以此前下单都成功）。分支 `bugfix/CE-2641-express-type-code`（基于 master，提交 `be45d4ffe`）只改字段名；合入 qa `e3cd2f4de`，UAT #499 成功。
- [ ] UAT 推送（11-24 18:03）：`expressTypeCode=TC` 的 CE24112600009 被 J&T 测试环境拒绝，原因 **B094**；对照 CE24112600010（重量 12，值为空）成功（U01201191473）。说明对方已识别该字段，B094 与 `TC` 取值有关，疑为测试客户号 `J0086000316` 未开通 TC。接口方技术确认 B094 是其测试环境问题，生产只需改用 `expressTypeCode`。已合入 master `54cf8310d`（文件与 UAT #499 qa 一致），待生产部署后核对首批 WHJT02 推送（TC 单是否下单成功）。
- [ ] 告知 YUTH：其分支追加了提交，WHJT02 识别方式已改。
