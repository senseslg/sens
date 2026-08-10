# ceccsl.com Deployment Runbook

## 操作范围

用于新增或更新 `ceccsl.com` 相关静态站点。默认复用：

- 部署根目录：`/home/sens/apps/`
- Nginx 配置目录：`/etc/nginx/conf.d/`
- SSL 目录：`/etc/nginx/ssl/ceccsl.com/`
- 通配符范围：`ceccsl.com` 与 `*.ceccsl.com`

## 新增子域名前的确认

- [ ] 确认完整域名和用途。
- [ ] 确认 DNS 应指向的服务器公网 IP。
- [ ] 确认站点目录、资源来源和发布负责人。
- [ ] 确认使用静态目录还是反向代理 upstream。
- [ ] 确认现有通配符证书覆盖该域名。
- [ ] 确认是否存在同名 Nginx 配置。

## 标准流程

1. 在腾讯云 DNS 添加或确认子域名记录。
2. 在 `/home/sens/apps/<domain>` 准备站点目录和资源。
3. 在 `/etc/nginx/conf.d/<domain>.conf` 创建 Server Block。
4. 引用统一的 ECC 与 RSA 证书。
5. 执行配置检查：

```bash
nginx -t
```

6. 只有检查通过且已获准时，reload Nginx：

```bash
systemctl reload nginx
```

7. 验证 DNS、HTTP 跳转、HTTPS、证书域名和站点内容。
8. 记录实际结果和任何偏离标准结构的配置。

## 官网源码更新

- 仓库：`git@github.com:senseslg/ceccsl-com.git`
- 目录：`/home/sens/apps/www.ceccsl.com`
- 认证：GitHub Deploy Key

更新前应先检查：

```bash
git status --short --branch
git remote -v
git branch --show-current
```

如果服务器工作区存在本地修改，不应直接覆盖或 pull；先确认修改来源和保留方式。

## 发布后验证

- [ ] DNS 返回预期服务器地址。
- [ ] HTTP 按预期跳转 HTTPS。
- [ ] HTTPS 握手成功。
- [ ] 证书包含目标域名且未过期。
- [ ] ECDSA/RSA 配置没有导致 Nginx 错误。
- [ ] 页面或下载资源返回正确内容。
- [ ] Nginx error log 没有新增相关错误。
- [ ] 其他共享证书的站点仍可正常访问。

## 当前待执行事项

根据来源摘要，需要复核或完成：

1. 腾讯云 DNS 中的 `@`、`www`、`static`、`download-app`。
2. `static.ceccsl.com` 和 `download-app.ceccsl.com` 的站点目录。
3. 对应 Nginx Server Block。
4. 上传资源并完成外部访问验证。

其中 `@` 与 `www` 在摘要其他位置被写为已解析，因此应先查询实际 DNS，不重复盲目添加。
