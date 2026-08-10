# Nginx Domain and SSL Runbook

本文记录 2026-08-01 在 D-Mall 服务器上为 CCSL 管理后台原型增加
`ccsl-prototype.ceccsl.com` HTTPS 入口的实际操作与可复用经验。本文不保存
私钥、密码、Token、数据库凭据或环境变量内容。

## 当前 Nginx 与证书布局

- 可用站点：`/etc/nginx/sites-available/`
- 已启用站点：`/etc/nginx/sites-enabled/`
- CCSL 原型上游：`127.0.0.1:3002`
- CCSL 域名：`ccsl-prototype.ceccsl.com`
- ECC 证书：`/home/sens/ssl/ceccsl.com/ecc/fullchain.pem`
- ECC 私钥：`/home/sens/ssl/ceccsl.com/ecc/privkey.pem`
- RSA 证书：`/home/sens/ssl/ceccsl.com/rsa/fullchain.pem`
- RSA 私钥：`/home/sens/ssl/ceccsl.com/rsa/privkey.pem`

证书的 SAN 已核验为 `*.ceccsl.com` 和 `ceccsl.com`，因此覆盖
`ccsl-prototype.ceccsl.com`。核验时证书有效期至 2026-10-17；该日期会变化，
每次发布和续期后都应重新读取证书，不要依赖本文的历史值。

## 新增域名前的检查

1. 确认 DNS A 记录已经指向当前服务器：

   ```bash
   getent ahostsv4 ccsl-prototype.ceccsl.com
   ```

2. 确认上游只监听回环地址且端口未与现有应用冲突：

   ```bash
   ss -ltn
   curl -fsS http://127.0.0.1:3002/api/health
   ```

3. 只读取证书元数据，不输出私钥内容：

   ```bash
   openssl x509 \
     -in /home/sens/ssl/ceccsl.com/ecc/fullchain.pem \
     -noout -subject -issuer -dates -ext subjectAltName
   ```

4. 检查目标域名没有被其他站点重复声明：

   ```bash
   grep -Rns 'server_name ccsl-prototype.ceccsl.com' /etc/nginx
   ```

## CCSL 原型的安装方式

项目仓库已经保存 Nginx 模板和带回滚的安装脚本：

```text
/home/sens/ccsl-prototype/deploy/nginx/ccsl-prototype.ceccsl.com.conf
/home/sens/ccsl-prototype/scripts/install-nginx-site.sh
```

交互登录服务器后执行：

```bash
sudo /home/sens/ccsl-prototype/scripts/install-nginx-site.sh
```

脚本会依次完成：

1. 检查本机上游健康接口和四个证书文件；
2. 备份同名旧站点配置；
3. 安装到 `sites-available` 并链接到 `sites-enabled`；
4. 执行 `nginx -t`，只有完整配置通过才 reload；
5. 使用 SNI 和本机 `127.0.0.1:443` 验证 HTTPS 反向代理；
6. 任一步失败时恢复旧配置并再次 reload。

`sens` 当前可免密运行 `/usr/sbin/nginx` 的检查命令和
`systemctl reload nginx`，但不能免密向 `/etc/nginx` 写文件，因此首次安装或
替换站点配置仍需要一次交互式 sudo 密码。不要在聊天、脚本参数或日志中传递
sudo 密码。

## 推荐的 Nginx 站点结构

站点应包含两个 `server`：

- 80 端口只执行 `301` 跳转到同域名 HTTPS；
- 443 端口声明精确 `server_name`、ECC/RSA 证书，并代理到回环上游。

反向代理至少保留 `Host`、`X-Real-IP`、`X-Forwarded-For` 和
`X-Forwarded-Proto`。WebSocket/Next.js 场景同时保留 HTTP/1.1、`Upgrade` 和
`Connection` 请求头。应用端口不得直接绑定 `0.0.0.0` 暴露公网。

## 发布后验收

先检查服务器完整配置：

```bash
sudo /usr/sbin/nginx -t
readlink -f /etc/nginx/sites-enabled/ccsl-prototype.ceccsl.com
```

绕过 DNS 和代理，从服务器本机验证目标 SNI：

```bash
curl -fsS --noproxy '*' \
  --resolve ccsl-prototype.ceccsl.com:443:127.0.0.1 \
  https://ccsl-prototype.ceccsl.com/api/health
```

最后从服务器外部验证：

```bash
curl -sSI http://ccsl-prototype.ceccsl.com/
curl -fsS https://ccsl-prototype.ceccsl.com/api/health
curl -sSI https://ccsl-prototype.ceccsl.com/admin/login
openssl s_client \
  -connect ccsl-prototype.ceccsl.com:443 \
  -servername ccsl-prototype.ceccsl.com </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
```

验收标准：HTTP 返回 301 且 `Location` 指向 HTTPS；健康接口返回 `ok=true`；
登录页返回 200；证书 SAN 覆盖目标域名。

## 本次遇到的错误证书问题

首次安装后，立即发起 HTTPS 检查时曾短暂读到默认站点的
`*.mango-kh.com` 证书。原因不是 CCSL 证书文件错误，而是
`systemctl reload nginx` 返回时旧 worker 仍可能短暂处理连接。若把第一次请求
直接视为失败，会误判配置并触发回滚。

修复方式是在 reload 后使用本机 SNI 验证并在约 10 秒窗口内重试，等待新 worker
完成接管。排查类似问题时按以下顺序确认：

1. `sites-available` 文件真实存在，不能只看 `readlink -f` 的输出；
2. `sites-enabled` 是指向该文件的有效符号链接；
3. `sudo nginx -T` 中能看到目标 `server_name` 和证书路径；
4. `sudo nginx -t` 通过且 systemd reload 成功；
5. 使用 `openssl s_client -servername ...` 检查实际 SNI 证书；
6. reload 后允许短暂重试，再判断是否需要回滚。

如果目标站点配置不存在，Nginx 会由默认 443 站点响应；此时看到其他业务域名的
证书是“目标虚拟主机未生效”的信号，不应通过关闭证书校验来掩盖问题。

## 日常更新与证书维护

应用代码日常更新使用：

```bash
/home/sens/deploy-ccsl-prototype.sh
```

该脚本执行 GitHub 快进拉取、锁文件安装、lint/build、PM2 重启和本机健康检查；
普通代码更新不需要重复安装 Nginx 站点。

证书续期后必须执行 `sudo nginx -t` 和 `sudo systemctl reload nginx`，并再次检查
证书有效期与 SAN。修改域名、证书路径、上游端口或安全头时，应先更新仓库模板，
再运行带回滚安装脚本，避免服务器配置与 GitHub 记录漂移。
