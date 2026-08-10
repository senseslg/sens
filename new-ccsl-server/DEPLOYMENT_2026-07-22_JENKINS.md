# 2026-07-22 Jenkins Production Deployment Verification

- 日期：`2026-07-22`
- 环境：CCSL 生产
- 发布方式：Jenkins
- 验证方式：经授权 SSH 会话内的只读命令
- 结论：技术发布成功；业务冒烟测试待完成

## 时间与进程证据

- `/home/engineer/prod/backend/ccsl-prod.jar` 的更新时间为 `2026-07-22 12:03:44`。
- 新生产 Java 进程的启动时间同为 `2026-07-22 12:03:44`。
- 经筛选后的启动字段确认该进程运行 `ccsl-prod.jar` 并使用 `server.port=8080`。
- 原有另一 Java 进程是 UAT：`/home/engineer/uat/backend/ccsl-uat.jar`，端口 `8081`，不是生产旧进程残留。

不在本文记录瞬时 PID，避免后续把失效 PID 当作稳定资产标识。

## 路由与可用性

- Nginx 的生产入口 `portal.ceccsl.com`、`m.ceccsl.com` 代理到 `127.0.0.1:8080`。
- UAT 入口 `m-uat.ceccsl.com`、`ccsl-uat.cambodianexpress.com` 代理到 `127.0.0.1:8081`。
- `http://127.0.0.1:8080/` 返回 200。
- `https://portal.ceccsl.com/` 返回 200，并跳转到正式管理入口。
- `https://m.ceccsl.com/` 返回 200。
- UAT HTTPS 入口也返回 200，说明 UAT 进程未因本次生产发布中断。
- `/actuator/health` 返回 404，当前不能用作标准健康检查端点。

## 资源与日志观察

发布后约 10 分钟的只读观测：

- 生产 Java RSS 约 3.6 GiB。
- Java 线程约 514。
- 三秒 CPU 采样为 11%、5%、14%，平均约 10%。
- 最近日志窗口未发现 `Application run failed`、Hikari 获取超时或 `OutOfMemoryError`。

同一日志窗口包含约 50 行 ERROR，时间集中在 `12:10:35` 至 `12:13:35`。脱敏分类中主要包括：

- Google API HTTP 响应异常。
- 少量 `IllegalStateException`。
- 少量 SQL、数据完整性、JSON 解析和空指针异常。

这些错误未阻止应用启动和 HTTP 服务，但需要按接口、请求影响和是否为历史已知错误继续归因。

## 安全发现

生产 Java 的完整命令行包含明文敏感配置。检查过程中没有把具体值写入本项目。后续必须：

1. 轮换可能暴露的 Token、密码和第三方凭证。
2. 将敏感值迁移到受控环境变量或密钥管理服务。
3. 避免在终端记录和自动采集里使用会输出完整命令行的 `ps -ef`、`ps ... cmd` 或 `pgrep -af`。

## 验收结论

以下技术项已通过：

- [x] Jenkins 产物已更新。
- [x] 新生产进程已按产物更新时间启动。
- [x] 生产进程运行正确 JAR 和端口。
- [x] 本机 upstream 返回 200。
- [x] 生产 HTTPS 入口返回 200。
- [x] 未发现启动失败、Hikari 获取超时或 OOM。

以下业务项仍待执行：

- [ ] 管理后台登录。
- [ ] 订单、包裹、费用和客户相关关键页面。
- [ ] 数据新增、修改与查询。
- [ ] 涉及 Google/第三方接口的功能。
- [ ] 发布后 ERROR 的业务影响归因。
- [ ] 回滚路径或上一版本产物验证。

## 后续复用

本次技术验证已固化为 [`scripts/verify_deployment.py`](scripts/verify_deployment.py)。后续 Jenkins 发布后优先直接执行：

```bash
python3 new-ccsl-server/scripts/verify_deployment.py --ssh-host <user>@<host>
```

脚本以退出码 `0` 表示技术验证通过，并可用 `--json` 生成结构化结果。它不会替代需要登录或写数据的业务冒烟测试。

2026-07-22 12:27 在 SSH 公钥认证配置完成后进行了首次端到端脚本复验，结果为 `PASS`、退出码为 `0`。产物与进程启动时间一致，本机及两个生产 HTTPS 入口均返回 200，选定的四类致命日志标记均为 0。
