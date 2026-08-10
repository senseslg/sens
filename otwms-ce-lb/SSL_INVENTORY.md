# CE LB SSL Inventory

## 当前结论

`ce-lb` 使用 Nginx 终止 TLS，证书由 Certbot 管理。`cambodianexpress.com`、`www.cambodianexpress.com` 和 `cp.cambodianexpress.com` 的独立证书当前有效；多个历史或仍在配置中的证书已经过期，需要按域名是否仍使用分别续期或下线。

## 2026-08-10 生效配置快照

| 域名 | Nginx 用途 | 证书状态 |
|---|---|---|
| `cambodianexpress.com` | HTTPS 301 跳转到 `www` | 匹配；有效至 `2026-09-13 11:57 UTC` |
| `www.cambodianexpress.com` | 本机 WordPress/PHP 官网 | 匹配；有效至 `2026-09-13 11:58 UTC` |
| `cp.cambodianexpress.com` | 反向代理到内网服务 | 有效至 `2026-09-13 11:58 UTC` |
| `api-scm.cambodianexpress.com` | 反向代理到内网服务 | 已于 `2022-09-20` 过期 |
| `scm.cambodianexpress.com` | 反向代理到内网服务 | 已于 `2023-03-22` 过期 |
| `nacos.cambodianexpress.com` | 反向代理到内网 Nacos | 引用的旧多域名证书已于 `2020-11-15` 过期 |
| `mp-api.ssl-global.cn` | 反向代理到内网服务 | 引用的旧多域名证书已于 `2020-11-15` 过期 |
| `ccsl.cambodianexpress.com` | 反向代理到外部 HTTP 上游 | 当前配置仅监听 HTTP 80 |

过期证书不等于对应域名当前仍对公网提供服务；必须结合 DNS、GCP 防火墙和业务状态判断是续期还是下线。

## 续期机制

- Certbot 版本：`1.11.0`。
- 有效证书使用 `nginx` authenticator 与 installer。
- `certbot-renew.timer` 已安装但处于 disabled/inactive。
- root crontab 每日 `12:00 UTC` 执行 `/usr/bin/certbot renew --quiet`。
- 主域名、`www` 与 `cp` 当前证书签发于 `2026-06-15`；下次续期必须在到期前验证结果和 Nginx 加载状态。

## 风险与下一步

- [ ] 确认 `api-scm`、`scm`、`nacos` 和 `mp-api` 是否仍有业务与 DNS；仍使用则修复续期，不再使用则移除入口和续期配置。
- [ ] 在 `2026-09-13` 前验证主域名、`www`、`cp` 自动续期成功，并复查实际 SNI 证书。
- [ ] 检查 Certbot 续期失败日志与告警，避免 `--quiet` 失败无人发现。
- [ ] 评估升级 Certbot、Nginx、OpenSSL 和操作系统，先在替代环境验证，不直接原地升级生产实例。

检查只读取证书公开信息；未读取或复制私钥内容。
