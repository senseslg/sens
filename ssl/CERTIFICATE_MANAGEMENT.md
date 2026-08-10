# Certificate Management

## 已建立的证书方案

使用 `acme.sh` 通过腾讯云 DNS API 插件 `dns_tencent` 完成 DNS 验证，证书覆盖：

- `ceccsl.com`
- `*.ceccsl.com`

已成功申请两套证书：

- ECDSA / ECC
- RSA

## 安装结构

```text
/etc/nginx/ssl/ceccsl.com/
├── ecc/
└── rsa/
```

具体证书文件名未在来源摘要中给出。修改 Nginx 前，应以服务器上的真实目录和现有配置为准，不推测文件名。

## Nginx 使用方式

- Nginx 已配置为同时加载 ECDSA 和 RSA 证书。
- 所有 `ceccsl.com` 相关站点复用这一套通配符证书。
- 新增子域名时，应复用相同证书目录，除非证书范围或安全隔离要求发生变化。

## 自动续期

来源摘要确认以下流程已经完成：

1. `acme.sh --cron` 执行续期检查。
2. 新证书自动覆盖安装目录中的证书文件。
3. 安装/续期完成后自动执行 `systemctl reload nginx`。

## 续期检查

检查时应确认：

- [ ] `acme.sh` 中同时存在 ECC 与 RSA 证书记录。
- [ ] 主域名和通配符域名均包含在证书范围内。
- [ ] 安装目标仍为 `/etc/nginx/ssl/ceccsl.com/`。
- [ ] reload hook 指向 Nginx，且最近一次执行成功。
- [ ] Nginx 当前配置引用的文件与实际更新文件一致。
- [ ] 外部访问返回的新证书有效期符合预期。

## 安全注意事项

- 腾讯云 DNS API 凭证不得写入项目文档、Git 历史或命令输出记录。
- 不手动覆盖证书文件，除非已确认 `acme.sh` 的安装路径和续期配置。
- 不在未通过 `nginx -t` 的情况下 reload Nginx。
- 续期成功不等于线上已生效；必须检查 Nginx reload 结果和外部 TLS 响应。
