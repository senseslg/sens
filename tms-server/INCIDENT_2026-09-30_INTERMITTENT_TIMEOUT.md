# 2026-09-30 TMS 间歇性超时

## 当前结论

**根因未确认，未执行生产变更。** TMS 的阻塞已复现到 Tomcat 本机 HTTP 层；不能把官网 ce-lb 的日志异常直接解释为 TMS/App 根因。时间均为柬埔寨时间 UTC+7。

## 入口对照与现场证据

- `21:41` 附近公网 TMS `/login` 与官网均完成 DNS/TCP/TLS，但等待 8 秒没有收到响应；同期 OTWMS 首页 HTTP 200、约 0.32 秒。首页正常不代表其全部业务 API 正常。
- `21:41–21:43` TMS 本机 `127.0.0.1:8080/login` 超时 8 秒，`/favicon.ico` 超时 4 秒；故障不只限于公网 LB 或单个业务页面。
- `21:43` 本机登录页恢复 HTTP 200、0.038 秒，`21:47` 为 0.009 秒；Java PID 未变。是间歇恢复，不是修复验收。
- 故障现场实例 load 约 0.00、可用内存约 12.7 GiB、根盘余 33 GB；Java PID 23935、RSS 约 11.5 GiB、线程约 265–266。未发现本次为整机内存/磁盘耗尽的证据。
- 数据库连接采样有 2 个 ESTABLISHED 和 1 个 Recv-Q 179 的 CLOSE_WAIT；后者在页面恢复后仍存在，不能仅凭一个半关闭连接认定连接池泄漏或主因。

## 2026-10-01 复发与 FD 核对

- `09:09–09:14` 官网、`cp`、OTWMS 首页返回 200，TMS 公网及本机登录页、静态资源仍超时；LB `09:10` 多条 502 为 `backend_timeout`、约 30 秒，TCP 健康检查仍显示 HEALTHY。
- 同一 Java PID 23935，线程 354（昨晚约 266），其中 OS 线程名称前缀 `http-nio-8080-e` 有 120 个；未取得线程栈，不能认定线程池耗尽或死锁。实例内存总量 32011 MiB、used 17072 MiB、available 12913 MiB，load 约 0.00。
- 用户授权尝试提高 FD 软上限；`09:14` `/proc/23935/limits` 确认 Java **soft=4096、hard=4096**，并非 ce-lb 日志采集器的 1024。当前账号不能列出 root Java 的 FD、`prlimit` 返回 Operation not permitted，`sudo -n` 要求密码；**未修改限额、未重启**。
- 只提高软上限不可超过现有硬上限。若继续临时试验，须经管理员执行、明确同时提高硬上限的范围，并记录 FD 数与 HTTP 前后对照；无效则恢复原来的 **4096/4096**，不写持久配置。
- 云端确有 Tomcat access log，可作为只读证据入口；本次非 access 的异常查询仅匹配系统采集/OSConfig 日志，不能据此声称应用无异常。根因仍未确认；下一步优先取得管理员诊断访问及故障线程栈。

## Redis 与 SQL（2026-09-30）

- TMS 使用独立 `tms-redis`，实例 READY，1 GiB、Redis 5.0；本窗口未见重启。
- `19:41–21:44` Redis 内存占用约 1.3%–2.1%，连接数恒为 34；blocked clients 在 7–8 间，非突然暴涨。该指标包含阻塞式 Redis 命令，尚不能等同于应用线程池堵塞，也不能排除应用自身 Redis 池等待。
- 先前 `19:30–20:30` 的 SQL 负载、容量与慢查询证据见 [ce-lb 事故中的跨系统对照](../otwms-ce-lb/INCIDENT_2026-09-30_LOGGING_PRESSURE.md)。不能把早一小时的数据库快照当作每次 TMS 超时现场证据。

## 新发现的安全风险（未证实为本次根因）

- 运行中 Java 参数启用 JDWP：`server=y,suspend=n,address=38081`；该端口监听 `0.0.0.0`。
- 实例具有公网地址，位于 default 网络且带 `http-server` 标签；VPC `default-allow-http` 向 `0.0.0.0/0` 放行 38081 等端口。尚未独立确认主机/上层防火墙是否另行限制，未主动连接调试器。
- 故障检查中未捕捉到 38081 已建立连接。不能因此断言无人连接，也不能宣称已发生入侵或 JVM 被暂停。
- 调试协议具备控制 JVM 执行的能力，应单独收敛暴露；参见 [Oracle JDWP 规范](https://docs.oracle.com/en/java/javase/22/docs/specs/jdwp/jdwp-protocol.html)。该规则被多个带标签的实例共用，不能直接修改共享规则而未核对其他业务和正常调试需求。

## 用户反馈：CPU Idle 与本地密码（2026-10-01 整理）

- 用户在实例页面看到 `Time Spent Idle` 约 99%；未提供截图，本次未独立确认指标及时间窗口。若这是 CPU idle 指标，表示约 99% 时间空闲，不是占用 99%；不应据此认定 CPU 满载或直接重启。
- 低 CPU 与请求无响应可以同时发生，例如线程、连接池或锁等待；只是诊断方向，不是已确认根因。需与故障线程栈、GC 和 HTTP 日志对照。
- 用户执行 `passwd` 后出现 `(current) UNIX password:` 提示；该提示以及 sudo 要求密码，都不能证明用户曾设置可用本地密码。本地 Linux 密码与 Google 账号密码不是同一凭证，不能读取其明文；本次没有完成密码重设。
- 本地密码正确也不自动赋予 sudo 权限。优先由具备权限的运维处理本地/OS Login 同名身份冲突，先核对文件归属和恢复路径，避免破坏 SSH 或 Jenkins 发布。
- 曾讨论管理员入口或隔离副本诊断作为备选，未形成已获批的恢复操作；本记录不表示已创建救援资源、变更权限或恢复 TMS。

## 下一步与阻塞

**权限复核（同日）：** 当前 Google 身份确有项目 `roles/owner`，官方 metadata `policy=adminLogin` 返回 `success:true`。TMS 开启 OS Login，但 `/etc/passwd` 存在同名 `senseslg_gmail_com` 本地用户 UID 1021，而云端 POSIX UID 为 643791315；NSS 优先 `files`，SSH 实际使用 UID 1021。已确认同名身份冲突，高概率解释当前免密 sudo 未生效，不是缺少 Owner 角色。尚未修改用户、UID、sudoers、IAM 或 SSH 配置；必须先确认旧用户文件归属、活动会话及可用管理员恢复路径。依据 [Google 官方权限诊断](https://docs.cloud.google.com/compute/docs/troubleshooting/troubleshoot-os-login#checking_login_permissions)。这属于诊断访问障碍，不是 TMS 业务超时根因。

1. 在故障时由具备目标 Java 权限的运维采集连续线程栈、GC/safepoint 和 Tomcat 错误日志，优先辨别 HTTP 工作线程、数据库/Redis 连接池等待、锁等待与 JVM 暂停。
2. 当前 SSH 会话命中同名本地用户，没有可用的免密 sudo、Tomcat 目录不可读；已有 `jstat` 尝试返回 `Could not attach`，没有绕过权限或利用公开调试端口取栈。
3. ce-lb 官网日志异常按其独立方案处理和验收；不能用官网恢复代替 TMS 恢复验收。
4. 调试暴露收敛、应用重启、连接池/JVM 参数和发布变更均待明确授权、影响核对与回滚准备。

仅完成诊断阶段；保留事故记录，不创建尚未验证的自动修复脚本或 Skill。
