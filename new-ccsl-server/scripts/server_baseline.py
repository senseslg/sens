#!/usr/bin/env python3
"""Collect a read-only, secret-safe CCSL server baseline.

Run locally on the server, or pass --ssh-host to stream this script to a remote
Python interpreter. The script never prints complete process command lines.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import socket
import subprocess
import sys
import time
from typing import Any


SERVICE_NAMES = ("nginx", "docker", "fail2ban")


def run_text(command: list[str], timeout: int = 10) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def read_key_values(path: str, separator: str = ":") -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        for line in Path(path).read_text(errors="replace").splitlines():
            if separator in line:
                key, value = line.split(separator, 1)
                values[key.strip()] = value.strip().strip('"')
    except OSError:
        pass
    return values


def bytes_from_meminfo(value: str) -> int | None:
    parts = value.split()
    if not parts:
        return None
    try:
        amount = int(parts[0])
    except ValueError:
        return None
    return amount * 1024 if len(parts) > 1 and parts[1].lower() == "kb" else amount


def disk_info(path: str) -> dict[str, Any] | None:
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return None
    return {
        "path": path,
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "used_percent": round(usage.used * 100 / usage.total, 1) if usage.total else 0,
    }


def safe_java_processes() -> list[dict[str, Any]]:
    processes: list[dict[str, Any]] = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            if (entry / "comm").read_text().strip() != "java":
                continue
            args = (entry / "cmdline").read_bytes().split(b"\0")
            decoded = [item.decode(errors="replace") for item in args if item]
            allowed = [
                item
                for item in decoded
                if item.startswith("-Dserver.port=") or item.endswith(".jar")
            ]
            status = read_key_values(str(entry / "status"))
            processes.append(
                {
                    "pid": int(entry.name),
                    "jar": next((item for item in allowed if item.endswith(".jar")), None),
                    "server_port": next(
                        (item.split("=", 1)[1] for item in allowed if item.startswith("-Dserver.port=")),
                        None,
                    ),
                    "rss_bytes": bytes_from_meminfo(status.get("VmRSS", "")),
                    "threads": int(status["Threads"]) if status.get("Threads", "").isdigit() else None,
                }
            )
        except (OSError, ValueError):
            continue
    return sorted(processes, key=lambda item: item["pid"])


def collect() -> dict[str, Any]:
    os_release = read_key_values("/etc/os-release", "=")
    meminfo = read_key_values("/proc/meminfo")
    try:
        uptime_seconds = float(Path("/proc/uptime").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        uptime_seconds = None

    services: dict[str, str] = {}
    for service in SERVICE_NAMES:
        code, output = run_text(["systemctl", "is-active", service])
        services[service] = output or ("unknown" if code == 127 else "inactive")

    _, listeners = run_text(["ss", "-lntH"])
    listener_lines = [" ".join(line.split()) for line in listeners.splitlines() if line.strip()]

    _, failed_output = run_text(
        ["systemctl", "--failed", "--no-legend", "--no-pager", "--plain"]
    )
    failed_units = []
    for line in failed_output.splitlines():
        fields = line.split()
        if fields:
            failed_units.append(fields[0].lstrip("●"))

    apt_code, apt_output = run_text(["apt", "list", "--upgradable"], timeout=30)
    upgradable_count = None
    if apt_code == 0:
        upgradable_count = sum(1 for line in apt_output.splitlines() if "/" in line)

    disks = [item for item in (disk_info("/"), disk_info("/mnt")) if item]
    load = os.getloadavg() if hasattr(os, "getloadavg") else None
    return {
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "hostname": socket.gethostname(),
        "operating_system": os_release.get("PRETTY_NAME"),
        "kernel": os.uname().release,
        "architecture": os.uname().machine,
        "cpu_count": os.cpu_count(),
        "uptime_seconds": uptime_seconds,
        "load_average": list(load) if load else None,
        "memory": {
            "total_bytes": bytes_from_meminfo(meminfo.get("MemTotal", "")),
            "available_bytes": bytes_from_meminfo(meminfo.get("MemAvailable", "")),
            "swap_total_bytes": bytes_from_meminfo(meminfo.get("SwapTotal", "")),
        },
        "disks": disks,
        "services": services,
        "listening_tcp": listener_lines,
        "java_processes": safe_java_processes(),
        "failed_systemd_units": failed_units,
        "reboot_required": Path("/var/run/reboot-required").exists(),
        "upgradable_package_count": upgradable_count,
    }


def human_bytes(value: int | None) -> str:
    if value is None:
        return "unknown"
    amount = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if amount < 1024 or unit == "TiB":
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return str(value)


def print_human(data: dict[str, Any]) -> None:
    print(f"CCSL server baseline @ {data['collected_at']}")
    print(f"Host: {data['hostname']} | {data['operating_system']} | kernel {data['kernel']}")
    print(f"CPU: {data['cpu_count']} | load: {data['load_average']} | uptime: {data['uptime_seconds']}s")
    memory = data["memory"]
    print(
        "Memory: "
        f"total={human_bytes(memory['total_bytes'])} "
        f"available={human_bytes(memory['available_bytes'])} "
        f"swap={human_bytes(memory['swap_total_bytes'])}"
    )
    for disk in data["disks"]:
        print(
            f"Disk {disk['path']}: used={disk['used_percent']}% "
            f"free={human_bytes(disk['free_bytes'])} total={human_bytes(disk['total_bytes'])}"
        )
    print("Services: " + ", ".join(f"{k}={v}" for k, v in data["services"].items()))
    print(f"Reboot required: {data['reboot_required']} | upgradable packages: {data['upgradable_package_count']}")
    print("Java processes (sanitized):")
    for process in data["java_processes"]:
        print(
            f"  pid={process['pid']} port={process['server_port']} jar={process['jar']} "
            f"rss={human_bytes(process['rss_bytes'])} threads={process['threads']}"
        )
    print("Listening TCP sockets (no process arguments):")
    for listener in data["listening_tcp"]:
        print(f"  {listener}")
    if data["failed_systemd_units"]:
        print("Failed systemd units: " + ", ".join(data["failed_systemd_units"]))


def run_remote(host: str, forwarded_args: list[str]) -> int:
    source = Path(__file__).read_text()
    remote_command = " ".join(
        shlex.quote(item) for item in ["python3", "-", "--local", *forwarded_args]
    )
    command = ["ssh", "-o", "ConnectTimeout=10", "--", host, remote_command]
    result = subprocess.run(command, input=source, text=True, check=False)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh-host", help="SSH target such as user@host; never stored by the script")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--local", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.ssh_host and not args.local:
        return run_remote(args.ssh_host, ["--json"] if args.json else [])

    data = collect()
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print_human(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
