# CE / WMS Infrastructure Map

## 快速结论

`ce-lb`、GCP `dev-lb`、`wms-db` 和 `wms-server` 不是同一入口：官网与部分历史域名进入 `ce-lb`；`job.cambodianexpress.com` 进入 GCP Global HTTPS Load Balancer 后落到 `wms-db`；CEWMS .NET 管理后台部署在 `wms-server`。Bitbucket 源码平台和 Jenkins 构建平台也运行在 `wms-db`。

## 快速定位

| 目标 | 首个检查位置 | 最终处理位置 | 记录 |
|---|---|---|---|
| `cambodianexpress.com` / `www` | DNS → `ce-lb` Nginx | `ce-lb` 本机 WordPress/PHP-FPM | [SERVICE_INVENTORY.md](SERVICE_INVENTORY.md) |
| `job.cambodianexpress.com` | GCP `dev-lb` | `wms-db` Nginx → `xxl-job-admin` 容器 | [WMS_DB_SERVER.md](WMS_DB_SERVER.md) |
| `code.cambodianexpress.com` | `wms-db` Nginx | `wms-db` Bitbucket 容器 | [WMS_DB_SERVER.md](WMS_DB_SERVER.md) |
| Jenkins 构建 | `wms-db` | Jenkins 容器；存在 `otwms`、`TMS`、`APP` 等任务 | [WMS_DB_SERVER.md](WMS_DB_SERVER.md) |
| CEWMS .NET 管理后台 | `wms-server:80` | `cewms.service` → `CE.WMS.Web.dll` | [WMS_SERVER.md](WMS_SERVER.md) |

## `job.cambodianexpress.com` 请求链路

```text
job.cambodianexpress.com
  → GCP global forwarding rule: dev-lb (HTTPS 443)
  → target HTTPS proxy: dev-lb-target-proxy
  → URL map: dev-lb（未配置 job 专属 Host Rule，使用默认后端）
  → backend service: dev-backend
  → zonal NEG: dev-neg
  → wms-db:80（2026-08-17 检查为 HEALTHY）
  → Nginx Host: job.cambodianexpress.com
  → 127.0.0.1:8087
  → xxl-job-admin container:8080
```

TLS 在 GCP HTTPS Load Balancer 终止；托管证书 `xxl-job` 状态为 `ACTIVE`，覆盖 `job.cambodianexpress.com`，检查时有效至 `2026-10-18`。

## 源码、构建与部署边界

- **源码平台：** Bitbucket 运行在 `wms-db`，数据挂载到 `/home/daniel/containers/bitbucket/bitbucket`；具体仓库与 CEWMS/XXL-JOB 的对应关系尚未登录 Bitbucket 确认。
- **构建平台：** Jenkins 运行在 `wms-db`，数据挂载到 `/home/daniel/containers/jenkins/jenkins`。
- **XXL-JOB：** 使用官方 `xuxueli/xxl-job-admin:2.3.1` 镜像；宿主机未挂载源码目录，仅将 `/tmp` 挂载为应用日志目录。
- **CEWMS 部署：** `wms-server` 只保存编译后的 .NET 发布产物，未发现 Git、解决方案、项目或 C# 源文件；它是部署服务器，不是源码工作区。

## SSH 入口

```bash
gcloud compute ssh ce-lb --zone asia-southeast1-a --project cambodian-express
gcloud compute ssh wms-db --zone asia-southeast1-a --project cambodian-express
gcloud compute ssh wms-server --zone asia-southeast1-a --project cambodian-express
```

`wms-db` 与 `wms-server` 没有外部 IP，GCloud CLI 会使用 IAP tunnel。所有服务器默认先做只读检查。

最近验证：`2026-08-17`。
