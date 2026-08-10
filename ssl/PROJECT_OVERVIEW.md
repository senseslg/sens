# ceccsl.com SSL & Deployment Overview

## 目标

- 为 `ceccsl.com` 及其子域名提供统一的 HTTPS 能力。
- 通过 ECDSA 与 RSA 双证书兼顾现代客户端和兼容性。
- 使用 `acme.sh` 和腾讯云 DNS API 自动申请、安装及续期通配符证书。
- 统一 Nginx 站点配置和服务器目录结构，降低新增子域名的部署成本。
- 通过 GitHub Deploy Key 实现网站源码免密码拉取。

## 当前架构

```text
GitHub
  ↓
/home/sens/apps/<site>
  ↓
Nginx /etc/nginx/conf.d/<site>.conf
  ↓
/etc/nginx/ssl/ceccsl.com/{ecc,rsa}
  ↓
ceccsl.com 及其子域名
```

## 证书范围

- 主域名：`ceccsl.com`
- 通配符：`*.ceccsl.com`
- 签发类型：ECDSA（ECC）与 RSA
- DNS 验证：腾讯云 DNS API，`dns_tencent`
- 安装目录：`/etc/nginx/ssl/ceccsl.com/`

详细说明见 [CERTIFICATE_MANAGEMENT.md](CERTIFICATE_MANAGEMENT.md)。

## 网站源码

- GitHub：`git@github.com:senseslg/ceccsl-com.git`
- 官网部署目录：`/home/sens/apps/www.ceccsl.com`
- 拉取方式：GitHub Deploy Key

Deploy Key 的私钥内容不得写入本仓库。

## 状态边界

来源摘要明确表示 HTTPS、自动续期、Nginx 双证书和基础部署框架已经完成，但没有提供：

- 服务器公网 IP。
- 精确完成时间。
- 每个域名的当前 DNS 查询结果。
- 每个站点的 HTTP/HTTPS 实际响应结果。
- `m`、`m-uat`、`portal` 对应的源码目录和上游服务。

因此，本子项目把配置摘要作为部署基线；涉及实时状态时必须重新查询服务器、DNS 和 HTTPS。

## 维护原则

- 默认先验证 DNS、目录和 Nginx 配置，再执行 reload。
- 证书续期测试、Nginx reload、DNS 修改和线上资源替换均属于外部状态变更，需要明确授权。
- 新增子域名优先复用现有通配符证书，不重复维护独立证书，除非有明确隔离需求。
- 不记录腾讯云 API Secret、Deploy Key 私钥或服务器登录凭证。
