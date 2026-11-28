# Project Overview

## What This Project Is

API Google Geo 是一个经纬度反向地理编码服务。用户通过 Token 鉴权调用接口，传入经纬度坐标，服务调用 Google Maps Geocoding API 解析地址信息，并将省份和市/区匹配到业务数据库中的地区表，返回结构化结果。

## 核心接口设计

### 请求

- 方式：HTTP GET 或 POST
- 鉴权：Header 或参数中携带 `token`
- 参数：
  - `lat`：纬度（Latitude），必填，DECIMAL(10,7)
  - `lon`：经度（Longitude），必填，DECIMAL(10,7)

### 响应（成功）

```json
{
  "code": 0,
  "msg": "ok",
  "data": {
    "province": 123,
    "district": 456,
    "country": "中国",
    "province_name": "广东省",
    "district_name": "深圳市",
    "route": "南山大道",
    "street_number": "88号",
    "formatted_address": "中国广东省深圳市南山区南山大道88号",
    "postal_code": "518000",
    "plus_code": "7PG8+QF 深圳市"
  }
}
```

### 响应（失败）

```json
{
  "code": -1,
  "msg": "token invalid or expired"
}
```

## Google Geocoding API 字段提取规则

调用地址：

```
https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&result_type=street_address|premise|subpremise&location_type=ROOFTOP|RANGE_INTERPOLATED&language=zh-CN&key={key}
```

从 `results[0].address_components` 中按 `types[0]` 提取：

| 字段                       | types[0]                     | 说明            |
|---------------------------|------------------------------|-----------------|
| 国家                       | `country`                    | long_name       |
| 省份/直辖市                | `administrative_area_level_1` | long_name       |
| 市/区                      | `administrative_area_level_2` | long_name       |
| 乡镇/街道                  | `route`                      | long_name       |
| 街道/门牌号                | `street_number`              | long_name       |
| 详细地址                   | —                            | formatted_address|
| 邮编                       | `postal_code`                | long_name       |
| Plus Code                 | —                            | plus_code.global_code |

## 地区匹配逻辑

- 省份/直辖市：查询 `new_ccsl.area`，条件为 `level = 2 AND is_deleted = 0 AND name LIKE '%{province_name}%'`，取 `id` 作为 `province`
- 市/区：查询 `new_ccsl.area`，条件为 `level = 3 AND is_deleted = 0 AND name LIKE '%{district_name}%'`，取 `id` 作为 `district`

## 数据库表结构

### api_token（Token 管理表）

```sql
CREATE TABLE api_token (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    token       VARCHAR(64)  NOT NULL UNIQUE COMMENT 'API Token 值',
    name        VARCHAR(100)          COMMENT 'Token 名称/备注',
    expired_at  DATETIME     NOT NULL COMMENT 'Token 过期时间',
    is_active   TINYINT      NOT NULL DEFAULT 1 COMMENT '1=启用 0=禁用',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_token (token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API Token 管理';
```

### api_request_log（请求日志表）

```sql
CREATE TABLE api_request_log (
    id                       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    token_id                 BIGINT UNSIGNED NOT NULL COMMENT '关联的 token.id',
    token                    VARCHAR(64)     NOT NULL COMMENT '请求时使用的 token 值（冗余存储便于查询）',
    request_ip               VARCHAR(45)              COMMENT '请求方 IP',
    request_lat              DECIMAL(10,7)   NOT NULL COMMENT '请求纬度',
    request_lon              DECIMAL(10,7)   NOT NULL COMMENT '请求经度',
    google_status            VARCHAR(20)              COMMENT 'Google API 返回的 status 字段',
    response_country         VARCHAR(100)             COMMENT '国家',
    response_province        VARCHAR(100)             COMMENT '省份/直辖市（原始文本）',
    response_district        VARCHAR(100)             COMMENT '市/区（原始文本）',
    response_route           VARCHAR(200)             COMMENT '乡镇/街道',
    response_street_number   VARCHAR(100)             COMMENT '街道/门牌号',
    response_formatted_addr  VARCHAR(500)             COMMENT '详细地址（formatted_address）',
    response_postal_code     VARCHAR(20)              COMMENT '邮编',
    response_plus_code       VARCHAR(30)              COMMENT 'Plus Code（global_code）',
    province_id              BIGINT UNSIGNED          COMMENT '匹配到的省份 area.id（level=2）',
    district_id              BIGINT UNSIGNED          COMMENT '匹配到的市/区 area.id（level=3）',
    status                   TINYINT         NOT NULL DEFAULT 1 COMMENT '0=失败 1=成功',
    error_message            TEXT                     COMMENT '失败时的错误信息',
    response_time_ms         INT UNSIGNED             COMMENT 'Google API 响应耗时（毫秒）',
    created_at               DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_token_id   (token_id),
    INDEX idx_token      (token),
    INDEX idx_created_at (created_at),
    INDEX idx_status     (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API 请求日志';
```

## 外部依赖

- Google Maps Geocoding API（需要有效的 API Key）
- MySQL 数据库 `new_ccsl`，表 `area`（字段：id, name, level, is_deleted）

## Working Rules For Future Changes

- Token 鉴权逻辑集中维护，不在接口层散落校验代码。
- Google API 调用封装为独立的 service/module，便于替换或 Mock。
- 地区匹配逻辑封装为独立函数，失败时降级返回 `null` 而不是报错中断。
- 每次接口调用必须写入 `api_request_log`，包括失败请求。
- 更新稳定行为时同步更新 `PROJECT_OVERVIEW.md` 和 `PROJECT_ITERATION_LOG.md`。
