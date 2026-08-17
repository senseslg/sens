# CE LB SSL Inventory

## 当前结论

**自动续期未完整生效。** `ce-lb` 的 Cron 会每天启动 Certbot，但当前 Cron 环境找不到 `nginx` 可执行文件；最近一次 `2026-08-09` 自动任务仍报告 7 个续期失败。`cambodianexpress.com`、`www.cambodianexpress.com` 和 `cp.cambodianexpress.com` 当前证书有效，是 `2026-06-15 12:55 UTC` 非 Cron 计划时刻的二次运行成功更新的结果，不能证明现有自动续期链路可靠。

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
- Cron 确实每日触发，但环境 `PATH` 只有 `/usr/bin:/bin`，不包含 Nginx 所在的 `/sbin/nginx`；三张有效证书均使用 `nginx` authenticator/installer，因此插件报 `Could not find a usable 'nginx' binary`。
- 主域名、`www` 与 `cp` 当前证书签发于 `2026-06-15`；截至 `2026-08-10` 尚余 34 天，Certbot 判定未到续期时间。

## 2026-08-10 自动续期核查

| 检查项 | 结果 | 判断 |
|---|---|---|
| Cron 配置与触发 | 每日 `12:00 UTC` 运行；`2026-08-09 12:00 UTC` 日志存在 | 调度生效 |
| 最近自动任务 | 7 个历史证书续期失败；原因均为 Cron 环境找不到 Nginx | 续期链路故障 |
| `2026-06-15 12:00 UTC` 自动任务 | 11 个证书全部因相同 Nginx 路径问题失败 | 自动续期未成功 |
| `2026-06-15 12:55 UTC` 二次运行 | 主域名、`www`、`cp` 成功签发并自动 reload Nginx；7 个历史域名仍失败 | 有效证书已恢复，但该运行不在现有 Cron 计划时刻，触发来源未确认 |
| 公网实际证书 | 三个域名序列号与服务器当前证书一致，均有效至 `2026-09-13` | 当前访客证书有效 |

证书归档显示三条有效 lineage 曾多次更新，但本次结论以最近两次进入续期流程的日志为准：现有 Cron 能触发 Certbot，不能可靠完成基于 Nginx 插件的续期。

## 风险与下一步

- [ ] 确认 `api-scm`、`scm`、`nacos` 和 `mp-api` 是否仍有业务与 DNS；仍使用则修复续期，不再使用则移除入口和续期配置。
- [ ] 在 root crontab 显式加入包含 `/sbin`、`/usr/sbin` 的安全 `PATH`，保留唯一一套续期调度，避免 Cron 与 systemd timer 重复运行。
- [ ] 逐项确认 7 张失败的历史证书是否仍有业务；仍使用则按有效 DNS 拆分重签，不再使用则在移除 Nginx 引用后删除对应 Certbot lineage。
- [ ] 修复后执行受控的 Certbot 测试，并在 `2026-09-13` 前复查主域名、`www`、`cp` 的实际 SNI 证书。
- [ ] 为 Certbot 失败增加告警，避免 `--quiet` 长期无人发现。
- [ ] 评估升级 Certbot、Nginx、OpenSSL 和操作系统，先在替代环境验证，不直接原地升级生产实例。

本次仅检查 Cron、Certbot 日志和证书公开字段，未运行 `certbot renew`/`--dry-run`，未读取或复制私钥内容。
