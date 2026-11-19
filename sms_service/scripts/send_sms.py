#!/usr/bin/env python3
"""PlasGate single/batch SMS; CLI defaults to offline dry-run."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
from urllib import error, parse, request

BASE_URL = "https://cloudapi.plasgate.com"
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config.local.json"


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def endpoint(base_url, batch=False):
    parts = parse.urlsplit(base_url)
    if (parts.scheme != "https" or not parts.hostname or parts.username
            or parts.password or parts.query or parts.fragment
            or parts.path not in ("", "/")):
        raise ValueError("base-url 必须为不含路径、认证或查询串的 HTTPS 域名")
    return base_url.rstrip("/") + ("/rest/batch-send" if batch else "/rest/send")


def validate_payload(payload, batch=False):
    def text(value):
        return isinstance(value, str) and bool(value.strip())

    def phone(value):
        return isinstance(value, str) and re.fullmatch(r"[0-9]+", value)

    if not isinstance(payload, dict):
        raise ValueError("请求体必须是 JSON 对象")
    if batch:
        globals_ = payload.get("globals")
        if not isinstance(globals_, dict) or not text(globals_.get("sender")):
            raise ValueError("globals.sender 必须为非空文本")
        messages = payload.get("messages")
        if not isinstance(messages, list) or not messages:
            raise ValueError("messages 必须为非空数组")
        if "batch_config" in payload and not isinstance(payload["batch_config"], dict):
            raise ValueError("batch_config 必须为对象")
    else:
        if not text(payload.get("sender")):
            raise ValueError("sender 必须为非空文本")
        messages = [payload]
    count = 0
    for message in messages:
        if not isinstance(message, dict) or not text(message.get("content")):
            raise ValueError("每条短信的 content 必须为非空文本")
        recipients = message.get("to") if batch else [message.get("to")]
        if not isinstance(recipients, list) or not recipients or not all(map(phone, recipients)):
            raise ValueError("to 必须为纯数字号码字符串；批发时为非空字符串数组")
        count += len(recipients)
    return count


def load_credentials(path):
    values = {}
    if not (os.environ.get("PLASGATE_PRIVATE_KEY") and os.environ.get("PLASGATE_X_SECRET")):
        # O_NOFOLLOW avoids following a credential symlink; check the opened file.
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600
                    or info.st_uid != os.getuid()):
                raise ValueError("凭据必须为当前用户所有的普通文件，权限为 600")
            values = json.load(stream)
        if not isinstance(values, dict):
            raise ValueError("凭据文件必须为 JSON 对象")
    credentials = {
        "private_key": os.environ.get("PLASGATE_PRIVATE_KEY") or values.get("private_key"),
        "X-Secret": os.environ.get("PLASGATE_X_SECRET") or values.get("X-Secret"),
    }
    for value in credentials.values():
        if not isinstance(value, str) or not value.strip() or "\r" in value or "\n" in value:
            raise ValueError("请配置有效的 private_key 和 X-Secret")
    return credentials


def send_request(payload, credentials, batch=False, base_url=BASE_URL, timeout=20):
    """Send exactly once. Returns HTTP status and raw bytes; never logs credentials."""
    validate_payload(payload, batch)
    url = endpoint(base_url, batch) + "?" + parse.urlencode({"private_key": credentials["private_key"]})
    req = request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                          headers={"X-Secret": credentials["X-Secret"],
                                   "Content-Type": "application/json", "Accept": "application/json"},
                          method="POST")
    opener = request.build_opener(NoRedirect())
    try:
        with opener.open(req, timeout=timeout) as response:
            return response.status, response.read()
    except error.HTTPError as exc:
        with exc:
            return exc.code, exc.read()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--batch", action="store_true")
    parser.add_argument("--apply", action="store_true", help="实际发送，可能产生费用")
    parser.add_argument("--base-url", default=os.environ.get("PLASGATE_BASE_URL", BASE_URL))
    parser.add_argument("--timeout", type=float, default=20)
    args = parser.parse_args(argv)
    try:
        endpoint(args.base_url, args.batch)
        if not math.isfinite(args.timeout) or args.timeout <= 0:
            raise ValueError("timeout 必须为有限正数")
        payload = json.loads(args.payload.read_text(encoding="utf-8"))
        count = validate_payload(payload, args.batch)
        if not args.apply:
            result = {"status": "dry_run", "mode": "batch" if args.batch else "single",
                      "recipient_count": count, "network_called": False}
        else:
            credentials = load_credentials(args.config)
            status, _ = send_request(payload, credentials, args.batch, args.base_url, args.timeout)
            result = {"status": "http_response_received", "http_status": status,
                      "business_status": "unverified", "delivery_status": "unverified"}
            print(json.dumps(result, ensure_ascii=False))
            return 0 if 200 <= status < 300 else 1
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, error.URLError, KeyError, TypeError):
        # Exceptions can contain the credential-bearing URL or remote response.
        print(json.dumps({"status": "error", "message": "配置、输入或网络执行失败；检查文件、权限、参数与连接。发送结果不明时先查交易报告，不要直接重试。"}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
