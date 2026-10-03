#!/usr/bin/env python3
"""Read-only OTWMS disk, inode, temp-file, Java, and HTTP health check."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from typing import Any


REMOTE_COLLECTOR = r'''
import datetime
import json
import os
import socket
import stat
import time
import urllib.request


def disk(path):
    value = os.statvfs(path)
    total = value.f_blocks * value.f_frsize
    free = value.f_bavail * value.f_frsize
    inode_total = value.f_files
    inode_free = value.f_favail
    return {
        "path": path,
        "total_bytes": total,
        "free_bytes": free,
        "used_percent": round((total - free) * 100 / total, 1) if total else None,
        "inode_total": inode_total,
        "inode_free": inode_free,
        "inode_used_percent": round((inode_total - inode_free) * 100 / inode_total, 1)
        if inode_total else None,
    }


def file_usage(path):
    try:
        value = os.stat(path)
    except OSError:
        return None
    return {
        "path": path,
        "logical_bytes": value.st_size,
        "physical_bytes": value.st_blocks * 512,
        "modified_at": datetime.datetime.fromtimestamp(value.st_mtime).astimezone().isoformat(),
    }


def tree_stats(path, stale_seconds=None):
    files = 0
    bytes_total = 0
    stale_files = 0
    stale_bytes = 0
    now = datetime.datetime.now().timestamp()
    try:
        iterator = os.walk(path)
        for root, _, names in iterator:
            for name in names:
                try:
                    value = os.stat(os.path.join(root, name), follow_symlinks=False)
                except OSError:
                    continue
                if not stat.S_ISREG(value.st_mode):
                    continue
                files += 1
                bytes_total += value.st_size
                if stale_seconds is not None and now - value.st_mtime > stale_seconds:
                    stale_files += 1
                    stale_bytes += value.st_size
    except OSError:
        pass
    return {
        "path": path,
        "files": files,
        "logical_bytes": bytes_total,
        "stale_files": stale_files,
        "stale_logical_bytes": stale_bytes,
    }


def java_processes():
    values = []
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        base = os.path.join("/proc", name)
        try:
            with open(os.path.join(base, "comm")) as handle:
                if handle.read().strip() != "java":
                    continue
            rss_bytes = None
            with open(os.path.join(base, "status")) as handle:
                for line in handle:
                    if line.startswith("VmRSS:"):
                        rss_bytes = int(line.split()[1]) * 1024
                        break
            open_tmp_files = 0
            open_poi_files = 0
            deleted_tmp_files = 0
            deleted_tmp_physical_bytes = 0
            stdout_log = None
            stdout_path = os.path.join(base, "fd", "1")
            try:
                stdout_target = os.readlink(stdout_path)
            except OSError:
                stdout_target = None
            if stdout_target == "/root/otwms-backend.log":
                with open(os.path.join(base, "fdinfo", "1")) as handle:
                    info = dict(line.strip().split(":", 1) for line in handle if ":" in line)
                stdout_log = {
                    "position": int(info["pos"].strip()),
                    "append": bool(int(info["flags"].strip(), 8) & os.O_APPEND),
                }
            for fd in os.listdir(os.path.join(base, "fd")):
                fd_path = os.path.join(base, "fd", fd)
                try:
                    target = os.readlink(fd_path)
                except OSError:
                    continue
                if target.startswith("/tmp/"):
                    open_tmp_files += 1
                    if target.startswith("/tmp/poifiles/"):
                        open_poi_files += 1
                    if target.endswith(" (deleted)"):
                        deleted_tmp_files += 1
                        try:
                            deleted_tmp_physical_bytes += os.stat(fd_path).st_blocks * 512
                        except OSError:
                            pass
            values.append({
                "pid": int(name),
                "rss_bytes": rss_bytes,
                "open_tmp_files": open_tmp_files,
                "open_poi_files": open_poi_files,
                "deleted_tmp_files": deleted_tmp_files,
                "deleted_tmp_physical_bytes": deleted_tmp_physical_bytes,
                "stdout_application_log": stdout_log,
            })
        except (OSError, ValueError):
            continue
    return sorted(values, key=lambda item: item["pid"])


def dated_tmp_dirs(retention_days):
    today = datetime.date.today()
    values = []
    try:
        names = os.listdir("/tmp")
    except OSError:
        return values
    for name in names:
        try:
            date = datetime.datetime.strptime(name, "%Y-%m-%d").date()
        except ValueError:
            continue
        path = os.path.join("/tmp", name)
        if os.path.isdir(path):
            values.append({"path": path, "age_days": (today - date).days,
                           "past_retention": (today - date).days > retention_days})
    return sorted(values, key=lambda item: item["path"])


def local_http(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return {"url": url, "status": response.status, "error": None}
    except Exception as exc:
        return {"url": url, "status": None, "error": type(exc).__name__}


log_before = file_usage("/root/otwms-backend.log")
sample_started = time.monotonic()
data = {
    "collected_at": datetime.datetime.now().astimezone().isoformat(),
    "hostname": socket.gethostname(),
    "disk": disk("/"),
    "application_log": file_usage("/root/otwms-backend.log"),
    "tmp": tree_stats("/tmp"),
    "poi_temp": tree_stats("/tmp/poifiles", stale_seconds=86400),
    "xxl_job_date_dirs": dated_tmp_dirs(7),
    "java_processes": java_processes(),
    "local_http": local_http("http://127.0.0.1:8080/"),
}
time.sleep(2)
log_after = file_usage("/root/otwms-backend.log")
if log_before and log_after:
    data["application_log_growth"] = {
        "sample_seconds": round(time.monotonic() - sample_started, 2),
        "logical_bytes_per_second": round(
            max(0, log_after["logical_bytes"] - log_before["logical_bytes"])
            / (time.monotonic() - sample_started), 1),
    }
data["application_log"] = log_after
print(json.dumps(data, separators=(",", ":")))
'''


def human_bytes(value: int | None) -> str:
    if value is None:
        return "unknown"
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return str(value)


def collect(args: argparse.Namespace) -> dict[str, Any]:
    command = [
        "gcloud", "compute", "ssh", args.instance,
        "--project", args.project,
        "--zone", args.zone,
        "--command", "sudo python3 -",
    ]
    result = subprocess.run(
        command,
        input=REMOTE_COLLECTOR,
        text=True,
        capture_output=True,
        timeout=args.timeout,
        check=False,
    )
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr.strip(), file=sys.stderr)
        raise RuntimeError(f"gcloud SSH failed with exit code {result.returncode}")
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    raise RuntimeError("remote output did not contain JSON")


def assess(data: dict[str, Any], args: argparse.Namespace) -> tuple[int, list[str]]:
    disk = data["disk"]
    warnings: list[str] = []
    critical = False
    if disk["used_percent"] >= args.critical_percent:
        warnings.append(f"CRITICAL disk usage {disk['used_percent']}%")
        critical = True
    elif disk["used_percent"] >= args.warning_percent:
        warnings.append(f"WARNING disk usage {disk['used_percent']}%")
    if disk["inode_used_percent"] >= args.critical_percent:
        warnings.append(f"CRITICAL inode usage {disk['inode_used_percent']}%")
        critical = True
    elif disk["inode_used_percent"] >= args.warning_percent:
        warnings.append(f"WARNING inode usage {disk['inode_used_percent']}%")
    if data["local_http"]["status"] != 200:
        warnings.append(f"CRITICAL local HTTP status {data['local_http']['status']}")
        critical = True
    log = data.get("application_log")
    if log and log["physical_bytes"] >= args.log_warning_gib * 1024**3:
        warnings.append(f"WARNING application log physical size {human_bytes(log['physical_bytes'])}")
    if data["tmp"]["files"] >= args.tmp_file_warning:
        warnings.append(f"WARNING /tmp file count {data['tmp']['files']}")
    for process in data.get("java_processes", []):
        stdout = process.get("stdout_application_log")
        if stdout and not stdout["append"]:
            warnings.append("WARNING application stdout is not append-mode; truncation leaves a sparse gap")
    return (2 if critical else 1 if warnings else 0), warnings


def print_human(data: dict[str, Any], warnings: list[str]) -> None:
    disk = data["disk"]
    print(f"OTWMS disk check @ {data['collected_at']} | host={data['hostname']}")
    print(
        f"Root: used={disk['used_percent']}% free={human_bytes(disk['free_bytes'])} "
        f"inodes={disk['inode_used_percent']}%"
    )
    log = data.get("application_log")
    if log:
        print(
            "App log: "
            f"logical={human_bytes(log['logical_bytes'])} physical={human_bytes(log['physical_bytes'])}"
        )
    print(f"/tmp: files={data['tmp']['files']} logical={human_bytes(data['tmp']['logical_bytes'])}")
    poi = data["poi_temp"]
    print(
        "POI temp: "
        f"files={poi['files']} logical={human_bytes(poi['logical_bytes'])} "
        f"older_24h={poi['stale_files']}/{human_bytes(poi['stale_logical_bytes'])}"
    )
    expired = [item["path"] for item in data["xxl_job_date_dirs"] if item["past_retention"]]
    print(f"XXL-JOB dated dirs past 7 days: {len(expired)}")
    for process in data["java_processes"]:
        print(
            f"Java: pid={process['pid']} rss={human_bytes(process['rss_bytes'])} "
            f"open_tmp_files={process['open_tmp_files']} "
            f"open_poi_files={process['open_poi_files']} "
            f"deleted_tmp_files={process['deleted_tmp_files']}/"
            f"{human_bytes(process['deleted_tmp_physical_bytes'])}"
        )
    http = data["local_http"]
    print(f"Local HTTP: status={http['status']} error={http['error']}")
    print("Verdict: " + ("; ".join(warnings) if warnings else "OK"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, help="Google Cloud project ID")
    parser.add_argument("--zone", required=True, help="Compute Engine zone")
    parser.add_argument("--instance", required=True, help="Current OTWMS instance name")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--warning-percent", type=float, default=80)
    parser.add_argument("--critical-percent", type=float, default=95)
    parser.add_argument("--log-warning-gib", type=float, default=10)
    parser.add_argument("--tmp-file-warning", type=int, default=200_000)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    try:
        data = collect(args)
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    code, warnings = assess(data, args)
    if args.json:
        data["assessment"] = {"exit_code": code, "messages": warnings}
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_human(data, warnings)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
