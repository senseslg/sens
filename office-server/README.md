# office-server

办公室服务器相关工作的子项目记录。

## 阅读顺序

1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：目标、范围、当前状态、行动项和风险。
2. [SERVER_INFO.md](SERVER_INFO.md)：服务器资产、SSH、网络、安全和备份基线。

## 当前状态

- 状态：`proposed`
- 建立日期：`2026-08-08`
- 已完成：创建项目记录、采集脱敏基线并验证 SSH Key 登录。
- 待确认：服务器用途、负责人、部署范围、安全加固和备份方案。

## 安全边界

- 不记录密码、Token、私钥、Cookie 或完整生产连接串。
- 服务器地址、账号和其他资产信息写入前必须脱敏。
