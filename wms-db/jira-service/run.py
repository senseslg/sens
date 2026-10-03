#!/usr/bin/env python3
"""Load private configuration and run on loopback only."""
import json
import os
from pathlib import Path

import uvicorn

if __name__ == "__main__":
    path = Path(__file__).resolve().parent / ".local" / "config.json"
    if path.exists():
        if path.stat().st_mode & 0o077:
            raise SystemExit("配置权限过宽，请执行 chmod 600 .local/config.json")
        config = json.loads(path.read_text(encoding="utf-8"))
        for name in ("JIRA_BASE_URL", "JIRA_SERVICE_API_KEY", "JIRA_USERNAME", "JIRA_PASSWORD"):
            if config.get(name):
                os.environ.setdefault(name, config[name])
    if not os.environ.get("JIRA_SERVICE_API_KEY"):
        raise SystemExit("请先运行 python3 setup_local.py")
    uvicorn.run("app:app", host="127.0.0.1", port=int(os.environ.get("JIRA_SERVICE_PORT", "8765")))
