# static OSS + CDN、DNS 与证书

## 当前状态（2026-10-19）

**续期后同步阿里云证书库及 CDN 的自动化已接通，并以当前正式证书完成端到端 API/TLS 验收。** ce-lb 自动 DNS 续期已通过 staging；首次到期后的真实签发与自动同步仍待观察。static 流量使用阿里云 OSS + CDN，不经过 ce-lb。

用户顺序：先验证 ce-lb 自动续期，再处理 CDN 自动更新；两阶段配置和 staging/API 验收均已完成，首次真实续期待观察。DNS API 自动完成每次新挑战，不依赖旧 TXT。正式续期检查成功后，同步脚本校验证书 SAN、私钥匹配和有效期，按 SHA-2/序列号/到期日匹配或上传 CAS 证书，再更新 CDN 绑定并检查公网 SNI 证书。

## 凭据与 Agent 入口

- 已按用户指定创建私有目录 `/Users/lingang/internationl_ali_cloud/`；[凭据索引](/Users/lingang/internationl_ali_cloud/CREDENTIALS.md) 仅保存用途、权限、位置与缺失状态，不明文保存秘密。
- [阿里云 Agent Skill](/Users/lingang/internationl_ali_cloud/SKILL.md) 与凭据预检已建立；阿里云实际凭据仍缺失。本机预检不联网，不代替云端授权验证。
- [Cloudflare 独立 Skill](/Users/lingang/cloudflare_cambodianexpress_com/SKILL.md) 的本机 Token 位于同目录 `secrets/cloudflare.ini`（0600），已由用户填入并确认 API active、目标 zone 可读及挑战 TXT 可创建/清理；阿里云资料只索引它，不另存副本。
- 创建摘要范围为 `cambodianexpress.com / DNS : Edit`，不是单条记录权限；完整策略/控制台有效期未另行审计，不宣称永久有效。个人空账号不管理此 zone，不应混用。
- 已通过 SSH 部署至 ce-lb root 0600 凭据文件；本机预检10项、DNS hook16项离线测试通过，后者也在服务器 Python3.6 上通过。远端位置、调用及回滚见 [续期 Runbook](/Users/lingang/cloudflare_cambodianexpress_com/RENEWAL_RUNBOOK.md)。

## 平台职责与当前链路

| 平台 | 职责 | 确认依据 |
|---|---|---|
| GoDaddy | 域名注册管理、续费及权威 NS 委派 | 用户说明；注册人拥有域名，GoDaddy 是注册商，不是网站服务器 |
| Cloudflare | 权威 DNS，维护 static 的 CNAME 和 ACME TXT | 用户说明；公网 NS 为 `jeff.ns.cloudflare.com`、`kami.ns.cloudflare.com` |
| 阿里云 CDN | 对外 HTTPS、缓存和回源 | 用户说明；新 CNAME、CDN 响应头及公网证书已验证 |
| 阿里云 OSS | 保存静态文件，作为 CDN 源站 | 用户说明；生产 Bucket 从应用配置确认，CDN 实际回源 Host/鉴权未读取 |
| ce-lb | 证书申请、保存及自动 DNS 续期执行位置 | 已签发、staging 验证及独立调度；非 static 流量入口 |

当前公开 DNS：`static.cambodianexpress.com` → `static.cambodianexpress.com.queniuaa.com` → 阿里云 CDN；CDN 缓存未命中时按其配置回源 OSS。DNS 委派/解析与 HTTP 流量转发是两回事，GoDaddy 不转发页面流量。

## 2026-10-19 公网验收

- 用户说明已切换上述 CNAME 并上传 SSL；`1.1.1.1`、`8.8.8.8` 均返回新 CDN CNAME。
- 标准 `curl` HTTPS 未跳过证书校验，TLS 成功；公网证书序列号与本次签发一致，SHA-256 指纹为 `64:9F:8B:97:90:63:B3:CB:B5:FB:FD:2C:77:6F:4A:EA:09:48:43:48:51:F2:96:CB:97:E3:27:67:EA:B1:35:33`。
- 根路径返回 HTTP 403，响应为 `Tengine`，含 CDN `Via`、`X-Cache`、`X-Swift-Error: orig response 4XX error` 和 OSS 请求标识。这证明收到 CDN/OSS HTTP 错误响应，不是 TLS 失败；根路径结果不能代表具体文件可用。
- 尚未验证：实际文件下载/图片展示、缓存命中、CDN 控制台的源站地址/Host、回源协议与鉴权、证书管理库中的证书 ID。不得因证书生效宣布全链路业务正常，也不应直接开放 Bucket 或放宽 ACL。

## 本次证书

- 域名：`static.cambodianexpress.com`，独立 RSA 2048 证书，不是通配符。
- 签发机构：Let's Encrypt / YR2；有效至 **2027-01-17 08:22:33 UTC（柬埔寨时间 15:22:33）**。
- 序列号：`050A2ED5C33D36DA6ED15ED41DAA6C752CFE`。
- DNS TXT 验证由用户在 Cloudflare 添加；已从两个公共解析器确认。旧 TXT 在本次验证完成后可清理，不能作为下一次验证凭据。
- 本地证书链、主机名及私钥有效性校验通过，远端证书与私钥公钥哈希一致；没有输出私钥内容。

## 自动续期阶段验收（2026-10-19）

- 保留 `authenticator = manual`，增加 root 管理的 Cloudflare `manual_auth_hook` / `manual_cleanup_hook`，未升级旧版官网 Certbot。
- 首轮 staging 创建/清理 TXT 成功，但 CA 因 CAA SERVFAIL 拒绝；公共与权威查询均 NOERROR 后一次重试完整通过。未改 CAA/CNAME，不能据一次恢复认定永久消除外部解析异常。
- 第二轮完整 dry-run 成功，正式生产检查因未到期正常跳过；正式证书序列号/指纹未变，测试证书未写入正式文件或 CDN。
- `/etc/cron.d/static-ssl-renewal` 独立任务，UTC 02:25/14:25（柬埔寨09:25/21:25），调用 `/usr/local/sbin/renew-static-ssl --apply`，带互斥锁。crond active，原官网 root crontab 与备份逐字比较未变。
- 原有1条TXT的记录摘要与测试前一致，CDN CNAME及DNS-only状态未变；公网TLS校验通过，根路径仍403，业务文件另验收。远端临时传输副本已清理，root正式文件与备份保留。
- 日志：`/var/log/letsencrypt-oss-static/`、syslog tag `static-ssl-renew`。外部告警与首次真实计划续期仍待验证；日志中的 success 可能只代表“未到期检查完成”，不能当成已签发新证书。

## 2026-10-19 阿里云 CDN 自动同步验收

- 阿里云凭据由用户放入本机 `/Users/lingang/internationl_ali_cloud/secrets/aliyun.json`；发现文件初始权限为0644，已收紧为0600。RAM身份 API 返回 `power-application-user`（AccountId `5462797789441439`），为RAM用户；其完整附加策略未审计，当前只验证了本流程调用的 API。
- 只读查询确认原 CDN 证书 ID `611857`，CAS地域 `ap-southeast-1`，HTTPS `on`，有效至 `2027-01-17`。CAS中已有证书名 `static_cambodianexpress_com`。阿里云 CAS `Sha2` 与证书 DER 指纹字段语义不同；实现按公钥 SHA-256、序列号及到期日识别证书，并用证书 DER SHA-256 验证公网 TLS。
- 用当前完全相同的正式证书/私钥验证 CAS 上传 API，新增证书 ID `611941`，名称 `static_cambodianexpress_com_d03f079e7440`；随后把 `static.cambodianexpress.com` CDN绑定切到 `611941`（新加坡 `ap-southeast-1`）。旧 ID `611857` 保留，可回滚。上传/绑定均为正式证书，没有改 DNS、OSS 或其它域名。
- CDN API读回 `CertId=611941`、HTTPS `on`；公网 SNI 提供证书 DER SHA-256 `649F8B979063B3CBB5FBFD2C776F4AEA0948434851F296CB97E32767EAB13533`，与 ce-lb正式证书一致。
- ce-lb已安装 `/usr/local/libexec/static-ssl/sync_static_cdn_certificate.py`（root0700），阿里云凭据 `/etc/letsencrypt-oss-static/secrets/aliyun.json`（root0600）。`/usr/local/sbin/renew-static-ssl --apply` 在Certbot报告证书未到期后，继续调用CDN同步并正确识别 `611941` 已为当前证书；完整入口返回成功。独立Cron原定时不变：每日02:25/14:25 UTC。
- 最小权限动作：`yundun-cert:UploadUserCertificate`、`yundun-cert:ListUserCertificateOrder`（CAS接口要求`Resource="*"`）；`cdn:DescribeDomainCertificateInfo`、`cdn:SetCdnDomainSSLCertificate` 限定到 `acs:cdn:*:5462797789441439:domain/static.cambodianexpress.com`。不需要OSS权限或管理员策略。调用已成功，但现有RAM用户的其它授权尚未读取或审计。
- 本机脚本：`/Users/lingang/sens/otwms-ce-lb/scripts/sync_static_cdn_certificate.py`。默认无写操作，必须指定`--dry-run`或`--apply`；生产包装器仅在正式`--apply`之后运行同步，staging dry-run不会向CAS上传或覆盖CDN。
- 仍待观察首次真实续期后的CAS上传、CDN绑定与公网更新；当前验证覆盖了这些API写权限和同证书上传/切换，但不能代替新签发证书的到期事件验收。未检查 `power-application-user` 的完整附加RAM策略；建议确认其权限符合最小范围。

## 已确认的 OSS 配置来源

- 用户指定 `/Users/lingang/work/new_ccsl`；查阅 Markdown（含忽略目录中的项目文档）未找到 Cloudflare DNS API 配置或证书管理凭据位置。
- 跟随后端资料核对 `ccsl-backend/src/main/resources/application-prod.yml`：生产 Bucket 为 `cambodianexpress-ccsl`，Endpoint 为 `oss-cn-hongkong.aliyuncs.com`，地域 `cn-hongkong`；测试环境使用 `uat-ccsl`，不可混用。
- AccessKey 字段只是 `${ALIYUN_OSS_ACCESS_KEY_ID}` 和 `${ALIYUN_OSS_ACCESS_KEY_SECRET}` 占位符，无默认值；当前执行环境也未注入。因此凭据预检在发送请求前停止，未调用阿里云 API，未验证 Bucket 绑定或 RAM 权限。
- 下一步只缺阿里云证书/CDN实际凭据及权限验证；Cloudflare Token 已就绪。应用 OSS 凭据不等同于 CDN 管理凭据，不修改应用凭据或擅自扩权。

## 流量与证书保存位置

- 同日较早的 CNAME `cambodianexpress-ccsl.cn-hongkong.thepacificmax.com` 及证书名称不匹配属于变更前状态，已被当前 CDN CNAME 和正常证书替代。
- CNAME 修改和阿里云证书上传由用户完成；助手完成 ce-lb 签发与专用自动DNS续期部署，未修改 Nginx、官网证书或官网 Cron。
- 正式证书：ce-lb `/etc/letsencrypt-oss-static/live/static.cambodianexpress.com/`；续期配置位于 `/etc/letsencrypt-oss-static/renewal/`。
- 独立工作目录 `/var/lib/letsencrypt-oss-static/`，日志 `/var/log/letsencrypt-oss-static/`；由新建独立Cron续期，不依赖官网 `/etc/letsencrypt/` 的任务。
- 本机上传副本 `secrets/static-oss-20261019/` 是首次签发快照，Git忽略、目录0700/文件0600；不会随服务器后续续期自动更新。

## 阿里云上传字段

| 字段 | 本机副本中的文件/值 |
|---|---|
| 标准 | 国际标准 |
| 名称 | `static.cambodianexpress.com_20261019` |
| 证书文件 | `cert.pem` |
| 私钥 | `static.cambodianexpress.com.key` |
| 证书链 | `chain.pem` |

另有 `fullchain.pem` 供要求合并证书链的接口使用；不要将私钥发到聊天、日志或版本库。证书管理服务负责存储证书；当前架构还必须将证书部署到 CDN 的 `static.cambodianexpress.com` HTTPS 配置，不能只检查上传成功。若回源使用 OSS 官方域名及 HTTPS，可使用 OSS 官方证书；只有仍使用自定义 OSS HTTPS 入口时才另评估该入口证书。

## 自动化待办与验收边界

1. **已完成DNS阶段：** stdlib hook、staging与独立调度已验证；仍待观察首次真实计划续期及失败告警。
2. **已完成CDN集成：** CAS上传、static域名CDN绑定写入、API读回、公网证书匹配和续期入口集成均通过当前正式证书验收；正式到期后的自动事件待观察。
3. **RAM权限复核：** 身份为 `power-application-user`；API上传、查询和static CDN绑定均已调用成功，但未审计此用户所有附加策略。建议用户或RAM管理员确认最小权限，不能从本次调用成功推断整体授权范围。
4. **业务链路待验收：** 实际OSS文件访问/403与证书部署独立，仍未验证具体文件下载、缓存命中、源站Host、回源协议或鉴权。不应开放Bucket或放宽ACL作为证书修复。

DNS续期和CDN部署代码/步骤已分别沉淀到Cloudflare入口及本子项目脚本；ce-lb现有续期入口已接入同步，待首次真实续期验证。

## 官方依据

- [Certbot manual 与自动续期限制](https://eff-certbot.readthedocs.io/en/stable/using.html#manual)
- [Cloudflare DNS 验证插件与受限 Token](https://certbot-dns-cloudflare.readthedocs.io/en/stable/)
- [阿里云 UploadUserCertificate](https://help.aliyun.com/zh/ssl-certificate/developer-reference/api-cas-2020-04-07-uploadusercertificate)
- [阿里云 CAS 证书列表及 SHA-2/序列号字段](https://www.alibabacloud.com/help/en/ssl-certificate/developer-reference/api-cas-2020-04-07-listusercertificateorder)
- [阿里云 OpenAPI V3 请求签名](https://www.alibabacloud.com/help/en/sdk/product-overview/v3-request-structure-and-signature)
- [OSS + CDN 的 HTTPS 配置位置](https://www.alibabacloud.com/help/en/oss/user-guide/access-oss-by-https-protocol)
- [CDN SetCdnDomainSSLCertificate 与域名级授权](https://www.alibabacloud.com/help/en/cdn/developer-reference/api-cdn-2018-05-10-setcdndomainsslcertificate)
