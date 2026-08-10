# Site Inventory

## Nginx 配置目录

```text
/etc/nginx/conf.d/
```

## 来源摘要中的现有配置

| 配置文件 | 对应域名 | 站点类型 | 当前记录状态 |
|---|---|---|---|
| `www.ceccsl.com.conf` | `www.ceccsl.com` | 官网 | 配置已存在；源码目录已记录 |
| `m.ceccsl.com.conf` | `m.ceccsl.com` | 待补充 | 配置已存在；后端/目录未记录 |
| `m-uat.ceccsl.com.conf` | `m-uat.ceccsl.com` | UAT，待确认 | 配置已存在；后端/目录未记录 |
| `portal.ceccsl.com.conf` | `portal.ceccsl.com` | Portal，待确认 | 配置已存在；后端/目录未记录 |

所有 `ceccsl.com` 相关站点均应使用统一通配符双证书。

## 源码与目录

### 已记录

| 站点 | 目录 | 来源 |
|---|---|---|
| `www.ceccsl.com` | `/home/sens/apps/www.ceccsl.com` | `git@github.com:senseslg/ceccsl-com.git` |

### 规划中

| 站点 | 建议目录 | 建议 Nginx 配置 |
|---|---|---|
| `static.ceccsl.com` | `/home/sens/apps/static.ceccsl.com` | `/etc/nginx/conf.d/static.ceccsl.com.conf` |
| `download-app.ceccsl.com` | `/home/sens/apps/download-app.ceccsl.com` | `/etc/nginx/conf.d/download-app.ceccsl.com.conf` |

## DNS 状态

来源摘要前文表示根域 `@` 和 `www` 已解析到服务器公网 IP；后续工作列表又把 `@` 和 `www` 列为需要添加。两处存在重复或状态冲突，因此记录为：

| 记录 | 目标状态 | 当前文档结论 |
|---|---|---|
| `@` | 指向新服务器公网 IP | 来源倾向于已完成，但上线前必须复核 |
| `www` | 指向新服务器公网 IP | 来源倾向于已完成，但上线前必须复核 |
| `static` | 指向同一服务器 | 规划中，是否已添加需复核 |
| `download-app` | 指向同一服务器 | 规划中，是否已添加需复核 |

服务器公网 IP 未记录在来源摘要中，不在本文件中推测或补写。

## 待补充

- [ ] `m`、`m-uat`、`portal` 的实际目录或 upstream。
- [ ] 四个目标 DNS 记录的实时解析结果。
- [ ] `static` 与 `download-app` 是否已创建目录和 Nginx 配置。
- [ ] 各站点的负责人、资源来源和发布方式。
