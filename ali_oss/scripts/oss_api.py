#!/usr/bin/env python3
"""Small OSS REST V4 client. Standard library only; no browser credentials."""
import base64
import datetime as dt
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import ssl
import stat
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


class OSSError(Exception):
    def __init__(self, code, status=None, request_id=None):
        self.code, self.status, self.request_id = code, status, request_id
        super().__init__(code)

    def as_dict(self):
        return {"error": self.code, "status": self.status, "request_id": self.request_id}


def load_credentials(path=None):
    """Explicit private JSON file or environment; never fall back to another identity."""
    if path:
        path = Path(path).expanduser()
        info = path.lstat()
        parent = path.parent.lstat()
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_mode & 0o077 or not stat.S_ISDIR(parent.st_mode)
                or parent.st_uid != os.geteuid() or parent.st_mode & 0o077
                or info.st_size > 65536):
            raise OSSError("credential_file_requires_private_owner_0600_parent_0700")
        try:
            credentials = json.loads(path.read_text())
        except (ValueError, UnicodeError):
            raise OSSError("invalid_credential_json") from None
    else:
        credentials = {
            "access_key_id": os.getenv("OSS_ACCESS_KEY_ID"),
            "access_key_secret": os.getenv("OSS_ACCESS_KEY_SECRET"),
            "security_token": os.getenv("OSS_SESSION_TOKEN"),
        }
    if not isinstance(credentials, dict):
        raise OSSError("invalid_credentials")
    for key in ("access_key_id", "access_key_secret"):
        value = credentials.get(key)
        if (not isinstance(value, str) or not value.strip()
                or value.startswith(("<", "${")) or "REPLACE_WITH" in value.upper()):
            raise OSSError("missing_or_placeholder_credentials")
    token = credentials.get("security_token")
    if token is not None and (not isinstance(token, str) or not token.strip()):
        raise OSSError("invalid_security_token")
    return credentials


def encode(value, safe=""):
    return urllib.parse.quote(str(value), safe=safe, encoding="utf-8")


def query_string(params):
    pairs = sorted((encode(k), None if v is None else encode(v))
                   for k, v in params.items())
    return "&".join(k if v is None else k + "=" + v for k, v in pairs)


def canonical_request(method, bucket, key, params, headers, additional=()):
    uri = "/" + (bucket + "/" if bucket else "") + key
    selected = {k.lower(): str(v).strip() for k, v in headers.items()
                if k.lower().startswith("x-oss-")
                or k.lower() in ("content-type", "content-md5", *additional)}
    lines = "".join(k + ":" + selected[k] + "\n" for k in sorted(selected))
    return "\n".join((method, encode(uri, safe="/"), query_string(params),
                       lines, ";".join(sorted(additional)), "UNSIGNED-PAYLOAD"))


def signing_key(secret, date, region):
    value = ("aliyun_v4" + secret).encode()
    for part in (date, region, "oss", "aliyun_v4_request"):
        value = hmac.new(value, part.encode(), hashlib.sha256).digest()
    return value


def sign(method, region, bucket, key, params, headers, credentials, timestamp=None):
    timestamp = timestamp or dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    headers = {k.lower(): v for k, v in headers.items()}
    headers.update({"x-oss-date": timestamp, "x-oss-content-sha256": "UNSIGNED-PAYLOAD"})
    if credentials.get("security_token"):
        headers["x-oss-security-token"] = credentials["security_token"]
    scope = timestamp[:8] + "/" + region + "/oss/aliyun_v4_request"
    canonical = canonical_request(method, bucket, key, params, headers)
    to_sign = "\n".join(("OSS4-HMAC-SHA256", timestamp, scope,
                          hashlib.sha256(canonical.encode()).hexdigest()))
    signature = hmac.new(signing_key(credentials["access_key_secret"], timestamp[:8], region),
                         to_sign.encode(), hashlib.sha256).hexdigest()
    headers["authorization"] = ("OSS4-HMAC-SHA256 Credential=" + credentials["access_key_id"]
                                + "/" + scope + ",Signature=" + signature)
    return headers


def parse_xml(body):
    # No DTD/entities, and responses are bounded by the transport.
    if b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise OSSError("xml_declarations_not_allowed")
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        raise OSSError("invalid_xml") from None
    for element in root.iter():
        element.tag = element.tag.rsplit("}", 1)[-1]
    return root


def xml_value(node):
    if not len(node):
        return node.text or ""
    result = {}
    for child in node:
        result.setdefault(child.tag, []).append(xml_value(child))
    return {key: values[0] if len(values) == 1 else values for key, values in result.items()}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OSSClient:
    def __init__(self, region, credentials, bucket="", timeout=20):
        if not re.fullmatch(r"[a-z]{2}(?:-[a-z0-9]+)+", region):
            raise OSSError("invalid_region")
        if bucket and not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", bucket):
            raise OSSError("invalid_bucket")
        self.region, self.credentials, self.bucket = region, credentials, bucket
        self.timeout = timeout
        self.endpoint = "https://" + (bucket + "." if bucket else "") + "oss-" + region + ".aliyuncs.com"
        # Never forward authentication on redirects. Ignore ambient proxy settings.
        cafile = os.getenv("OSS_CA_BUNDLE")
        if not cafile and ssl.get_default_verify_paths().cafile is None and Path("/etc/ssl/cert.pem").is_file():
            cafile = "/etc/ssl/cert.pem"
        context = ssl.create_default_context(cafile=cafile)
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                                                  urllib.request.HTTPSHandler(context=context))

    def request(self, method="GET", key="", params=None, body=None, headers=None,
                max_bytes=2 * 1024 * 1024):
        params, headers = params or {}, dict(headers or {})
        if body is not None:
            headers["Content-MD5"] = base64.b64encode(hashlib.md5(body).digest()).decode()
            headers.setdefault("Content-Type", "application/octet-stream")
        signed = sign(method, self.region, self.bucket, key, params, headers, self.credentials)
        url = self.endpoint + "/" + encode(key, safe="/")
        if params:
            url += "?" + query_string(params)
        request = urllib.request.Request(url, data=body, headers=signed, method=method)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise OSSError("response_too_large")
                # Do not print arbitrary object metadata or user-defined headers.
                safe = {k.lower(): v for k, v in response.headers.items()
                        if k.lower() in {"etag", "content-length", "content-type", "last-modified",
                                         "x-oss-request-id", "x-oss-version-id"}}
                return {"status": response.status, "headers": safe, "body": data}
        except urllib.error.HTTPError as exc:
            code = "http_error"
            try:
                code = parse_xml(exc.read(65536)).findtext("Code") or code
            except OSSError:
                pass
            # Never return server Message, StringToSign, Request, URL or credentials.
            code = code if re.fullmatch(r"[A-Za-z0-9_]+", code) else "http_error"
            raise OSSError(code, exc.code, exc.headers.get("x-oss-request-id")) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise OSSError("network_or_tls_error") from None


def public_result(result):
    output = {"status": result["status"], "headers": result["headers"]}
    if result["body"]:
        if result["body"].lstrip().startswith(b"<"):
            root = parse_xml(result["body"])
            output["data"] = {root.tag: xml_value(root)}
        else:
            try:
                output["data"] = json.loads(result["body"])
            except (ValueError, UnicodeError):
                raise OSSError("unexpected_non_configuration_response") from None
    return output
