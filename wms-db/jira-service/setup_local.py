#!/usr/bin/env python3
"""Create a private local configuration, without Jira credentials."""
import json
from pathlib import Path
import secrets

root = Path(__file__).resolve().parent / ".local"
root.mkdir(mode=0o700, exist_ok=True)
target = root / "config.json"
if target.exists():
    print("本地配置已存在，未覆盖")
else:
    with target.open("x", encoding="utf-8") as output:
        target.chmod(0o600)
        json.dump({"JIRA_BASE_URL": "https://issue.cambodianexpress.com",
                   "JIRA_SERVICE_API_KEY": secrets.token_urlsafe(32),
                   "JIRA_USERNAME": "sens", "JIRA_PASSWORD": ""}, output, indent=2)
    print("已生成私有配置 .local/config.json；请在本机填写 Jira 密码，不要提交该文件")
