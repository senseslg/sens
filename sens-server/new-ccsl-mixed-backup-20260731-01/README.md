# sens-server/new-ccsl

本目录当前包含两套不同服务器的工具。执行前必须根据目标选择正确入口，不能把
两个公网 IP、项目目录或部署命令混用。

## 1. CCSL 管理后台服务器（本次新增）

- SSH：`sens@8.212.48.176`
- 主机名：`new-ccsl`
- 生产：`ccsl-prod.jar` / `8080`
- UAT：`ccsl-uat.jar` / `8081`
- 详细资料：[SERVER_INFO.md](SERVER_INFO.md)

只读工具统一位于 `bin/`：

```bash
# 登录 CCSL 服务器
./bin/connect.sh

# SSH 身份与连通性
./bin/check-ssh.sh

# 系统、磁盘、服务、端口、脱敏 Java 进程
./bin/server-status.sh

# 生产和 UAT 技术健康检查
./bin/health-check.sh prod
./bin/health-check.sh uat
./bin/health-check.sh all
```

从其他项目直接调用：

```bash
/Users/lingang/sens/sens-server/new-ccsl/bin/server-status.sh
/Users/lingang/sens/sens-server/new-ccsl/bin/health-check.sh uat
```

标准 SSH：

```bash
ssh -F /Users/lingang/sens/sens-server/new-ccsl/ssh_config ccsl-new
```

## 2. CE SSR App 服务器（保留的并发资料）

目录根部的 `connect.sh`、`status.sh`、`health-check.sh`、`logs.sh` 和
`deploy.sh` 属于另一台 `ce-ssr-app` 服务器，不属于 CCSL Java 后端。
原始说明已保存为 [CE_SSR_APP_README.md](CE_SSR_APP_README.md)。

特别注意：

- 根部 `./connect.sh`：连接 CE SSR App 服务器。
- `./bin/connect.sh`：连接 CCSL 管理后台服务器。
- 根部 `deploy.sh` 具有变更能力，未经明确授权不要执行。
- 本次新增的 `bin/server-status.sh` 和 `bin/health-check.sh` 均只读。

## 安全边界

- 不保存密码、Token、Cookie、数据库连接串或私钥正文。
- CCSL 私钥只引用本机 `~/.ssh/id_ed25519`，不得复制到本目录。
- CCSL 巡检脚本不会重启、部署、改配置或写数据库。
- 不输出完整 Java 启动参数，避免泄露启动参数中的敏感配置。
- 主机指纹异常时应先核实服务器是否重装，不得直接关闭主机密钥校验。
