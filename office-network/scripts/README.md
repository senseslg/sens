# Office Network Scripts

## `port_forward_precheck.py`

只读检查一个公网端口映射的参数、内网 TCP 可达性和脱敏 RouterOS 导出，并生成供人工审核的规则模板。脚本不会登录路由器，也不会执行任何配置。

```bash
python3 office-network/scripts/port_forward_precheck.py \
  --service-name demo-web \
  --target-ip 192.168.0.50 \
  --target-port 3000 \
  --public-port 8443 \
  --source-cidr 198.51.100.10/32
```

如已取得脱敏后的 RouterOS 文本导出，可增加：

```bash
--router-export /path/to/sanitized-router-export.rsc
```

脚本会检查已有 `dstnat` 公网端口冲突，但无法替代人工检查 RouterOS 规则顺序。完整实施与回滚步骤见 [`../PORT_FORWARDING_RUNBOOK.md`](../PORT_FORWARDING_RUNBOOK.md)。

退出码：

- `0`：未发现本地服务失败或明确端口冲突，可以进入人工路由器审核。
- `1`：内网 TCP 服务不可达，或脱敏导出中发现公网端口冲突。
- `2`：命令参数无效。
