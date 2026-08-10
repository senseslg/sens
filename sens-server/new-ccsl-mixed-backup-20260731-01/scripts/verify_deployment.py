#!/usr/bin/env python3
"""Verify a CCSL Java deployment without printing secrets or changing state.

Exit codes: 0 = technical verification passed, 1 = verification failed,
2 = invalid invocation or unexpected probe error.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import shlex
import ssl
import subprocess
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_JAR = "/home/engineer/prod/backend/ccsl-prod.jar"
DEFAULT_LOG = "/home/engineer/prod/backend/ccsl-prod.log"
DEFAULT_PORT = 8080
DEFAULT_DOMAINS = ("https://portal.ceccsl.com/", "https://m.ceccsl.com/")
FATAL_PATTERNS = (
    "Application run failed",
    "HikariPool-1 - Connection is not available",
    "OutOfMemoryError",
    "Address already in use",
)
EXCEPTION_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.]*(?:Exception|Error)")
TIMESTAMP_RE = re.compile(r"20\d\d-\d\d-\d\d[ T]\d\d:\d\d:\d\d(?:\.\d+)?")


def read_status(pid: int) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        for line in Path(f"/proc/{pid}/status").read_text(errors="replace").splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                values[key] = value.strip()
    except OSError:
        pass
    return values


def safe_java_processes() -> list[dict[str, Any]]:
    processes: list[dict[str, Any]] = []
    try:
        boot_time = next(
            int(line.split()[1])
            for line in Path("/proc/stat").read_text().splitlines()
            if line.startswith("btime ")
        )
        clock_ticks = os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError, StopIteration):
        boot_time = None
        clock_ticks = None
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if (entry / "comm").read_text().strip() != "java":
                continue
            decoded = [
                item.decode(errors="replace")
                for item in (entry / "cmdline").read_bytes().split(b"\0")
                if item
            ]
            jar = next((item for item in decoded if item.endswith(".jar")), None)
            port = next(
                (item.split("=", 1)[1] for item in decoded if item.startswith("-Dserver.port=")),
                None,
            )
            status = read_status(int(entry.name))
            rss_match = re.match(r"(\d+)", status.get("VmRSS", ""))
            started_epoch = None
            if boot_time is not None and clock_ticks:
                stat_fields = (entry / "stat").read_text().split()
                started_epoch = boot_time + int(stat_fields[21]) / clock_ticks
            processes.append(
                {
                    "pid": int(entry.name),
                    "jar": jar,
                    "server_port": port,
                    "rss_bytes": int(rss_match.group(1)) * 1024 if rss_match else None,
                    "threads": int(status["Threads"]) if status.get("Threads", "").isdigit() else None,
                    "started_epoch": started_epoch,
                    "started_at": time.strftime(
                        "%Y-%m-%dT%H:%M:%S%z", time.localtime(started_epoch)
                    ) if started_epoch else None,
                }
            )
        except (OSError, ValueError):
            continue
    return processes


def process_cpu_percent(pid: int, seconds: float = 1.0) -> float | None:
    try:
        clock_ticks = os.sysconf("SC_CLK_TCK")

        def ticks() -> int:
            fields = Path(f"/proc/{pid}/stat").read_text().split()
            return int(fields[13]) + int(fields[14])

        start_ticks = ticks()
        started = time.monotonic()
        time.sleep(seconds)
        delta_seconds = time.monotonic() - started
        return round((ticks() - start_ticks) / clock_ticks / delta_seconds * 100, 1)
    except (OSError, ValueError, IndexError):
        return None


def http_check(url: str, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    request = Request(url, headers={"User-Agent": "ccsl-deployment-verifier/1.0"})
    try:
        context = ssl.create_default_context() if url.startswith("https://") else None
        with urlopen(request, timeout=timeout, context=context) as response:
            code = response.status
            final_url = response.geturl()
        error = None
    except HTTPError as exc:
        code = exc.code
        final_url = exc.geturl()
        error = f"HTTP {exc.code}"
    except (URLError, TimeoutError, OSError) as exc:
        code = None
        final_url = url
        error = type(exc).__name__
    return {
        "url": url,
        "status": code,
        "final_url": final_url,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "ok": code is not None and 200 <= code < 400,
        "error": error,
    }


def tail_bytes(path: Path, limit: int) -> str:
    with path.open("rb") as handle:
        handle.seek(0, os.SEEK_END)
        size = handle.tell()
        handle.seek(max(0, size - limit))
        return handle.read().decode(errors="replace")


def log_summary(path: Path, limit: int, since_epoch: float | None) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "bytes_scanned": 0, "fatal_counts": {}, "error_lines": None}
    raw_text = tail_bytes(path, limit)
    text = raw_text
    filter_applied = False
    since_text = None
    if since_epoch is not None:
        since_text = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(since_epoch))
        lines = raw_text.splitlines()
        for index, line in enumerate(lines):
            match = TIMESTAMP_RE.search(line)
            if match and match.group(0)[:19] >= since_text:
                text = "\n".join(lines[index:])
                filter_applied = True
                break
        if not filter_applied:
            text = ""
    error_lines = [line for line in text.splitlines() if "ERROR" in line]
    exceptions: Counter[str] = Counter()
    timestamps: list[str] = []
    for line in error_lines:
        exceptions.update(EXCEPTION_RE.findall(line))
        match = TIMESTAMP_RE.search(line)
        if match:
            timestamps.append(match.group(0))
    return {
        "exists": True,
        "bytes_read": len(raw_text.encode()),
        "bytes_scanned_after_filter": len(text.encode()),
        "since": since_text,
        "since_filter_applied": filter_applied,
        "fatal_counts": {pattern: text.count(pattern) for pattern in FATAL_PATTERNS},
        "error_lines": len(error_lines),
        "error_time_first": timestamps[0] if timestamps else None,
        "error_time_last": timestamps[-1] if timestamps else None,
        "exception_classes": dict(exceptions.most_common(20)),
    }


def verify(args: argparse.Namespace) -> tuple[dict[str, Any], bool]:
    jar = Path(args.jar_path)
    jar_info = {
        "path": str(jar),
        "exists": jar.exists(),
        "size_bytes": jar.stat().st_size if jar.exists() else None,
        "modified_at": time.strftime(
            "%Y-%m-%dT%H:%M:%S%z", time.localtime(jar.stat().st_mtime)
        ) if jar.exists() else None,
    }
    java_processes = safe_java_processes()
    matches = [
        process
        for process in java_processes
        if process["jar"] == args.jar_path and process["server_port"] == str(args.port)
    ]
    for process in matches:
        process["cpu_percent_1s"] = process_cpu_percent(process["pid"])

    process_time_matches = [
        process
        for process in matches
        if process.get("started_epoch") is not None
        and jar.exists()
        and process["started_epoch"] >= jar.stat().st_mtime - 10
    ]

    local_http = http_check(f"http://127.0.0.1:{args.port}/", args.timeout)
    external_http = [http_check(url, args.timeout) for url in args.domain]
    logs = log_summary(
        Path(args.log_path),
        args.log_bytes,
        jar.stat().st_mtime if jar.exists() else None,
    )
    fatal_total = sum(logs.get("fatal_counts", {}).values())
    passed = bool(
        jar_info["exists"]
        and process_time_matches
        and local_http["ok"]
        and all(item["ok"] for item in external_http)
        and fatal_total == 0
    )
    result = {
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "result": "PASS" if passed else "FAIL",
        "jar": jar_info,
        "matching_processes": matches,
        "process_time_matches_artifact": bool(process_time_matches),
        "local_http": local_http,
        "external_http": external_http,
        "log_summary": logs,
        "notes": [
            "PASS confirms process, port, HTTP entry points, and absence of selected fatal log markers.",
            "Authenticated login and critical business flows require a separate smoke test.",
            "Complete Java command lines and log messages are intentionally not printed.",
        ],
    }
    return result, passed


def human_bytes(value: int | None) -> str:
    if value is None:
        return "unknown"
    return f"{value / 1024 / 1024:.1f} MiB"


def print_human(result: dict[str, Any]) -> None:
    print(f"CCSL deployment verification: {result['result']} @ {result['verified_at']}")
    jar = result["jar"]
    print(f"JAR: exists={jar['exists']} modified={jar['modified_at']} size={jar['size_bytes']}")
    if not result["matching_processes"]:
        print("Matching production Java process: NOT FOUND")
    for process in result["matching_processes"]:
        print(
            f"Process: pid={process['pid']} port={process['server_port']} "
            f"started={process['started_at']} "
            f"rss={human_bytes(process['rss_bytes'])} threads={process['threads']} "
            f"cpu_1s={process.get('cpu_percent_1s')}%"
        )
    local = result["local_http"]
    print(f"Local HTTP: status={local['status']} time={local['elapsed_seconds']}s ok={local['ok']}")
    for item in result["external_http"]:
        print(
            f"External: {item['url']} status={item['status']} ok={item['ok']} "
            f"time={item['elapsed_seconds']}s final={item['final_url']}"
        )
    logs = result["log_summary"]
    print(
        f"Logs: exists={logs['exists']} error_lines={logs['error_lines']} "
        f"fatal_counts={logs['fatal_counts']}"
    )
    if logs.get("exception_classes"):
        print("Exception classes (sanitized):")
        for name, count in logs["exception_classes"].items():
            print(f"  {count:>5} {name}")
    for note in result["notes"]:
        print(f"NOTE: {note}")


def remote_arguments(args: argparse.Namespace) -> list[str]:
    values = [
        "--local",
        "--jar-path", args.jar_path,
        "--log-path", args.log_path,
        "--port", str(args.port),
        "--timeout", str(args.timeout),
        "--log-bytes", str(args.log_bytes),
    ]
    for domain in args.domain:
        values.extend(["--domain", domain])
    if args.json:
        values.append("--json")
    return values


def run_remote(host: str, args: argparse.Namespace) -> int:
    source = Path(__file__).read_text()
    remote_command = " ".join(
        shlex.quote(item) for item in ["python3", "-", *remote_arguments(args)]
    )
    command = ["ssh", "-o", "ConnectTimeout=10", "--", host, remote_command]
    result = subprocess.run(command, input=source, text=True, check=False)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", help="SSH target such as user@host; never stored by the script")
    parser.add_argument("--jar-path", default=DEFAULT_JAR)
    parser.add_argument("--log-path", default=DEFAULT_LOG)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--domain", action="append", help="HTTPS entry to verify; repeatable")
    parser.add_argument("--timeout", type=int, default=12)
    parser.add_argument("--log-bytes", type=int, default=20_000_000)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--local", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.domain is None:
        args.domain = list(DEFAULT_DOMAINS)

    if args.ssh_host and not args.local:
        return run_remote(args.ssh_host, args)

    try:
        result, passed = verify(args)
    except Exception as exc:  # Last-resort concise failure, without dumping sensitive data.
        print(f"verification error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_human(result)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
