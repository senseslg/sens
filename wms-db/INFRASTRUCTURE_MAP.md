# WMS DB Infrastructure Map

## 公网请求链路

```text
issue / code / yapi / jenkins / job .cambodianexpress.com
  → DNS: 34.117.18.41
  → GCP global forwarding rules: dev-lb
  → target HTTP(S) proxy / URL map / dev-backend
  → wms-db:80
  → Nginx 按 Host 转发
  → 本机 Docker 容器
```

| Host | Nginx 上游 | 容器 |
|---|---:|---|
| `issue.cambodianexpress.com` | `127.0.0.1:8080` | `jira` |
| `code.cambodianexpress.com` | `127.0.0.1:7990` | `bitbucket` |
| `yapi.cambodianexpress.com` | `127.0.0.1:40001` | `yapi-web` → `yapi-mongo` |
| `jenkins.cambodianexpress.com` | `127.0.0.1:8081` | `jenkins`（容器 8080） |
| `job.cambodianexpress.com` | `127.0.0.1:8087` | `xxl-job-admin` |

Bitbucket 的 Git SSH 另经共享入口的 TCP 9200 转发链路到本机容器端口 7999。正式克隆地址和密钥兼容要求由具体源码子项目维护。

## 平台边界

- `wms-db`：共享工具与数据平台，运行本文件所列容器和 Nginx。
- `wms-server`：CEWMS .NET 应用部署服务器；不是 Bitbucket/Jenkins 所在机。
- `otwms` 与 `tms` 生产实例：运行构建产物；源码事实来源和 Jenkins 构建入口位于 `wms-db`。

## Jira 本机 API 接入

```text
本机调用方 → Mac jira-service（127.0.0.1:8765）
  → HTTPS issue.cambodianexpress.com → dev-lb
  → wms-db:80 → Nginx → jira 容器:8080 → Jira REST API
```

Python 服务与 Jira 本体分开运行；本轮没有新增服务器部署、端口或数据库写入链路。认证与使用方式见 [Jira 接入说明](JIRA_REQUIREMENTS.md)。

旧版跨服务器总图保留在 [`otwms-ce-lb/INFRASTRUCTURE_MAP.md`](../otwms-ce-lb/INFRASTRUCTURE_MAP.md)；本目录作为 `wms-db` 当前主记录。
