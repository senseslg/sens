#!/usr/bin/env python3
"""Create a private local configuration, without Jira credentials."""
import json
import secrets
from private_config import config_path, protect_private_path


def main():
    target = config_path()
    root = target.parent
    if not root.exists():
        root.mkdir(mode=0o700, parents=True)
        protect_private_path(root)
    if target.exists():
        print("本地配置已存在，未覆盖")
        return
    with target.open("x", encoding="utf-8") as output:
        protect_private_path(target)
        json.dump({"JIRA_BASE_URL": "https://issue.cambodianexpress.com",
                   "JIRA_SERVICE_API_KEY": secrets.token_urlsafe(32),
                   "JIRA_USERNAME": "sens", "JIRA_PASSWORD": ""}, output, indent=2)
    print("已生成私有配置；请在本机填写Jira密码，不要提交该文件")


if __name__ == "__main__":
    main()
