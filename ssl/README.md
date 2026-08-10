# ssl

`ceccsl.com` 新服务器的 HTTPS、Nginx、DNS 与静态站点部署记录子项目。

## 阅读顺序

1. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)：部署范围、当前架构和已知边界。
2. [CERTIFICATE_MANAGEMENT.md](CERTIFICATE_MANAGEMENT.md)：通配符证书、双证书和自动续期。
3. [SITE_INVENTORY.md](SITE_INVENTORY.md)：域名、DNS、Nginx 配置和部署目录状态。
4. [RUNBOOK.md](RUNBOOK.md)：新增站点、验证配置和发布检查流程。

## 当前结论

- `ceccsl.com` 与 `*.ceccsl.com` 通配符证书已申请。
- ECDSA 与 RSA 双证书已安装并接入 Nginx。
- `acme.sh` 自动续期和 Nginx reload 流程已建立。
- 官网源码通过 GitHub Deploy Key 拉取到新服务器。
- `static.ceccsl.com` 与 `download-app.ceccsl.com` 属于待落地的新站点规划。

> 来源摘要未提供服务器 IP、部署完成日期和逐站点在线验证结果；这些内容不得在没有实际检查的情况下补写为已确认。
