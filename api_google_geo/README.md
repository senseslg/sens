# API Google Geo

Google Geocoding 反向地址解析服务。接收用户提供的经纬度，调用 Google Maps Geocoding API，提取结构化地址信息，并将省份和市/区匹配到 `new_ccsl.area` 表中的对应记录返回。

## 功能说明

- 接受 `lat`（纬度）和 `lon`（经度）参数
- 调用 Google Maps Geocoding API 获取结构化地址
- 提取国家、省份/直辖市、市/区、街道、门牌号、详细地址、邮编、Plus Code
- 将省份和市/区与 `new_ccsl.area` 表匹配，返回对应 `id`
- Token 鉴权，支持过期时间
- 记录完整请求日志

## 返回字段

| 字段        | 说明                             |
|------------|----------------------------------|
| province   | new_ccsl.area 中 level=2 的 id  |
| district   | new_ccsl.area 中 level=3 的 id  |

## 项目文档

开发前请先阅读：

1. `PROJECT_READ_FIRST.md`
2. `PROJECT_OVERVIEW.md`
3. `PROJECT_ITERATION_LOG.md`
