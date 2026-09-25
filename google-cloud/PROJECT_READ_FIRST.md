# Google Cloud 管理：先读

1. 阅读 [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) 和 [PROJECT_ITERATION_LOG.md](PROJECT_ITERATION_LOG.md)。
2. 涉及具体资源时，核对 [RESOURCE_INVENTORY.md](RESOURCE_INVENTORY.md) 的采集日期，并在控制台重新确认实时状态。
3. 涉及操作时，阅读 [MANAGEMENT_RULES.md](MANAGEMENT_RULES.md) 和对应 [RUNBOOK.md](RUNBOOK.md)；服务内部操作另读相关子项目。

## 工作规则

- 先确认项目 ID、目标资源、环境、影响范围和成功标准。实例名、IP、数量、费用均可能变化。
- 区分控制台显示的状态与业务健康：VM 显示 `Running` 不能证明 SSH、端口或应用可用。
- 默认只读。修改 IAM、网络、防火墙、账单、资源规格、实例组或生产实例前，明确操作范围、恢复方式和授权。
- 不在仓库保存密码、密钥、Token、Cookie、服务账号 JSON 或完整生产连接串。
- 完成后只更新有长期价值的事实、决定、风险和下一步；快照标注日期与来源，重要变化写入迭代日志。
