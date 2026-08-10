# CCSL Production Database Pool Exhaustion Incident

- 事件日期：`2026-07-21`
- 环境：CCSL 生产环境
- 状态：服务已恢复，永久修复未完成
- 最近更新：`2026-07-21`
- 来源：`/Users/lingang/Downloads/CCSL_生产系统数据库连接池耗尽事件记录_2026-07-21.md`

## 事件摘要

CCSL 生产系统先后两次出现登录及后台接口超时，Nginx 返回 `504 Gateway Timeout`。Java 应用的 Hikari 数据库连接池耗尽，大量请求等待数据库连接并在 30 秒后失败。重启应用能短暂恢复，但较短时间后再次发生，说明重启只是解除资源堆积，没有修复根因。

第二次故障期间保存的 `jstack` 显示，大量业务线程阻塞在 Spring Redis Cache 的同一个对象锁，同时另有大量线程等待 `HikariPool.getConnection()`。当前证据支持：缓存锁竞争与事务范围共同延长了数据库连接持有时间，最终触发连接池耗尽和系统雪崩。

## 业务影响

- 用户登录和多个后台接口出现 504。
- 请求长时间无响应，客户端超时后主动断开。
- Java 应用无法及时处理新请求。
- 服务端 TCP 连接从约 1,000 增长至 6,000 以上，并出现大量 `CLOSE_WAIT` 与 `FIN_WAIT_2`。
- CPU 和内存没有同步出现明显资源耗尽，问题集中在应用线程、缓存锁、数据库连接和连接关闭链路。

## 已确认事实

### 应用与连接池

- 生产应用为 Java JAR，监听 `8080`。
- 数据库连接池使用 HikariCP。
- 日志反复出现：

```text
HikariPool-1 - Connection is not available, request timed out after 30000ms
Could not open JDBC Connection
Failed to obtain JDBC Connection
CannotCreateTransactionException
Broken pipe
```

- 事故期间 Java 线程约 591、RSS 内存约 5.8 GB、打开文件描述符约 4,386。
- `/pdd-api/track_query` 等接口存在高频调用迹象。

### 第二次故障现场

- MySQL `Threads_connected = 16`、`Threads_running = 3`。
- 数据库允许连接上限远高于现场连接数。
- `SHOW FULL PROCESSLIST` 未发现大量长查询、锁等待或元数据锁。
- 大多数业务数据库连接处于短时 `Sleep`。
- `jstack` 中大量线程阻塞于：

```text
org.springframework.data.redis.cache.RedisCache.get
waiting to lock RedisCache
```

- 高频调用路径包括：
  - `CCSLCache.getCustomer`
  - `OrderWrapper.listVO`
  - `ParcelManager.calculateFee`
  - `ParcelManager.inbound`
  - `ParcelWrapper.entityVO`
  - `ShopeeManager.shopeeShipmentCreate`
- 同时存在大量线程等待 `HikariPool.getConnection()`。

### 数据库状态

- 应用重启后的 InnoDB 状态正常：没有查询排队、待处理读写或长事务积压。
- 曾观察到 MySQL 连接中断和自动重连：`MySQL server has gone away`、`Lost connection to MySQL server during query`。
- 部分查询首次执行较慢，`external_interface_log` 上的前置通配符 `LIKE '%...%'` 查询曾耗时约 25–28 秒。
- `2026-07-19` 的 `new_ccsl.cost` 并发插入曾触发死锁；该事件发生在本次事故前两天，不足以认定为本次根因，但可能放大高峰期连接占用。
- `2026-05-26` 的 UAT 外键错误属于测试数据一致性问题，与本次生产事故无直接关系。

## 原因判断

### 直接原因

Hikari 数据库连接池中的可用连接耗尽，新请求无法在 30 秒内取得连接，继而导致事务创建失败、请求超时、504、Broken pipe 和 TCP 连接堆积。

### 当前主要根因

> 后端代码中的 Redis Cache 锁竞争与数据库事务/连接池共同作用，导致数据库连接无法及时归还并最终耗尽 Hikari 连接池。

证据链：

1. `CCSLCache.getCustomer()` 被多个高频业务链路调用。
2. 大量线程争用同一个 `RedisCache` 对象锁。
3. 部分缓存或外部调用位于 Spring Transaction 内部。
4. 线程等待缓存锁期间仍可能持有数据库连接。
5. Hikari 可用连接逐渐归零，更多线程开始等待连接。
6. 请求超时后客户端断开，服务端继续写响应产生 `Broken pipe`。
7. 数据库现场没有连接总数耗尽或整体慢查询阻塞的证据。

### 放大因素与待验证项

- `OrderWrapper.listVO()`、`ParcelWrapper.entityVO()` 等逐条获取客户缓存，可能形成 N+1 式缓存/数据库访问。
- 事务范围可能包含缓存加载、第三方 HTTP 或其他耗时逻辑。
- `external_interface_log` 写入失败主要是连接池耗尽的连锁反应，但大表扫描和同步日志写入可能进一步占用连接。
- `cost` 表并发写入和死锁可能延长部分事务。
- MySQL/RDS 空闲连接、代理层或网络中断仍需独立确认。
- Hikari 参数、真实池大小和连接泄漏情况尚未完成核对。

## 临时恢复

生产部署目录：

```text
/home/engineer/prod/backend
```

主要文件包括 `ccsl-prod.jar`、`deploy.sh`、应用日志和 GC 日志。当前未使用 systemd；`deploy.sh` 会用 `kill -9` 终止旧进程，再通过 `nohup java -jar` 启动应用。普通用户因进程和日志权限不足无法完成重启，最终使用管理员权限执行脚本后恢复。

重启后：

- Java 进程重新运行。
- `8080` 恢复监听。
- 接口恢复响应。
- 数据库没有持续锁等待和事务排队。

该操作只能作为紧急恢复手段，不应视为根因修复。

## 修复行动

| 优先级 | 状态 | 行动 | 验收标准 |
|---|---|---|---|
| P0 | 待办 | 修改 `CCSLCache.getCustomer()`，避免在共享缓存锁内执行数据库加载 | 并发压测时不再出现大量线程等待同一 `RedisCache` 锁 |
| P0 | 待办 | 缩小事务范围，禁止在事务中等待缓存和第三方 HTTP | 线程栈与事务监控显示连接持有时间显著下降 |
| P0 | 待办 | 将逐条客户查询/缓存改为批量查询或批量缓存 | 典型订单、包裹流程的缓存与 SQL 调用次数显著下降 |
| P0 | 待办 | 增加 Hikari Active、Idle、Pending、Max 和获取超时告警 | 连接池接近耗尽时可提前告警 |
| P1 | 待办 | 临时启用 Hikari 连接泄漏检测，例如 60 秒阈值 | 能记录长期持有连接的调用栈；验证后评估运行开销 |
| P1 | 待办 | 为外部接口设置连接/读取超时、限流和必要的异步处理 | 外部服务阻塞不再长时间占用事务和工作线程 |
| P1 | 待办 | 检查 `cost` 并发写入顺序、唯一索引和死锁重试 | 压测中死锁可控且业务能有限重试 |
| P1 | 待办 | 优化或替代 `external_interface_log` 前置通配符查询 | 不再出现 25 秒级全表扫描；有 EXPLAIN 与前后对比 |
| P1 | 待办 | 将日志写入与主业务隔离，日志失败不得阻塞主流程 | 日志存储异常时主业务仍可受控运行 |
| P1 | 待办 | 排查 RDS 慢日志、连接错误和代理层断连 | 明确 `server has gone away` / `Lost connection` 原因 |
| P2 | 待办 | 用 systemd 管理 Java 服务并实现优雅停止 | 自动恢复、日志、权限和停止流程经过验证 |
| P2 | 待办 | 建立事故现场自动采集脚本 | 故障时保存 jstack、processlist、InnoDB、GC 和 TCP 状态 |

调整 Hikari 池大小只能作为缓解手段；未缩短连接持有时间前盲目扩池可能把压力转移到数据库。

## 事故现场采集清单

发生类似问题时，优先保存证据，再决定是否重启：

- Java `jstack`。
- Hikari Active / Idle / Pending / Max。
- Java 线程、RSS、GC 和文件描述符。
- `8080` 的 TCP 状态分布。
- MySQL `SHOW FULL PROCESSLIST`。
- `SHOW ENGINE INNODB STATUS\G`。
- RDS 连接数、活跃连接、慢 SQL 和连接错误监控。
- Nginx 504 数量与 upstream 响应时间。
- 高频接口、请求时间和外部依赖耗时。

## 安全后续

原始排查终端曾显示数据库、Redis、第三方接口、JWT 和通知机器人等敏感配置。本文不复制任何值。应完成：

- 轮换可能暴露的数据库和 Redis 密码。
- 轮换第三方接口、JWT 和通知机器人相关密钥或 Token。
- 检查历史日志、脚本和终端记录中的明文凭证。
- 将敏感配置迁移到受控环境变量或密钥管理服务。

## 当前结论

- 服务当前已恢复。
- 重启不是永久修复，事故已经复发过一次。
- 数据库实例本身不是当前主要根因。
- Redis Cache 锁竞争、事务范围和连接持有时间是首要修复方向。
- 慢 SQL、`cost` 死锁和连接中断属于放大因素或独立风险，需要继续处理。
