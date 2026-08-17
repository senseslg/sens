# 2026-08-16 官网域名停放事故

## 当前结论

`www.cambodianexpress.com` 当前未进入 `ce-lb` 官网源站，而是由 GoDaddy 权威 DNS 指向域名停放页。用户已确认根因是域名到期且尚未续费；源站绕过 DNS 后仍能返回完整 WordPress 页面，因此不是 WordPress、Nginx 或原 Let's Encrypt 证书失效。

## 关键证据

- `www` 当前 CNAME 到根域名；根域名由 GoDaddy 权威 DNS 返回停放目标。
- 公网访问返回约 114 字节的跳转脚本，并进入 `/lander`；证书是 `2026-08-15` 新签发的 GoDaddy 证书。
- 绕过 DNS 直接访问原 `ce-lb`，Nginx/PHP 返回 HTTP 200 和约 92 KB 的完整 WordPress 页面。
- Verisign RDAP 显示域名于 `2026-08-15 15:14 UTC` 更新，Registry 到期日暂显示为 `2027-08-11`；该日期可能来自注册局自动续期宽限期，不能证明 GoDaddy 账户已完成付款续费。
- GoDaddy 权威查询未返回原有 `mail` 与 MX 记录，需要立即核对邮件解析是否也受影响。
- 用户于 `2026-08-16` 确认 GoDaddy 域名已到期且尚未续费。

## 影响

- 官网访客看到 GoDaddy 停放页，无法访问真实网站。
- 根域名和 `www` 当前使用 GoDaddy 停放证书，不再使用 `ce-lb` 上的证书。
- 若权威 DNS 中的邮件记录确实丢失，新邮件投递和客户端连接可能受影响；需以 GoDaddy DNS 管理页实际记录为准。

## 恢复建议

1. 在 GoDaddy 完成域名续费，并确认停放状态解除。
2. 续费后检查原 DNS 是否自动恢复；如未恢复，从可信备份或变更记录恢复根域名、`www`、`mail`、MX、SPF、DKIM 和 DMARC，不能只修官网两条记录。
3. 等待 DNS 生效后，从多个解析器复查权威结果、公网页面、证书和邮件路由。
4. 恢复后继续修复 `ce-lb` Certbot 自动续期，避免 DNS 恢复后再发生证书到期。

本次仅执行公网、注册信息和源站只读检查，未修改 GoDaddy、DNS 或生产服务器。
