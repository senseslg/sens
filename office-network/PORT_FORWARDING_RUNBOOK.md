# MikroTik 公网端口映射 Runbook

- 状态：`prepared`
- 最近更新：`2026-09-19`
- 目标：把指定公网 TCP/UDP 端口安全转发到办公网内的单个服务。
- 边界：本文不授权实际变更；每次配置前必须重新确认目标、影响、备份和回滚。

## 当前结论

一次端口映射需要 **8 个步骤**。RouterOS 核心配置通常是：

1. 必需：一条 `dstnat` 规则。
2. 条件必需：一条位于最终拒绝规则之前的 `forward accept` 规则。

如果现有防火墙已经采用“只拒绝从 WAN 进入且未经过 DST-NAT 的新连接”，则 DST-NAT 流量会通过，不应重复增加宽泛放行规则。是否需要第 2 条规则必须根据现有规则顺序判断。

## 当前办公网已验证基线

- 网关：MikroTik RB3011UiAS，RouterOS `6.49.1 stable`。
- 当前账号：自定义 `admin` 组，具备 `read`、`write`、`web`，足以通过 WebFig 配置 NAT/Firewall。
- 权限限制：无 `policy`、`ssh`、`telnet`、`api`，不能管理用户或通过这些接口执行配置。
- 现有 NAT：已存在 WAN masquerade；当前动态条目包含 UDP 5060 和 UDP 10000–65535 的 SIP/RTP 转发。
- 影响：新增 TCP Web 映射目前未见同协议冲突；新增 UDP 映射必须先复核现有范围和 SIP helper 行为。
- 管理风险：WebFig 当前使用 HTTP，配置操作只能在可信办公网内进行，且不得在不可信网络输入凭据。

## 开始前需要的参数

| 参数 | 示例 | 要求 |
|---|---|---|
| 内网目标 IP | `192.168.0.50` | 固定地址或 DHCP 静态租约 |
| 内网服务端口 | `3000` | 服务必须实际监听且本机防火墙允许 |
| 公网端口 | `443` 或高位端口 | 不能与现有映射或路由器管理服务冲突 |
| 协议 | `tcp` / `udp` | Web 服务通常是 TCP |
| 来源范围 | `<可信公网 CIDR>` | 能限制时不要对全球开放 |
| 公网入口 | 固定公网 IP / WAN 接口 | 必须确认公网 IP 是否直接位于 MikroTik |
| 域名与 TLS | 可选 | Web 服务建议使用域名、HTTPS 和反向代理 |

## 8 步实施流程

### 1. 确认暴露边界

- 明确服务用途、负责人、开放时间和允许来源。
- 管理后台、数据库、调试服务优先使用 WireGuard/Tailscale/VPN，不直接暴露。
- 前端若调用内网 API，需同时规划 API、HTTPS、CORS、Cookie 和认证。

### 2. 验证内网服务

- 服务监听内网地址或 `0.0.0.0`，不能只监听 `127.0.0.1`。
- 从另一台办公网设备访问 `<内网 IP>:<服务端口>`。
- 确认目标电脑自身防火墙允许该端口。

### 3. 固定目标地址

- 优先在 MikroTik DHCP Lease 中为目标设备设置静态租约。
- 避免只在电脑端手工设置地址而未排除 DHCP 地址冲突。

### 4. 只读采集路由器基线

至少检查：

```routeros
/system resource print
/ip address print detail
/interface list member print detail
/ip route print detail
/ip firewall nat print detail stats
/ip firewall filter print detail stats
/ip service print
```

确认 WAN 接口/接口列表、公网 IP、现有 NAT 端口、`forward` 规则顺序和管理端口冲突。输出必须脱敏，不把完整公网 IP、凭据或完整配置提交到仓库。

### 5. 建立备份和回滚点

- 保存 RouterOS 二进制备份及脱敏文本导出。
- 记录新增规则的唯一 `comment`，便于精确禁用或删除。
- 对远程配置使用 Safe Mode；本地配置也要确保有 WinBox/MAC 访问回退路径。

### 6. 新增 DST-NAT

WebFig 路径：`IP → Firewall → NAT → Add New`。

- General：`Chain=dstnat`、`Protocol=<协议>`、`Dst. Port=<公网端口>`、`In. Interface List=WAN`。
- 如果 WAN 有多个公网 IP，再指定 `Dst. Address=<固定公网 IP>`。
- Action：`Action=dst-nat`、`To Addresses=<内网 IP>`、`To Ports=<内网端口>`。

命令模板：

```routeros
/ip firewall nat add chain=dstnat action=dst-nat \
    in-interface-list=WAN protocol=tcp dst-port=<公网端口> \
    to-addresses=<内网IP> to-ports=<内网端口> \
    comment="office-network:<服务名>"
```

如已确认固定公网 IP 直接配置在 MikroTik，可额外匹配：

```routeros
dst-address=<固定公网IP>
```

如只允许可信来源，可额外匹配：

```routeros
src-address=<可信公网CIDR>
```

### 7. 按现有防火墙决定是否放行

RouterOS 的 `forward` 链在 DST-NAT 后看到的是内网目标地址和端口。只有现有规则会拒绝该流量时，才新增精确放行规则，并放在最终 `drop` 之前：

```routeros
/ip firewall filter add chain=forward action=accept \
    in-interface-list=WAN connection-nat-state=dstnat \
    protocol=tcp dst-address=<内网IP> dst-port=<内网端口> \
    comment="office-network:<服务名>:allow"
```

有来源限制时，在 NAT 和 Filter 两处使用相同的 `src-address`。不要增加无目标地址、无端口限制的宽泛 WAN 放行规则。

### 8. 外网验证、监控和回滚

- 必须用手机流量或真正的外部网络测试，不能只在办公室内通过公网 IP 测试。
- 同时验证成功访问、错误端口不可访问、认证、TLS 和应用日志。
- 查看新增规则计数器和连接跟踪，确认流量命中预期规则。
- 若失败，先禁用本次新增规则，再按应用监听、本机防火墙、NAT、Filter、上游专线依次排查。
- 若内网也需用公网域名访问，优先使用内部 DNS；必要时再单独设计 Hairpin NAT。

## 一次实施的完成标准

- [ ] 目标 IP 已固定，无 DHCP 冲突。
- [ ] 内网访问服务正常。
- [ ] 公网 IP 确认位于 MikroTik 或已明确上游设备。
- [ ] 现有 NAT、Filter 和管理端口无冲突。
- [ ] 备份与回滚路径可用。
- [ ] 只创建必要且精确的 NAT/Filter 规则。
- [ ] 真正外网访问成功，非目标端口保持关闭。
- [ ] HTTPS、认证、日志和负责人已确认。

## 回滚

优先按本次唯一 `comment` 精确查找并禁用，不直接删除：

```routeros
/ip firewall nat print detail where comment="office-network:<服务名>"
/ip firewall filter print detail where comment="office-network:<服务名>:allow"
```

确认业务恢复后，再决定是否删除规则。若还创建了 DHCP 静态租约、DNS、反向代理或证书，它们需要按各自变更记录单独回滚。

## 官方依据

- [MikroTik：Port forwarding](https://help.mikrotik.com/docs/spaces/RKB/pages/154042388/Port%2Bforwarding)
- [MikroTik：NAT](https://help.mikrotik.com/docs/spaces/ROS/pages/3211299/NAT)
- [MikroTik：Building Advanced Firewall](https://help.mikrotik.com/docs/spaces/ROS/pages/328513/Building%2BAdvanced%2BFirewall)
- [MikroTik：Firewall](https://help.mikrotik.com/docs/spaces/ROS/pages/250708066/Firewall)
