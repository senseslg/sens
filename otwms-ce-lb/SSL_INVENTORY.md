# CE LB SSL Inventory

## 当前结论

**2026-09-17：官网 HTTPS 已恢复。** `cambodianexpress.com`、`www.cambodianexpress.com`、`cp.cambodianexpress.com` 三张证书已重新签发并加载，有效至 `2026-12-16`。公网标准 TLS 验证通过，根域名返回 301，`www` 返回完整 WordPress 页面（HTTP 200）。Certbot Cron 的 Nginx 路径问题已修复，官网证书在模拟 Cron 环境下 dry-run 通过；其他历史证书的续期失败仍待清理。

## 2026-09-17 恢复验收

| 域名 | 证书到期（UTC） | 公网结果 |
|---|---|---|
| `cambodianexpress.com` | `2026-12-16 09:33:29` | TLS 验证通过，301 到 `www` |
| `www.cambodianexpress.com` | `2026-12-16 09:36:53` | TLS 验证通过，HTTP 200、约 92 KB WordPress 页面 |
| `cp.cambodianexpress.com` | `2026-12-16 09:37:53` | TLS 验证通过；后端恢复后公网 HTTP 200 |

故障原因：`2026-09-16` 的 Cron 仍因缺少 `/sbin` 而报 `Could not find a usable 'nginx' binary`，导致 11 项续期失败。经用户授权，已在服务器本机备份 Cron、Nginx 和三张续期配置至 `/root/ssl-recovery-20260917T1030Z/`；只针对这三张证书执行续期并由 Certbot 重载 Nginx。root crontab 已增加 `PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`，仍保留每日 `12:00 UTC` 的原调度。`www` 在该 PATH 的最小环境下 dry-run 成功；最终 Nginx 配置测试通过，公网正式证书已复核。

下次同类故障的只读判断、授权恢复和验收步骤见 [RUNBOOK.md](RUNBOOK.md#官网证书过期时的恢复流程)。

## 2026-08-10 历史配置快照

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
- root crontab 每日 `12:00 UTC` 执行 `/usr/bin/certbot renew --quiet`；已显式设置包含 `/sbin` 的 PATH。
- 三张官网相关证书使用 `nginx` authenticator/installer；旧 Cron 缺少 `/sbin` 是本次过期原因。
- 主域名、`www` 与 `cp` 的上一批证书签发于 `2026-06-15`；截至 `2026-08-10` 尚余 34 天，当时 Certbot 判定未到续期时间。

## 2026-08-10 自动续期核查

| 检查项 | 结果 | 判断 |
|---|---|---|
| Cron 配置与触发 | 每日 `12:00 UTC` 运行；`2026-08-09 12:00 UTC` 日志存在 | 调度生效 |
| 最近自动任务 | 7 个历史证书续期失败；原因均为 Cron 环境找不到 Nginx | 续期链路故障 |
| `2026-06-15 12:00 UTC` 自动任务 | 11 个证书全部因相同 Nginx 路径问题失败 | 自动续期未成功 |
| `2026-06-15 12:55 UTC` 二次运行 | 主域名、`www`、`cp` 成功签发并自动 reload Nginx；7 个历史域名仍失败 | 有效证书已恢复，但该运行不在现有 Cron 计划时刻，触发来源未确认 |
| 公网实际证书 | 三个域名序列号与服务器当前证书一致，均有效至 `2026-09-13` | 当前访客证书有效 |

以上是 `2026-08-10` 的历史判断；`2026-09-17` 已修复 Cron PATH 并重新签发三张官网相关证书。

## 风险与下一步

- [ ] 复核下一次 `12:00 UTC` Cron 的实际执行日志；dry-run 成功不等于计划任务已完成一次真实运行。
- [ ] 逐项确认 `api-scm`、`scm`、`nacos`、`mp-api` 等其他过期 lineage 是否仍有业务；仍使用则按有效 DNS 修复，不再使用则先移除 Nginx 引用再清理续期项。整批 `certbot renew` 仍可能因旧项报错。
- [x] `cp.cambodianexpress.com` 页面超时已在 `wms-server` 扩容后解除；其证书正常。
- [ ] 为 Certbot 失败增加告警，避免 `--quiet` 长期无人发现。
- [ ] 评估升级 Certbot、Nginx、OpenSSL 和操作系统，先在替代环境验证，不直接原地升级生产实例。

本次未读取或复制私钥内容，也未处理无关的历史证书。
