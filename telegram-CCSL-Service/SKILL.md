# 复用入口

调用工具与配置见 [RUNBOOK.md](RUNBOOK.md)。本项目已提供共享 Python helper，无需额外安装全局 skill。

CLI 与 Python helper 共用系统 CA 加载逻辑，macOS 无需手工导出证书；每次发送仍需业务授权，失败不自动重试。
