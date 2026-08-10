# New CCSL Server

CCSL 管理后台 Java 服务器的本地连接资料和只读运维工具。

## 快速使用

```bash
cd /Users/lingang/sens/sens-server/new-ccsl

# 登录服务器
./bin/connect.sh

# 验证 SSH 身份和连接
./bin/check-ssh.sh

# 查看系统、磁盘、服务、端口和脱敏 Java 进程
./bin/server-status.sh

# 检查应用
./bin/health-check.sh prod
./bin/health-check.sh uat
./bin/health-check.sh all
```

其他项目可以直接使用绝对路径调用：

```bash
/Users/lingang/sens/sens-server/new-ccsl/bin/server-status.sh
/Users/lingang/sens/sens-server/new-ccsl/bin/health-check.sh uat
```

服务器、应用路径、域名及当前状态见 [SERVER_INFO.md](SERVER_INFO.md)。

## 文件说明

- `ssh_config`：本目录专用 SSH 别名 `ccsl-new`。
- `bin/connect.sh`：登录或执行单条远端命令。
- `bin/check-ssh.sh`：验证连接、主机名和远端用户。
- `bin/server-status.sh`：只读采集服务器基线。
- `bin/health-check.sh`：分别验证生产和 UAT。
- `scripts/`：由上述入口调用的 Python 检查实现。

## 安全边界

- 不保存密码、Token、Cookie、数据库连接串或私钥正文。
- 私钥只引用本机 `~/.ssh/id_ed25519`，不得复制到本目录。
- 所有脚本默认只读，不部署、不重启、不改配置、不写数据库。
- 不输出完整 Java 启动参数或原始业务日志。
- 主机指纹异常时先核实服务器是否重装，不得直接关闭校验。
