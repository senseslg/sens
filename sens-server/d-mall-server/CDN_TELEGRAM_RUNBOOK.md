# CDN 证书与 Telegram 告警

2026-11-19 经用户授权在 D-Mall 启用。仅维护 `static.ceccsl.com` 证书同步及告警，不部署移动站、不改 Nginx、不重启业务。

## 当前配置

| 对象 | 路径 / 行为 |
|---|---|
| 证书签发 | sens 的既有 acme.sh cron；原续期配置及 Nginx reload 不变 |
| CDN 部署工具 | `/home/sens/.local/lib/ccsl-cdn-cert-sync/deploy-static-cdn.py` |
| RSA 部署钩子 | `/home/sens/.acme.sh/deploy/ccsl_static_cdn.sh`；只处理 ceccsl.com RSA lineage |
| 监控工具 | `/home/sens/.local/lib/ccsl-cdn-cert-sync/cdn-cert-monitor.py` |
| Telegram 共享 helper 副本 | 同目录 `telegram_send.py`；来自本机 telegram-CCSL-Service 的 send.py |
| Telegram 凭据 | `/home/sens/.config/ccsl-cdn-cert-sync/telegram.json`，600，父目录 700；不得打印、提交或复制到文档 |
| 告警状态 / 锁 | `/home/sens/.local/state/ccsl-cdn-cert-sync/`，700；状态文件 600 |
| 变更前备份 | `/home/sens/.config/ccsl-cdn-cert-sync/telegram-deploy-n1b9mdoc/`，700；含 `hook.before`、`crontab.before`、`rsa-config.before` |
| 周期检查 | sens crontab 每小时第 17 分钟；cron 守护进程已确认 active |

cron 使用服务器时区，但按每小时执行，不受金边/UTC 的小时差影响；消息时间统一显示金边 UTC+7。

```cron
17 * * * * /usr/bin/python3 /home/sens/.local/lib/ccsl-cdn-cert-sync/cdn-cert-monitor.py --apply 2>&1 | /usr/bin/logger -t ccsl-cdn-cert-monitor
```

原有 3 条 cron 保留，新检查恰好 1 条。检查只读证书和公网 TLS，`--apply` 只允许写去重状态及发送通知，**不自动续签、更新 CDN 或重启服务**。实际证书更新仍由既有 acme.sh deploy hook 调用部署工具。

## 通知规则

- 首次失败立即发送；同一未恢复故障最多每 24 小时提醒一次。定时检查每小时发现新问题；钩子失败则当次触发。
- 从普通异常升级为公网 TLS 无法校验时立即告警，不等日提醒；持续同一紧急状态仍去重。
- 公网及续期证书一致、有效且不在不足 7 天预警窗口时，恢复通知一次。正常成功不刷屏。
- 校验本地 RSA 原始证书与公网证书指纹、有效期；不足 7 天预警。不要把 HTTP 200 当作完整业务验收。
- 通知只包含域名、金边时间、失败分类、证书状态/到期时间及处理提示，不含密钥和原始日志。
- Telegram 发送失败或超时只记脱敏日志，不自动立即重发；先记录尝试以避免投递未知时刷屏。持续故障下一次可发送时间由去重状态决定。恢复消息投递失败不盲目重发，需人工核查。
- 本机 Mac 关机不影响服务端发送。但 D-Mall 整机停机/断网时，本机监控本身无法发出通知；外部独立存活监控尚未配置。

## 只读检查

```sh
# 不写状态、不发送 Telegram；0 正常、1 发现异常、2 执行错误
python3 /home/sens/.local/lib/ccsl-cdn-cert-sync/cdn-cert-monitor.py

# 校验公网与已安装 RSA 证书一致
python3 /home/sens/.local/lib/ccsl-cdn-cert-sync/deploy-static-cdn.py \
  --verify-public --certificate-dir /home/sens/ssl/ceccsl.com/rsa

# 只检查通知配置与 TLS 上下文，不请求 Telegram
python3 /home/sens/.local/lib/ccsl-cdn-cert-sync/telegram_send.py \
  --check --config /home/sens/.config/ccsl-cdn-cert-sync/telegram.json
```

监控日志标签 `ccsl-cdn-cert-monitor`；钩子日志标签 `ccsl-cdn-cert-sync`。不要输出完整 cron、acme 配置、凭据或私钥；只查必要的脱敏摘要。

## 回退（写操作，需授权）

1. 核对当前 cron 和钩子是否有后续修改；只删本次的 monitor cron 行及对应注释，不覆盖其他任务。
2. 用备份 `hook.before` 恢复 `ccsl_static_cdn.sh`，权限 700，执行 `sh -n`。原证书同步能力保留，只停用新增通知。
3. 原 `ceccsl.com.conf` 未修改，不需要恢复整个 RSA 配置；不要回退云端到过期证书。
4. 组件和凭据可先保持受限、停用状态；如需删除，精确核对本次新增文件并另行授权，不删除共享 Bot 或本机原始凭据。

## 验证及操作记录（金边 UTC+7）

| 时间 | 操作 | 结果 |
|---|---|---|
| 2026-11-19 03:26–03:30 | 备份、安装通知组件/凭据及每小时检查 | 文件权限通过；原 cron、RSA 配置及 Nginx reload 保持不变 |
| 2026-11-19 03:30 前 | 从 D-Mall 发送单条明确标注的服务端测试消息 | Telegram `ok=true`，消息 3437；用户确认收到；具体发送分钟未单独记录 |
| 2026-11-19 03:30 | 调用实际证书钩子、只读检查及部署后核对 | CDN 同证书幂等跳过，监控正常无额外通知，应用入口 200 |

11 项离线回归已在本机及服务端通过，含日提醒去重、紧急升级、单次恢复、发送失败不立即重试。未人为制造生产证书故障，未强制续签；下一次真实续期与首次自然 cron 运行仍待观察。

工具源文件及账号业务记录位于本机 `/Users/lingang/work/new_ccsl/tools/cert-renewal-deploy/` 与 `alicloud-back-end-mangement/internation-edition/STATIC_CDN.md`。复用现有 Telegram helper，无额外常驻 HTTP 服务或全局 skill。
