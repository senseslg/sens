# RUNBOOK

当前仓库在本机上已经验证过的操作记录。这里保存环境相关经验，不保存通用工作背景。

## Device Snapshot

- Host: `MacBook-Pro.local`
- OS / Kernel: `Darwin 25.2.0`
- Architecture: `arm64`
- Shell: `/bin/bash`
- Repo root: `/Users/lingang/sens`
- Git branch: `main`
- Remote: `git@github.com:senseslg/sens.git`

## 常用检查

```bash
git status --short --branch
git branch --show-current
git remote -v
```

## 更新记录后的检查

```bash
git diff --check
git status --short
git diff --stat
```

## 提交与推送

先查看变更范围，只暂存本次相关文件：

```bash
git status --short
git add <相关文件>
git diff --cached --stat
git commit -m "简短且具体的说明"
git push origin main
```

## 恢复工作上下文

1. 阅读 `PROJECT_READ_FIRST.md`。
2. 查看最近的 `PROJECT_ITERATION_LOG.md` 条目。
3. 打开本次工作对应的 `records/projects/` 文件。
4. 用 `git status --short --branch` 确认是否存在未完成修改。

## Notes

- 只记录在这台设备和当前仓库中实际验证过的命令。
- 环境变化后先更新 Device Snapshot，再更新相关命令。
- 如果 Git 写操作出现 `.git/index.lock` 或权限错误，确认没有其他 Git 进程后，再按当前执行环境的授权机制重试。
- 不在此文件记录密码、Token、私钥或生产连接凭证。
