from __future__ import annotations

import os
import platform
import re
import shutil
import socket
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import (
    LOCAL_DEVICE_MD,
    LOCAL_DISK_WARN_PERCENT,
    LOCAL_MEMORY_WARN_PERCENT,
    ENABLE_REMOTE_CHECKS,
    SENS_SERVER_DIR,
    SERVICE_LABELS,
    SERVICE_ORDER,
)
from .db import inspect_database


def _run_command(args: list[str], cwd: Path | None = None, timeout: int = 30) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        combined = "\n".join(part for part in [stdout, stderr] if part)
        return {
            "args": args,
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "output": combined,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "args": args,
            "returncode": 124,
            "stdout": (exc.stdout or "").strip(),
            "stderr": (exc.stderr or "").strip() or f"Timed out after {timeout}s",
            "output": (exc.stdout or "").strip(),
            "error": "timeout",
        }


def _first_non_empty(lines: list[str]) -> str:
    for line in lines:
        if line.strip():
            return line.strip()
    return ""


def _trim_output(text: str, limit: int = 20) -> str:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) <= limit:
        return "\n".join(lines)
    head = lines[: max(6, limit // 2)]
    tail = lines[-max(6, limit // 2) :]
    return "\n".join(head + ["..."] + tail)


def _normalize_label(value: str) -> str:
    return re.sub(r"[\s\-/_:·|()]+", "", value.strip().lower())


def _markdown_table_pairs(text: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|") or line.count("|") < 2:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        key, value = cells[0], cells[1]
        if not key or not value:
            continue
        normalized_key = _normalize_label(key)
        normalized_value = _normalize_label(value)
        if normalized_key in {"item", "项目", "字段", "name"}:
            continue
        if normalized_value in {"verifiedvalue", "当前值", "已确认信息", "已核验信息", "value", "verified"}:
            continue
        pairs.append((key, value))
    return pairs


def _service_device_info(folder: Path) -> dict[str, Any] | None:
    combined = []
    for filename in ("SERVER_INFO.md", "README.md"):
        path = folder / filename
        if path.exists():
            combined.append(path.read_text(encoding="utf-8", errors="ignore"))
    if not combined:
        return None

    pairs = _markdown_table_pairs("\n".join(combined))
    if not pairs:
        return None

    field_order = [
        ("ssh", ["ssh", "ssh连接", "ssh主机", "ssh端口", "ssh别名"]),
        ("hostname", ["hostname", "主机名", "远端主机名"]),
        ("provider", ["provider", "云平台"]),
        ("os", ["os", "操作系统"]),
        ("kernel", ["kernel", "内核"]),
        ("architecture", ["architecture", "架构"]),
        ("cpu", ["cpu", "cpu逻辑", "cpu核心", "cpu / memory", "cpu/内存"]),
        ("memory", ["memory", "内存"]),
        ("swap", ["swap"]),
        ("timezone", ["timezone", "服务器timezone"]),
        ("path", ["path", "项目目录"]),
        ("version", ["version", "核验版本"]),
        ("branch", ["branch", "分支"]),
        ("port", ["port", "本机端口", "监听端口"]),
        ("endpoint", ["endpoint", "外部入口", "公网入口"]),
    ]

    seen: set[str] = set()
    items: list[dict[str, str]] = []

    for raw_key, raw_value in pairs:
        normalized_key = _normalize_label(raw_key)
        normalized_value = " ".join(raw_value.split())
        label = raw_key.strip()
        for canonical, candidates in field_order:
            if canonical in seen:
                continue
            if any(_normalize_label(candidate) in normalized_key for candidate in candidates):
                items.append({"label": label, "value": normalized_value})
                seen.add(canonical)
                break

    if not items:
        return None

    summary = " · ".join(f"{item['label']}: {item['value']}" for item in items[:4])
    return {
        "state": "neutral",
        "summary": summary,
        "items": items,
        "source": "doc",
    }


def _classify_service_check(text: str) -> str:
    lowered = _normalize_label(text)
    if any(
        keyword in lowered
        for keyword in [
            "fail",
            "failed",
            "failure",
            "error",
            "异常",
            "inactive",
            "stopped",
            "down",
            "timeout",
            "denied",
            "oom",
        ]
    ):
        return "error"
    if any(
        keyword in lowered
        for keyword in [
            "warning",
            "attentionrequired",
            "attention",
            "risk",
            "风险",
            "需关注",
        ]
    ):
        return "warning"
    if any(
        keyword in lowered
        for keyword in [
            "pass",
            "healthy",
            "healthycheck",
            "ok",
            "active",
            "running",
            "ready",
            "通过",
            "正常",
            "alive",
            "http200",
        ]
    ):
        return "healthy"
    return "neutral"


def _service_check_items(folder: Path) -> dict[str, Any] | None:
    combined: list[str] = []
    for filename in ("SERVER_INFO.md", "README.md"):
        path = folder / filename
        if path.exists():
            combined.append(path.read_text(encoding="utf-8", errors="ignore"))
    if not combined:
        return None

    lines = "\n".join(combined).splitlines()
    capture: list[str] = []
    start_idx: int | None = None
    section_keywords = [
        "health",
        "health status",
        "current health",
        "current verified health",
        "verified health",
        "验证状态",
        "健康",
        "核验状态",
    ]
    for idx, raw in enumerate(lines):
        stripped = raw.strip()
        lowered = stripped.lower()
        if stripped.startswith("##") and any(keyword in lowered for keyword in section_keywords):
            start_idx = idx
            capture = [stripped]
            continue
        if start_idx is not None:
            if stripped.startswith("##") and idx > start_idx:
                break
            if stripped:
                capture.append(stripped)
            if len(capture) >= 14:
                break

    if len(capture) <= 1:
        return None

    items: list[dict[str, str]] = []
    for raw in capture[1:]:
        text = raw.lstrip("-* ").strip()
        text = re.sub(r"^\d+\.\s*", "", text)
        text = text.strip("`")
        if not text:
            continue
        if text.startswith("|") or text.startswith("##"):
            continue
        state = _classify_service_check(text)
        if state == "neutral":
            continue
        items.append({"label": text, "state": state})
        if len(items) >= 6:
            break

    if not items:
        return None

    summary = " · ".join(f"{item['state']}:{item['label']}" for item in items[:3])
    overall = "healthy"
    if any(item["state"] == "error" for item in items):
        overall = "error"
    elif any(item["state"] == "warning" for item in items):
        overall = "warning"

    return {
        "state": overall,
        "summary": summary,
        "items": items,
        "source": "doc",
    }


def _approx_memory_status() -> dict[str, Any]:
    total = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
    vm_stat = _run_command(["vm_stat"], timeout=10)
    page_size = 4096
    free_pages = inactive_pages = speculative_pages = 0
    for line in vm_stat["stdout"].splitlines():
        if "page size of" in line:
            try:
                page_size = int(line.split("page size of", 1)[1].split("bytes")[0].strip())
            except Exception:  # noqa: BLE001
                pass
        if line.startswith("Pages free:"):
            free_pages = int(line.split(":", 1)[1].strip().split(".")[0])
        if line.startswith("Pages inactive:"):
            inactive_pages = int(line.split(":", 1)[1].strip().split(".")[0])
        if line.startswith("Pages speculative:"):
            speculative_pages = int(line.split(":", 1)[1].strip().split(".")[0])
    available = (free_pages + inactive_pages + speculative_pages) * page_size
    available_percent = (available / total * 100) if total else 0.0
    return {
        "total_mb": round(total / 1024 / 1024),
        "available_mb": round(available / 1024 / 1024),
        "available_percent": round(available_percent, 1),
        "state": "healthy" if available_percent >= LOCAL_MEMORY_WARN_PERCENT else "warning",
        "vm_stat": _trim_output(vm_stat["stdout"], 12),
    }


def _disk_status() -> dict[str, Any]:
    usage = shutil.disk_usage("/")
    used_percent = round((usage.used / usage.total) * 100, 1) if usage.total else 0.0
    return {
        "total_gb": round(usage.total / 1024 / 1024 / 1024, 1),
        "used_gb": round(usage.used / 1024 / 1024 / 1024, 1),
        "free_gb": round(usage.free / 1024 / 1024 / 1024, 1),
        "used_percent": used_percent,
        "state": "healthy" if used_percent < LOCAL_DISK_WARN_PERCENT else "warning",
    }


def _mysql_status() -> dict[str, Any]:
    db_status = inspect_database()
    if db_status.online:
        return {
            "state": "healthy",
            "version": db_status.version,
            "user_count": db_status.user_count,
            "database_count": db_status.database_count,
        }
    return {"state": "error", "error": db_status.error}


def collect_local_snapshot() -> dict[str, Any]:
    hostname = socket.gethostname()
    fqdn = socket.getfqdn()
    if "arpa" in fqdn or fqdn.count(".") > 4:
        fqdn = hostname
    os_version = platform.mac_ver()[0] or platform.release()
    uptime = _run_command(["uptime"], timeout=10)
    load_averages = None
    try:
        load_averages = [round(value, 2) for value in os.getloadavg()]
    except OSError:
        load_averages = None

    memory = _approx_memory_status()
    disk = _disk_status()
    mysql = _mysql_status()

    checks = {
        "disk": disk["state"],
        "memory": memory["state"],
        "mysql": mysql["state"],
    }
    overall = "healthy"
    if "error" in checks.values():
        overall = "error"
    elif "warning" in checks.values():
        overall = "warning"

    return {
        "hostname": hostname,
        "fqdn": fqdn,
        "os": platform.system(),
        "os_version": os_version,
        "kernel": platform.release(),
        "architecture": platform.machine(),
        "cpu_count": os.cpu_count(),
        "load_averages": load_averages,
        "uptime": uptime["stdout"],
        "memory": memory,
        "disk": disk,
        "mysql": mysql,
        "health": overall,
        "collected_at": datetime.now().isoformat(timespec="seconds"),
    }


def _read_head(path: Path, line_limit: int = 12) -> str:
    if not path.exists():
        return ""
    lines: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.rstrip()
        if line or lines:
            lines.append(line)
        if len(lines) >= line_limit:
            break
    return "\n".join(lines).strip()


def _service_doc_excerpt(folder: Path) -> str:
    parts: list[str] = []
    for filename in ("README.md", "SERVER_INFO.md"):
        path = folder / filename
        if path.exists():
            excerpt = _read_head(path, 14)
            if excerpt:
                parts.append(excerpt)
    return "\n\n".join(parts)


def _service_doc_health(folder: Path) -> dict[str, Any] | None:
    combined = []
    for filename in ("SERVER_INFO.md", "README.md"):
        path = folder / filename
        if path.exists():
            combined.append(path.read_text(encoding="utf-8", errors="ignore"))
    if not combined:
        return None
    text = "\n".join(combined)
    lines = text.splitlines()
    capture: list[str] = []
    start = None
    for idx, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped.startswith("##") and (
            "health" in stripped.lower()
            or "验证" in stripped
            or "健康" in stripped
            or "current" in stripped.lower()
            or "current health" in stripped.lower()
            or "current verified health" in stripped.lower()
            or "2026-07-31" in stripped
        ):
            start = idx
            capture = [stripped]
            continue
        if start is not None:
            if stripped.startswith("##") and idx > start:
                break
            if stripped:
                capture.append(stripped)
            if len(capture) >= 10:
                break
    excerpt = "\n".join(capture).strip() if capture else _trim_output(text, 18)
    lowered = text.lower()
    if any(keyword in lowered for keyword in ["attention required", "warning", "fail", "failed", "异常", "风险"]):
        state = "warning"
    elif any(
        keyword in lowered
        for keyword in [
            "pass",
            "healthy",
            "healthy.",
            "healthy!",
            "http 200",
            ": active",
            " active",
            "通过",
            "正常",
        ]
    ):
        state = "healthy"
    else:
        state = "neutral"
    return {
        "state": state,
        "summary": _first_non_empty(excerpt.splitlines()),
        "output": excerpt,
        "source": "doc",
    }


def _script_command(folder: Path) -> tuple[Path | None, list[str] | None]:
    if folder.name == "new-ccsl":
        script = folder / "bin" / "health-check.sh"
        if script.exists():
            return script, ["all"]
    candidates = [
        ("health-check.sh", []),
        ("health-check.command", []),
        ("daily-check.sh", []),
    ]
    for name, args in candidates:
        script = folder / name
        if script.exists():
            return script, args
    return None, None


def _status_command(folder: Path) -> tuple[Path | None, list[str] | None]:
    if folder.name == "new-ccsl":
        script = folder / "bin" / "server-status.sh"
        if script.exists():
            return script, []
    candidates = [
        ("server-status.sh", []),
        ("status.sh", []),
        ("daily-check.sh", []),
    ]
    for name, args in candidates:
        script = folder / name
        if script.exists():
            return script, args
    return None, None


def _classify_health(exit_code: int, output: str) -> str:
    if exit_code == 0:
        if "ATTENTION REQUIRED" in output:
            return "warning"
        return "healthy"
    if exit_code == 2:
        return "warning"
    return "error"


def collect_service_snapshot(folder_name: str) -> dict[str, Any] | None:
    folder = SENS_SERVER_DIR / folder_name
    if not folder.exists():
        return None
    title = SERVICE_LABELS.get(folder_name, folder_name)
    readme = folder / "README.md"
    info = folder / "SERVER_INFO.md"
    doc_excerpt = _service_doc_excerpt(folder)
    device_result = _service_device_info(folder)
    health_result = _service_doc_health(folder)
    status_result = _service_doc_health(folder)
    checks_result = _service_check_items(folder)

    if ENABLE_REMOTE_CHECKS:
        health_script, health_args = _script_command(folder)
        status_script, status_args = _status_command(folder)
        if health_script:
            health_result = _run_command([str(health_script), *(health_args or [])], cwd=folder, timeout=60)
            health_result["state"] = _classify_health(
                int(health_result["returncode"]),
                health_result["output"],
            )
            health_result["summary"] = _first_non_empty(health_result["output"].splitlines())
            health_result["output"] = _trim_output(health_result["output"], 24)
            health_result["source"] = "script"
        if status_script:
            status_result = _run_command([str(status_script), *(status_args or [])], cwd=folder, timeout=60)
            status_result["state"] = _classify_health(
                int(status_result["returncode"]),
                status_result["output"],
            )
            status_result["summary"] = _first_non_empty(status_result["output"].splitlines())
            status_result["output"] = _trim_output(status_result["output"], 24)
            status_result["source"] = "script"

    facts = []
    if info.exists():
        facts.append(info.name)
    if readme.exists():
        facts.append(readme.name)
    facts.append("archived" if "backup" in folder_name else "active")

    return {
        "key": folder_name,
        "title": title,
        "path": str(folder),
        "readme": str(readme) if readme.exists() else None,
        "server_info": str(info) if info.exists() else None,
        "excerpt": doc_excerpt,
        "device": device_result,
        "checks": checks_result,
        "facts": facts,
        "health": health_result,
        "status": status_result,
        "archive": "backup" in folder_name,
        "source": "script" if ENABLE_REMOTE_CHECKS else "doc",
    }


def collect_dashboard_snapshot() -> dict[str, Any]:
    local = collect_local_snapshot()
    services: dict[str, dict[str, Any] | None] = {}

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(collect_service_snapshot, service_name): service_name
            for service_name in SERVICE_ORDER
        }
        for future in as_completed(futures):
            service_name = futures[future]
            services[service_name] = future.result()

    ordered_services = [services[name] for name in SERVICE_ORDER if services.get(name)]
    healthy_count = sum(1 for item in ordered_services if item and item["health"] and item["health"]["state"] == "healthy")
    warning_count = sum(
        1
        for item in ordered_services
        if item and item["health"] and item["health"]["state"] == "warning"
    )
    error_count = sum(
        1
        for item in ordered_services
        if item and item["health"] and item["health"]["state"] == "error"
    )
    archive_count = sum(1 for item in ordered_services if item and item["archive"])

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "local": local,
        "services": ordered_services,
        "summary": {
            "service_count": len(ordered_services),
            "healthy_count": healthy_count,
            "warning_count": warning_count,
            "error_count": error_count,
            "archive_count": archive_count,
        },
        "device_record_path": str(LOCAL_DEVICE_MD),
    }
