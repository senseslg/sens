# CCSL Server Automation Scripts

本目录保存经过验证、可以重复执行的只读运维脚本。目标是用一致的命令和判定标准替代临时拼接命令，同时避免把密码、Token、完整 Java 启动参数或原始业务日志写入输出。

> 文档与脚本输出应简短、明确：先给 PASS/FAIL 或当前状态，再给关键指标和下一步，不输出无助于判断的过程信息。

## 服务器基线

从本地通过 SSH 执行：

```bash
python3 new-ccsl-server/scripts/server_baseline.py --ssh-host <user>@<host>
```

已经登录服务器并位于项目副本中时，也可以直接执行：

```bash
python3 new-ccsl-server/scripts/server_baseline.py
```

JSON 输出：

```bash
python3 new-ccsl-server/scripts/server_baseline.py \
  --ssh-host <user>@<host> \
  --json
```

脚本采集系统、CPU、内存、磁盘、关键服务、监听端口、安全过滤后的 Java 实例、失败的 systemd 单元、更新数量和重启标记。它不会输出完整进程命令行。

## 生产发布验证

```bash
python3 new-ccsl-server/scripts/verify_deployment.py \
  --ssh-host <user>@<host>
```

脚本默认验证生产配置：

- JAR：`/home/engineer/prod/backend/ccsl-prod.jar`
- 日志：`/home/engineer/prod/backend/ccsl-prod.log`
- 端口：`8080`
- 外部入口：`portal.ceccsl.com`、`m.ceccsl.com`

如需覆盖参数：

```bash
python3 new-ccsl-server/scripts/verify_deployment.py \
  --ssh-host <user>@<host> \
  --jar-path /path/to/app.jar \
  --log-path /path/to/app.log \
  --port 8080 \
  --domain https://example.com/ \
  --json
```

退出码：

- `0`：技术发布验证通过。
- `1`：验证未通过。
- `2`：参数或探测过程异常。

`PASS` 必须同时满足：

- JAR 存在。
- 匹配 JAR 和端口的 Java 进程存在。
- 进程启动时间不早于产物更新时间。
- 本机 HTTP 和配置的外部入口返回 2xx/3xx。
- 本次产物更新后的日志没有选定的启动失败、Hikari、OOM 或端口占用标记。

该脚本不会执行登录或数据写入，因此 `PASS` 不代表业务验收完成。管理后台登录、关键页面、数据读写和第三方接口仍需单独冒烟测试。

## 安全约束

- SSH 地址必须通过 `--ssh-host` 临时传入，不写入脚本默认值或仓库。
- 密码由 SSH 自己在终端中交互读取，脚本不接收、不保存密码。
- 不输出 `ps -ef`、完整 `/proc/<PID>/cmdline` 或完整错误日志。
- 脚本默认只读；新增任何会修改远端状态的能力前，必须拆成独立脚本并加入显式确认与回滚设计。
