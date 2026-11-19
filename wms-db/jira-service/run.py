#!/usr/bin/env python3
"""Load private configuration and run on loopback only (Windows/macOS/Linux)."""
import os
import uvicorn
from private_config import load_environment

if __name__ == "__main__":
    try:
        load_environment()
        if not os.environ.get("JIRA_SERVICE_API_KEY"):
            raise ValueError("请先运行python setup_local.py")
        port = int(os.environ.get("JIRA_SERVICE_PORT", "8765"))
        if not 1 <= port <= 65535:
            raise ValueError("服务端口无效")
    except (OSError, ValueError) as error:
        raise SystemExit("配置加载失败，请检查本机私有配置与权限（不输出凭据）") from None
    uvicorn.run("app:app", host="127.0.0.1", port=port)
