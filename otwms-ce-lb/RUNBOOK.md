# OTWMS CE LB Runbook

## SSH 登录

```bash
gcloud compute ssh --zone "asia-southeast1-a" "ce-lb" --project "cambodian-express"
```

当前验证使用远程用户 `lingang`。如果 GCloud 身份、实例 Metadata 或 OS Login 改变，应重新确认实际账号，不在仓库记录密钥内容。

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

## 当前环境注意事项

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
