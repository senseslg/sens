#!/usr/bin/env python3
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from admin_portal.backend.config import LOCAL_DEVICE_MD
from admin_portal.backend.system import collect_dashboard_snapshot


def main() -> None:
    snapshot = collect_dashboard_snapshot()
    local = snapshot["local"]
    summary = snapshot["summary"]

    md = f"""# 本地设备与系统状况

> 记录本机和后续可能加入的服务端设备信息。新增设备时只追加当前状态，不保留重复聊天记录。

## 当前设备

| 设备 | 角色 | 主机 | 系统 | CPU / 内存 | 磁盘 | MySQL | 状态 | 更新时间 |
|---|---|---|---|---|---|---|---|---|
| {local['hostname']} | 本地管理机 | `{local['hostname']}` | {local['os']} {local['os_version']} | {local['cpu_count']} 核 / {local['memory']['total_mb']} MB | {local['disk']['total_gb']} GB，总使用 {local['disk']['used_percent']}% | {local['mysql']['version']}，`sens` 库已创建 | {local['health']} | {datetime.now().strftime('%Y-%m-%d %H:%M')} |

## 关键说明

- 当前告警主要来自系统盘使用率较高。
- 本机 MySQL 以本地 socket 方式运行，数据库 `sens` 已准备好供管理后台使用。
- 当前后台汇总的服务目录数量为 {summary['service_count']}，其中 {summary['warning_count']} 个目录显示为关注状态。
- 后续如新增服务端设备，继续追加到这里，并同步更新状态与最近采集时间。
"""
    Path(LOCAL_DEVICE_MD).write_text(md, encoding="utf-8")
    print(str(LOCAL_DEVICE_MD))


if __name__ == "__main__":
    main()
