from __future__ import annotations

import os
from pathlib import Path


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable is not set: {name}")
    return value


ROOT_DIR = Path(__file__).resolve().parents[2]
APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"
SENS_SERVER_DIR = ROOT_DIR / "sens-server"
LOCAL_DEVICE_MD = ROOT_DIR / "LOCAL_DEVICE_STATUS.md"
LOCAL_MYSQL_DIR = Path(
    os.getenv("SENS_PORTAL_MYSQL_DIR", str(ROOT_DIR / ".local-mysql84"))
)
LOCAL_MYSQL_SOCKET = Path(
    os.getenv("SENS_PORTAL_MYSQL_SOCKET", str(LOCAL_MYSQL_DIR / "run" / "mysql.sock"))
)

MYSQL_ROOT_PASSWORD = required_env("SENS_PORTAL_MYSQL_ROOT_PASSWORD")
MYSQL_DATABASE = os.getenv("SENS_PORTAL_MYSQL_DATABASE", "sens")
ADMIN_USERNAME = os.getenv("SENS_PORTAL_ADMIN_USERNAME", "sens")
ADMIN_PASSWORD = required_env("SENS_PORTAL_ADMIN_PASSWORD")
SESSION_SECRET = required_env("SENS_PORTAL_SESSION_SECRET")
ENABLE_REMOTE_CHECKS = os.getenv("SENS_PORTAL_ENABLE_REMOTE_CHECKS", "0") == "1"

LOCAL_DISK_WARN_PERCENT = float(os.getenv("SENS_PORTAL_DISK_WARN_PERCENT", "85"))
LOCAL_MEMORY_WARN_PERCENT = float(os.getenv("SENS_PORTAL_MEMORY_WARN_PERCENT", "10"))

SERVICE_ORDER = [
    "cs-online",
    "mallgogo",
    "new-ccsl",
    "d-mall-sever",
    "new-ccsl-mixed-backup-20260731-01",
]

SERVICE_LABELS = {
    "cs-online": "Chatwoot / cs-online",
    "mallgogo": "Mallgogo",
    "new-ccsl": "CCSL 管理后台",
    "d-mall-sever": "D-Mall / ce-ssr-app",
    "new-ccsl-mixed-backup-20260731-01": "CCSL 历史混合备份",
}
