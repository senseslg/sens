# Project Iteration Log

每个版本 / 重要变化一行，最新在上：`- **vX.Y.Z** YYYY-MM-DD — 一句话描述`。架构、字段与业务规则细节见 `reference/`。

---

- **v0.3.0** 2026-11-27 — 经授权创建只读 RAM 用户 `ali-oss-ops` 并配置本机凭据，脚本真实调用验证通过；新增 `import-csv`（10 项离线测试）；记录用户确认的 `ceccsl`/`uat-mallgogo`/`daniel-cel-shop` 用途
- **v0.2.0** 2026-11-27 — 控制台只读采集 7 个 Bucket、域名与健康检测（284/500，5 个公共读）；新增标准库 OSS API 脚本（默认 dry-run、受保护桶需确认，9 项离线测试通过，真实调用待凭据）与分阶段安全加固方案（待决定）；发现 `uat-mallgogo` 占约 94% 流出流量
- **v0.1.0** 2026-11-27 — 新建 OSS 管理子项目并接入 agent 框架 v0.3.1；汇总既有 Bucket 记录。Chrome（Browser 1）访问国际站控制台被重定向到登录页，控制台信息未采集（T-001 blocked）
