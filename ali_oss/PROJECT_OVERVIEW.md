# ali_oss 总览

## 是什么

管理阿里云（国际站，主账号 `cambodianex**`）OSS 的子项目：Bucket 清单、权限、CDN/域名、用量、安全加固，以及供 agent/其他业务调用的 API 脚本。

## 当前版本

- `v0.3.0`（SemVer：MAJOR 结构不兼容 · MINOR 新能力/脚本 · PATCH 修正与文档）

## 当前结论（控制台只读，2026-11-27）

- 7 个 Bucket，全部 `cn-hongkong`、标准存储、同城冗余（ZRS）；均未开版本控制、传输加速。
- **5 个公共读**；健康检测 284/500，权限控制 0 分。加固方案见 [OSS 安全加固方案](reference/security-hardening-plan.md)。
- `uat-mallgogo` 虽为 UAT 命名，实为商城业务（[mallgogo-server](../mallgogo-server/README.md)）在用，本月外网流出 30.43 GB，约占全账号 94%，按生产对待。
- API 脚本 [scripts/oss.py](scripts/oss.py) 已用专用只读账号 `ali-oss-ops` 真实验证（2026-11-27：buckets/info/stat/config/ls 均成功），见 [RUNBOOK](RUNBOOK.md)。

## Bucket 清单

| Bucket | 读写权限 | 存储 | 本月流出 | 本月读请求 | 自定义域名 | 控制台创建时间 | 判断 |
|---|---|---|---|---|---|---|---|
| `cambodianexpress-ccsl` | 公共读 | 52.06 GB | 2.04 GB | 98,668 | `static.cambodianexpress.com`（CDN） | 2026-07-25 | 生产（CCSL 后端配置确认） |
| `ccsl-mallgogo` | 公共读 | 144.97 MB | 320 KB | 17,145 | `static.cel-mall.com`（CDN） | 2026-03-19 | 推断生产（商城） |
| `ceccsl` | 公共读 | 52.55 MB | 1.33 MB | 1,283 | — | 2026-07-15 | new_ccsl 业务（用户确认，[new-ccsl-server](../new-ccsl-server/PROJECT_OVERVIEW.md)） |
| `uat-mallgogo` | 公共读 | 834.16 MB | **30.43 GB** | 44,842 | — | 2026-07-21 | 商城业务在用（用户确认，[mallgogo-server](../mallgogo-server/README.md)） |
| `uat-ccsl` | 公共读 | 114.44 MB | 6.07 MB | 1,040 | — | 2026-07-24 | UAT |
| `ccsl-courier-uat` | 私有 | 12.2 KB | 0 | 149 | — | 2026-11-26 | UAT（新建） |
| `daniel-cel-shop` | 私有 | 0 | 0 | 470 | — | 2026-03-30 | D-Mall 原型/测试（用户确认，[d-mall-server](../sens-server/d-mall-server/README.md)） |

账号合计：存储 53.18 GB；本月流出 32.48 GB（上月 62.73 GB）；本月读请求 123,384（上月 168,153）。控制台统计延迟 1–3 小时，仅供参考，非计费数据。

## 访问方式

- 外网 Endpoint `oss-cn-hongkong.aliyuncs.com`，Bucket 域名 `<bucket>.oss-cn-hongkong.aliyuncs.com`；内网 `oss-cn-hongkong-internal.aliyuncs.com`（仅阿里云 ECS）。
- TLS 版本未限制；无报警规则；无资源包。
- 控制台概览称 3 个 Bucket 配置了域名，仅找到 2 个；第 3 个可能与 `static.ceccsl.com` CDN（见 [d-mall-server CDN 记录](../sens-server/d-mall-server/CDN_TELEGRAM_RUNBOOK.md)）有关，待 API 核实。
- `static.cambodianexpress.com`：Cloudflare DNS → 阿里云 CDN → OSS，证书链路见 [STATIC_OSS_SSL](../otwms-ce-lb/STATIC_OSS_SSL.md)。

## 凭据

- 已有 RAM 用户 `power-application-user` 只用于证书/CDN，**不用于 OSS**（凭据用途约定；2026-11-27 agent 拟借用做只读验证，被本机授权检查拒绝，未发出请求）。
- OSS 专用 RAM 用户 `ali-oss-ops`（2026-11-27 创建，仅 OpenAPI、无控制台登录，权限 `AliyunOSSReadOnlyAccess`）；AccessKey 在 `ali_oss/.local/credentials.json`（0600，gitignore），用户另有备份。需要写权限时再按桶追加最小策略。
- 账号内其他 RAM 用户 8 个（含 `oss-bucket-put-object-mallgogo`、`ccsl-cdn-cert-sync`、`power-application-user`），均非本项目使用。

## 不在范围

- static 证书续期实现（归 `otwms-ce-lb`）；应用代码与业务文件内容。
