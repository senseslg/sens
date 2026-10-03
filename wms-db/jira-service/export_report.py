#!/usr/bin/env python3
"""Export a resolved-issue report via the running local Jira service."""
import argparse
import csv
from datetime import date
import io
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

from reporting import REPORT_COLUMNS, REPORT_NAMES

ROOT = Path(__file__).resolve().parent
DEFAULT_EXPORT_DIR = Path.home() / "Downloads"


def month_window(value):
    if not re.fullmatch(r"\d{4}-\d{2}", value):
        raise ValueError("月份格式必须是 YYYY-MM")
    start = date.fromisoformat(value + "-01")
    end = date(start.year + 1, 1, 1) if start.month == 12 else date(start.year, start.month + 1, 1)
    return start, end


def save_csv(data, expected_count, destination):
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
    if (not data.startswith(b"\xef\xbb\xbf") or not rows or
            rows[0] != [REPORT_NAMES[c] for c in REPORT_COLUMNS] or
            len(rows) - 1 != expected_count or any(len(row) != 8 for row in rows[1:])):
        raise ValueError("响应格式或条数不符，未保存报表")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects existing reports even if another export races us.
    with destination.open("xb") as output:
        output.write(data)
    return len(rows) - 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="按解决日期导出固定 8 列 CSV；需先启动 run.py")
    period = parser.add_mutually_exclusive_group(required=True)
    period.add_argument("--month", help="月份，如 2026-09")
    period.add_argument("--start", type=date.fromisoformat, help="起始日，包含，YYYY-MM-DD")
    parser.add_argument("--end", type=date.fromisoformat, help="结束日，不包含；与 --start 一起使用")
    parser.add_argument("--project", action="append", default=[], help="项目代号，可重复；默认全部可见项目")
    parser.add_argument("--timezone", default="Asia/Phnom_Penh")
    parser.add_argument("--output", type=Path, help="输出 CSV；默认 ~/Downloads，拒绝覆盖已有文件")
    args = parser.parse_args(argv)
    try:
        if args.month:
            if args.end:
                raise ValueError("--month 不可与 --end 一起使用")
            start, end = month_window(args.month)
        else:
            if args.end is None:
                raise ValueError("--start 必须同时提供 --end")
            start, end = args.start, args.end
        if end <= start:
            raise ValueError("结束日必须晚于起始日")
        destination = args.output or DEFAULT_EXPORT_DIR / f"jira-resolved-{start}-{end}.csv"
        if destination.exists():
            raise ValueError("输出文件已存在，请指定新的 --output")
        key = os.environ.get("JIRA_SERVICE_API_KEY")
        if not key:
            config_path = ROOT / ".local" / "config.json"
            if config_path.stat().st_mode & 0o077:
                raise ValueError("配置权限过宽，应为 600")
            key = json.loads(config_path.read_text()).get("JIRA_SERVICE_API_KEY")
        if not key:
            raise ValueError("尚未配置本地服务密钥，请先运行 setup_local.py")
        port = int(os.environ.get("JIRA_SERVICE_PORT", "8765"))
        if not 1 <= port <= 65535:
            raise ValueError("服务端口无效")
        payload = {"start_date": start.isoformat(), "end_date": end.isoformat(),
                   "timezone": args.timezone, "projects": args.project, "limit": 10000}
        request = urllib.request.Request(f"http://127.0.0.1:{port}/reports/resolved/export",
                    data=json.dumps(payload).encode(),
                    headers={"X-API-Key": key, "Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=300) as response:
            data = response.read()
            expected_count = int(response.headers["X-Export-Count"])
        count = save_csv(data, expected_count, destination)
        print(f"已导出 {count} 条；区间 [{start}, {end})；时区 {args.timezone}；文件 {destination.resolve()}")
        return 0
    except urllib.error.HTTPError as error:
        print(f"导出失败：HTTP {error.code}；请核对服务认证、查询范围与服务日志，不输出凭据。")
    except urllib.error.URLError:
        print("无法连接本机服务，请先启动 run.py；未生成报表。")
    except (OSError, ValueError, TypeError, KeyError) as error:
        # Never echo configuration, request headers or arbitrary remote content.
        print(f"导出失败（{type(error).__name__}）：请核对参数、配置权限及输出文件；未完成导出。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
