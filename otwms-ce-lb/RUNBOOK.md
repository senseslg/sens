# OTWMS CE LB Runbook

## SSH 登录

```bash
gcloud compute ssh --zone "asia-southeast1-a" "ce-lb" --project "cambodian-express"
```

当前验证使用远程用户 `lingang`。如果 GCloud 身份、实例 Metadata 或 OS Login 改变，应重新确认实际账号，不在仓库记录密钥内容。

关联服务器：

```bash
gcloud compute ssh wms-db --zone "asia-southeast1-a" --project "cambodian-express"
gcloud compute ssh wms-server --zone "asia-southeast1-a" --project "cambodian-express"
```

两台关联服务器当前无外部 IP，GCloud CLI 会通过 IAP tunnel 连接。

## 默认只读巡检

登录后优先检查：

```bash
uptime
free -h
df -hT
df -ih
systemctl is-system-running
systemctl list-units --type=service --state=running --no-pager
netstat -lnt
ps -eo pid,user,comm,%cpu,%mem,etime --sort=-%mem
```

需要核对短时 CPU 状态时：

```bash
top -b -n 1
vmstat 1 5
```

本机 HTTP 快速验证：

```bash
curl -sS -o /dev/null -w "status=%{http_code} total=%{time_total}s\n" --max-time 10 http://127.0.0.1/
```

## Nginx 与 SSL 只读检查

```bash
sudo nginx -t
sudo certbot certificates
sudo systemctl status certbot-renew.timer --no-pager
sudo crontab -l
```

核对实际 SNI 证书时，只输出证书公开字段，不读取私钥：

```bash
openssl s_client -connect 127.0.0.1:443 -servername cambodianexpress.com </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -checkhost cambodianexpress.com
```

证书续期命令可能发起外部验证并修改证书文件，不属于只读检查；未经授权不要执行 `certbot renew` 或 `--dry-run`。

## 官网证书过期时的恢复流程

`2026-09-17` 已验证：先区分 DNS/源站故障与证书过期。公网 `curl` 报证书过期而跳过校验后官网仍返回完整页面时，再核对实际 SNI 证书和 Certbot 日志；Cron 有触发记录不代表续期成功。本机 Nginx 位于 `/sbin/nginx`，旧 root Cron 缺少 `/sbin` 导致 Nginx 插件无法运行。

1. **只读定位：** 核对 DNS、`curl` 标准 HTTPS、实际 SNI 证书到期时间、`sudo nginx -t`、`sudo certbot certificates`、root crontab 和 `/var/log/letsencrypt/letsencrypt.log`。最终验收不能使用 `curl -k`。
2. **获得生产变更授权后：** 先备份 root crontab、Nginx 与目标证书的续期配置；确认空间、Nginx 配置测试和无其他 Certbot 进程。逐张续期在用 lineage，避免把废弃域名混入紧急恢复。`2026-09-17` 的备份位于服务器 `/root/ssl-recovery-20260917T1030Z/`。
3. **当前 Certbot 1.11 的已验证命令：** 将下例 `--cert-name` 依次替换为 `cambodianexpress.com-0001`、`www.cambodianexpress.com`、`cp.cambodianexpress.com`，每张完成后检查结果，不并行执行。

```bash
sudo env PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  /usr/bin/certbot renew --cert-name www.cambodianexpress.com \
  --non-interactive --no-random-sleep-on-renew
```

4. **防止复发：** root crontab 保留每日 `12:00 UTC` 的 `/usr/bin/certbot renew --quiet`，并显式设置 `PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`。在相同 PATH 的最小环境中对目标 lineage 做一次受控 `--dry-run`，再复核 Nginx 配置、公网证书和标准 HTTPS 响应。

注意：旧版 Certbot 的非交互续期会随机等待，当前版本支持 `--no-random-sleep-on-renew`。中断 SSH 不一定停止远端等待进程；重试前先核对 `pgrep -af certbot`。其他历史 lineage 仍可能使整批 `certbot renew` 报失败，必须逐项确认业务归属后处理，不能直接删除。

## 当前环境注意事项

- Ops Agent 异常时，先核对上传 403、实际 FD 上限和缓存；不能只提高 FD 后一次性处理旧缓存。已验证的风险、保留位置文件的隔离方式及专用资源限额见 [日志事故记录](INCIDENT_2026-09-30_LOGGING_PRESSURE.md)。
- CentOS 7 的 `systemctl show` 不支持 `--value`；用 `systemctl show <unit> -p MainPID | cut -d= -f2` 获取 PID。变更前始终重新核实 PID 和二进制路径。

- 系统没有 `ss` 命令，当前用 `netstat -lnt` 查看监听地址；进程归属需在授权范围内进一步核对。
- 当前 `lsblk` 版本不支持 `MOUNTPOINTS` 列，应使用 `MOUNTPOINT`。
- SSH 会出现 `LC_ALL=C.UTF-8` locale 警告，未影响本次命令执行。
- Nginx 与 PHP-FPM 进程存在；普通用户默认 `PATH` 中未找到可执行文件，使用 sudo 后可从系统路径执行 Nginx 检查。

## 变更边界

以下操作不是巡检动作，执行前必须获得明确授权并准备回滚与恢复验证：

- 重启或停止 Nginx、PHP-FPM、MySQL、GCS Fuse、journald 或 Ops Agent。
- 修改 GCP/主机防火墙、监听端口、数据库授权或服务配置。
- 清理日志、增加 Swap、升级系统或软件包。
- 读取或导出数据库、密钥、证书私钥和业务数据。
