# 后台前端模块到业务 SQL 的定位方法

## 适用场景

- 收到“某后台页面/模块查询慢/结果不对”，需要确认该模块点击查询时实际执行的 SQL。
- 只有前端菜单路径（如 管理后台 > 运单轨迹）或页面名称，没有接口 URL 和 Java 类名。

## 本次结论（运单轨迹模块）

- “运单轨迹”等后台菜单标题**不在前端源码里写死**，由 BladeX 动态菜单（`blade_menu`）下发，标题还可能被运行时 i18n 覆盖；源码里搜索菜单中文名通常搜不到，不代表模块不存在。
- 该模块“轨迹时间线”的数据源是事件表 `tms_shipment_event`（运单每到一个操作节点产生一条事件，轨迹 = 这些事件的列表），不管从哪个页面进入都走同一个接口：

```text
POST /tms-shipment-event/query        body: ["运单号", ...]
```

- 前端调用点（快照：frontend master `5cda7fb`，2026-08-12）：
  - `otwms-frontend/src/api/Ordermanagement/order.js`：`tmsShipmentEvent`（第 443～450 行）指向 `/tms-shipment-event/query`；`remark`（第 628～635 行）指向 `/tms-shipment-event/remark`。
  - `otwms-frontend/src/views/Ordermanagement/orderTracking.vue`：订单详情里的轨迹/跟踪面板，`getList: tmsShipmentEvent`，入参 `[this.shipmentCode]`；由 `Ordermanagement/order.vue` 抽屉（`jumpDetail`）打开，抽屉标题 `pageview.other15`（zh.js = “订单跟踪”）。
  - `otwms-frontend/src/views/ExpressOrderManagement/ScanOrderTracking.vue`（含 `ScanOrderTracking/` 目录变体）：扫码/输号查轨迹，轨迹页签同样调 `tmsShipmentEvent`，另并行调异常 `/exception-item/query`、备注 `/tms-shipment-event/remark`、运单信息 `/tms-shipment/track`。
- 后端链路（快照：backend branch `codex/fix-daily-bill-revenue-cost-batching` @ `a77eb6e71`，2026-08-17）：
  - `org/springblade/tms/controller/TmsShipmentEventController.java` `POST /query` → `getTmsShipmentEventByShipmentCodes`。
  - `org/springblade/tms/service/impl/TmsShipmentEventServiceImpl.java` 第 72～119 行。

### 轨迹列表主 SQL

第 73 行是 MyBatis-Plus `lambdaQuery().in(...).list()`，无手写 XML，框架按实体自动生成，等价于：

```sql
SELECT id, shipment_code, order_code, event_code, event_text,
       tracking_event_code, tracking_event_desc, tracking_event_desc_km, tracking_event_desc_zh,
       event_time, operator, operator_role, event_courier, place, location_code,
       event_shop, longitude, latitude, location_type, address_details,
       village_code, city_code, province_code, country_code, event_source,
       route_code, prev_stop, next_stop, trip_no, batch_no, picture_flag,
       picture_url, customer, remark, creation_date, created_by,
       last_update_date, last_updated_by, file_id
FROM tms_uat.tms_shipment_event
WHERE shipment_code IN (/* 传入的运单号集合 */);
```

- 实体 `org/springblade/tms/entity/TmsShipmentEvent.java`：`@TableName(value = "tms_shipment_event", schema = "tms_uat")`，故 SQL 带 `tms_uat.` schema 前缀；应用数据源默认 catalog 是 `otwms`，两者不同，不要混。
- 该多单入口不按 event_code 过滤；单号入口 `getTmsShipmentEventByShipmentCode`（ServiceImpl 第 66～69 行）会排除事件码 10/90/99/100/120/140，但只被 C 端 App / Telegram bot 使用。

### 同一次调用附带执行的 SQL

1. 取消轨迹合并（ServiceImpl 第 74～77、121～149 行；`TmsOrderEventServiceImpl.getTmsOrderCancelEventList` 第 70～78 行）：

```sql
SELECT * FROM tms_uat.order_event            -- @TableName(schema="tms_uat", value="order_event")
WHERE shipment_code IN (...) AND order_status = '10';      -- OrderBusinessStatus.ORDER_CANCEL
```

```sql
-- 业务状态仍为取消时，取最新一条取消单，合成 event_code='999' 的轨迹：
SELECT * FROM cancel_order WHERE shipment_code = ? ORDER BY cancel_time DESC LIMIT 1;
```

2. POD/异常图片 fileId 回填（`TmsShipmentEventMapper.xml` `getTmsFileIdByTrackingEventCodeAndType`，事件码 80/86/150 时触发）：

```sql
SELECT sf.FILE_ID
FROM tms_uat.sys_attachment sa, tms_uat.sys_file sf
WHERE sf.ATTACHMENT_ID = sa.ATTACHMENT_ID
  AND sa.SOURCE_TYPE = #{type}            -- SHIPMENT_POD / SHIPMENT_EXCEPTION
  AND sa.SOURCE_KEY = #{trackingEventCode};
```

3. 备注列表（若页面含备注页签，`POST /tms-shipment-event/remark` → `queryRemarkByShipmentCodes`）：

```sql
SELECT * FROM tms_uat.tms_shipment_event
WHERE shipment_code IN (...) AND event_code = '99';        -- REMARK
```

4. 若页面同时显示运单基础信息（收寄件人/运费等），另走 `POST /tms-shipment/track` → `TmsShipmentManager.queryTrack`（`TmsShipmentManager.java` 第 150 行起），查的是 `tms_shipment` 主表，不属于轨迹时间线。

## 只读定位顺序（任意模块通用）

1. 用页面 URL 或菜单名反查菜单表，确认模块绑定哪个前端组件：
   ```sql
   SELECT id, name, path, component, source
   FROM blade_menu
   WHERE name LIKE '%模块中文名%';          -- 只读，先确认表在哪个库/catalog
   ```
   `component` 即 `src/views/` 下的 vue 路径；也可直接让用户提供 Network 里的接口 URL 跳过这步。
2. 在前端 `src/api/**` 里按 URL 片段反查封装函数，再 grep 该函数被哪些 `views/**` 页面使用，确认触发入口和入参。
3. 在后端按 URL 片段找 `@RequestMapping` Controller，落到具体 service 方法。
4. 判断 SQL 来源：
   - MyBatis-Plus `lambdaQuery()/queryWrapper` → 框架自动生成，按实体 `@TableName`/字段还原（camelCase→snake_case，`map-underscore-to-camel-case: true`）。
   - 手写 SQL → 在 **`src/main/java/.../mapper/*Mapper.xml`** 下找同名 mapper XML（本项目 XML 放在 java 目录树，`src/main/resources` 下没有 mapper XML；`mapper-locations` 配置 `classpath:org/springblade/**/mapper/*Mapper.xml`）。
5. 还原 SQL 后，涉及慢查询时按 [mysql-large-in-query.md](mysql-large-in-query.md) 做只读 EXPLAIN 诊断，不直接跑真实 SELECT。

## 判定标准

- 前端封装函数 URL 与后端 Controller mapping 一致。
- grep 到的页面确实是菜单 `component` 对应的 vue。
- service 方法与 XML/lambda 查询逐行对应，实体表名与库中 `SHOW INDEX`/`information_schema.TABLES` 一致。

## 安全边界

- 不输出数据源密码、连接串明文或业务 shipment code 原文。
- 菜单/字典确认只读；不要为“看 SQL”在生产库执行未知 SELECT 或 COUNT。
- 行号随源码快照漂移：引用时标注所在文件与当时的 Git commit。
- 菜单中文名查不到不代表模块不存在；先确认菜单/i18n 来源，再下结论。
