"""Local Jira requirement service. Run from this directory with uvicorn app:app."""
import base64
from collections import Counter
from contextlib import contextmanager
import csv
import hashlib
import hmac
import io
import json
import os
import re
from pathlib import Path
import sqlite3
import ssl
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parent
STATE = Path(os.environ.get("JIRA_SERVICE_STATE", ROOT / ".local"))
BASE = os.environ.get("JIRA_BASE_URL", "https://issue.cambodianexpress.com").rstrip("/")
app = FastAPI(title="Jira 需求服务", version="0.3.0")
service_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def authorize(x_api_key: str | None = Depends(service_key_header)):
    expected = os.environ.get("JIRA_SERVICE_API_KEY", "")
    if not expected:
        raise HTTPException(503, "服务访问密钥尚未配置")
    if not hmac.compare_digest((x_api_key or "").encode(), expected.encode()):
        raise HTTPException(401, "服务访问密钥不正确")


def jira(method: str, path: str, payload=None):
    user, password = os.environ.get("JIRA_USERNAME"), os.environ.get("JIRA_PASSWORD")
    if not user or not password:
        raise HTTPException(503, "Jira 账号凭据尚未配置")
    if urllib.parse.urlsplit(BASE).scheme != "https":
        raise HTTPException(503, "Jira 地址必须使用 HTTPS")
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    headers = {"Accept": "application/json", "Authorization": "Basic " + token}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    context = ssl.create_default_context()
    if Path("/etc/ssl/cert.pem").exists():
        context.load_verify_locations("/etc/ssl/cert.pem")
    req = urllib.request.Request(BASE + path, method=method, headers=headers,
                                 data=None if payload is None else json.dumps(payload).encode())
    try:
        with urllib.request.urlopen(req, context=context, timeout=30) as result:
            raw = result.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        # Return field validation errors only; never echo an HTML body or credentials.
        detail: dict[str, Any] = {"jira_status": error.code}
        if error.code == 400:
            try:
                body = json.loads(error.read())
                detail["fields"] = body.get("errors", {})
                detail["messages"] = body.get("errorMessages", [])
            except (ValueError, UnicodeError):
                pass
        raise HTTPException(error.code if error.code in (400, 401, 403, 404, 429) else 502, detail)
    except (OSError, ValueError) as error:
        raise HTTPException(502, "Jira 请求未完成；写入请求可能已生效，请先核对，勿自动重试") from error


def quote(value):
    return urllib.parse.quote(str(value), safe="")


def get_meta(project, issue_type=None):
    query = {"projectKeys": project, "expand": "projects.issuetypes.fields"}
    if issue_type:
        query["issuetypeIds"] = issue_type
    return jira("GET", "/rest/api/2/issue/createmeta?" + urllib.parse.urlencode(query))


class CreateRequest(BaseModel):
    project: str = Field(min_length=1, max_length=100)
    issue_type_id: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=255)
    description: str = ""
    assignee: str | None = None
    priority_id: str | None = None
    labels: list[str] = Field(default_factory=list)
    extra_fields: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


def create_fields(body):
    fields = {"project": {"key": body.project}, "issuetype": {"id": body.issue_type_id},
              "summary": body.summary, "description": body.description, "labels": body.labels}
    if body.assignee is not None:
        fields["assignee"] = {"name": body.assignee} if body.assignee else None
    if body.priority_id:
        fields["priority"] = {"id": body.priority_id}
    if set(body.extra_fields) & set(fields):
        raise HTTPException(422, "extra_fields 不可覆盖已有字段")
    fields.update(body.extra_fields)
    meta = get_meta(body.project, body.issue_type_id)
    projects = meta.get("projects", [])
    types = projects[0].get("issuetypes", []) if projects else []
    if len(types) != 1:
        raise HTTPException(403, "无法读取该项目/问题类型的创建字段")
    schema = types[0]["fields"]
    # Omit empty optional fields that are not on this project's create screen.
    fields = {key: value for key, value in fields.items()
              if key in schema or value not in ("", [], None)}
    missing = [key for key, spec in schema.items()
               if spec.get("required") and not spec.get("hasDefaultValue")
               and (key not in fields or fields[key] in ("", [], None))]
    unsupported = sorted(set(fields) - set(schema))
    if missing or unsupported:
        raise HTTPException(422, {"missing_required": missing, "unsupported": unsupported})
    return fields


@contextmanager
def database():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    db_path = STATE / "requests.sqlite3"
    db = sqlite3.connect(db_path, timeout=10)
    os.chmod(db_path, 0o600)
    db.execute("CREATE TABLE IF NOT EXISTS requests (key TEXT PRIMARY KEY, digest TEXT NOT NULL, "
               "state TEXT NOT NULL, issue_key TEXT, updated REAL NOT NULL)")
    db.commit()
    try:
        with db:
            yield db
    finally:
        db.close()


def claim(key, digest):
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT digest,state,issue_key FROM requests WHERE key=?", (key,)).fetchone()
        if row:
            if row[0] != digest:
                raise HTTPException(409, "此幂等键已用于不同内容")
            if row[1] == "created":
                return row[2]
            raise HTTPException(409, "此请求正在处理或结果待核对；先查询 Jira，勿换键重试")
        db.execute("INSERT INTO requests VALUES (?,?,?,NULL,?)", (key, digest, "pending", time.time()))
    return None


def finish(key, state, issue_key=None):
    with database() as db:
        db.execute("UPDATE requests SET state=?,issue_key=?,updated=? WHERE key=?",
                   (state, issue_key, time.time(), key))


def replay(key, digest):
    """Check a completed request before consulting state-dependent workflow metadata."""
    with database() as db:
        row = db.execute("SELECT digest,state,issue_key FROM requests WHERE key=?", (key,)).fetchone()
    if row is None:
        return None
    if row[0] != digest:
        raise HTTPException(409, "此幂等键已用于不同内容")
    if row[1] != "created":
        raise HTTPException(409, "此请求正在处理或结果待核对；先查询 Jira，勿换键重试")
    return row[2]


@app.get("/health")
def health():
    return {"status": "ok", "jira_configured": bool(os.environ.get("JIRA_USERNAME") and
            os.environ.get("JIRA_PASSWORD")), "service_key_configured": bool(os.environ.get("JIRA_SERVICE_API_KEY"))}


@app.get("/projects", dependencies=[Depends(authorize)])
def projects():
    return [{k: p[k] for k in ("id", "key", "name")} for p in jira("GET", "/rest/api/2/project")]


@app.get("/projects/{project}/metadata", dependencies=[Depends(authorize)])
def metadata(project: str, issue_type_id: str | None = None):
    return get_meta(project, issue_type_id)


@app.get("/fields", dependencies=[Depends(authorize)])
def fields():
    return jira("GET", "/rest/api/2/field")


@app.post("/requirements", dependencies=[Depends(authorize)])
def create(body: CreateRequest, idempotency_key: str | None = Header(default=None)):
    payload = {"fields": create_fields(body)}
    if body.dry_run:
        return {"submitted": False, "fields": payload["fields"],
                "note": "仅检查字段存在性和必填项；值、权限及工作流校验由 Jira 在提交时执行"}
    if not idempotency_key or len(idempotency_key) > 200:
        raise HTTPException(422, "实际创建需要长度 1–200 的 Idempotency-Key 请求头")
    # Hash the caller's intent, not Jira's changing field metadata.
    digest = hashlib.sha256(json.dumps(body.model_dump(exclude={"dry_run"}),
                                      sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    cached = claim(idempotency_key, digest)
    if cached:
        return {"key": cached, "url": BASE + "/browse/" + cached, "replayed": True}
    try:
        created = jira("POST", "/rest/api/2/issue", payload)
        issue_key = created["key"]
    except Exception:
        # Conservative even for a rejected request: explicit investigation before reuse.
        finish(idempotency_key, "unknown")
        raise
    finish(idempotency_key, "created", issue_key)
    try:
        verified = jira("GET", "/rest/api/2/issue/" + quote(issue_key) + "?fields=summary,status")
    except HTTPException:
        return {"key": issue_key, "url": BASE + "/browse/" + issue_key,
                "verified": False, "note": "Jira 已返回创建成功；读回失败，不应重新创建"}
    return {"key": issue_key, "url": BASE + "/browse/" + issue_key, "verified": True,
            "fields": verified["fields"]}


def issue_state(key):
    return jira("GET", "/rest/api/2/issue/" + quote(key) + "?fields=summary,status,resolution,assignee")


def issue_transitions(key):
    return jira("GET", "/rest/api/2/issue/" + quote(key) + "/transitions?expand=transitions.fields")


@app.get("/requirements/{issue_key}/transitions", dependencies=[Depends(authorize)])
def transitions(issue_key: str):
    return {"issue": issue_state(issue_key), **issue_transitions(issue_key)}


@app.get("/resolutions", dependencies=[Depends(authorize)])
def resolutions():
    return jira("GET", "/rest/api/2/resolution")


class CloseRequest(BaseModel):
    transition_id: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=10000)
    intent: str = Field(default="close", pattern="^(close|wont_do)$")
    resolution_id: str | None = None
    expected_status_id: str | None = None
    extra_fields: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = True


CANCEL_NAMES = {"won't do", "won't fix", "wont do", "wont fix", "cancelled", "canceled",
                "不做", "不予修复", "不会修复", "取消", "已取消"}


@app.post("/requirements/{issue_key}/close", dependencies=[Depends(authorize)])
def close(issue_key: str, body: CloseRequest, idempotency_key: str | None = Header(default=None)):
    """Explicit workflow transition, never delete or automatically mark cancelled work fixed."""
    issue_key = issue_key.upper()
    if not body.reason.strip():
        raise HTTPException(422, "必须提供关闭/不做的原因")
    token = None
    digest = hashlib.sha256(json.dumps({"issue": issue_key, **body.model_dump(exclude={"dry_run"})},
                                      sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if not body.dry_run:
        if not idempotency_key or len(idempotency_key) > 200:
            raise HTTPException(422, "实际转换需要 Idempotency-Key 请求头（1–200 字符）")
        if not body.expected_status_id:
            raise HTTPException(422, "实际转换需要 expected_status_id，防止误用过时的工作流状态")
        token = "transition:" + idempotency_key
        cached = replay(token, digest)
        if cached:
            return {"key": cached, "url": BASE + "/browse/" + cached, "replayed": True}
    current = issue_state(issue_key)
    status = current["fields"]["status"]
    if body.expected_status_id and body.expected_status_id != status["id"]:
        raise HTTPException(409, {"message": "需求状态已变化，请重新选择转换", "current_status": status})
    options = issue_transitions(issue_key).get("transitions", [])
    selected = next((t for t in options if t["id"] == body.transition_id), None)
    if selected is None:
        raise HTTPException(422, "该转换不在当前账号允许的工作流动作中")
    target = selected["to"]
    if target.get("statusCategory", {}).get("key") != "done":
        raise HTTPException(422, "关闭接口仅允许转入结束类别的状态")
    schema = selected.get("fields", {})
    fields = dict(body.extra_fields)
    if "resolution" in fields:
        raise HTTPException(422, "解决结果请使用 resolution_id，避免绕过不做语义检查")
    chosen_resolution = None
    if body.resolution_id:
        if "resolution" not in schema:
            raise HTTPException(422, "此转换不允许填写解决结果；需选择带解决结果字段的动作")
        catalog = jira("GET", "/rest/api/2/resolution")
        chosen_resolution = next((r for r in catalog if r["id"] == body.resolution_id), None)
        if not chosen_resolution:
            raise HTTPException(422, "解决结果 ID 不存在")
        allowed = schema["resolution"].get("allowedValues")
        if allowed is not None and not any(r.get("id") == body.resolution_id for r in allowed):
            raise HTTPException(422, "此转换不允许选择该解决结果")
        fields["resolution"] = {"id": body.resolution_id}
    if body.intent == "wont_do":
        if chosen_resolution:
            if chosen_resolution["name"].strip().lower() not in CANCEL_NAMES:
                raise HTTPException(422, "不做需求不能选择完成/已修复等解决结果")
        elif target["name"].strip().lower() not in CANCEL_NAMES:
            raise HTTPException(422, "不做需明确取消状态或不做的解决结果；不能只关闭并采用默认已修复结果")
    missing = [k for k, v in schema.items() if v.get("required") and not v.get("hasDefaultValue")
               and k != "comment" and (k not in fields or fields[k] in (None, "", []))]
    if missing or set(fields) - set(schema):
        raise HTTPException(422, {"missing_required": missing, "unsupported": sorted(set(fields) - set(schema))})
    payload = {"transition": {"id": body.transition_id}, "fields": fields,
               "update": {"comment": [{"add": {"body": ("不做原因：" if body.intent == "wont_do" else
                                                         "关闭原因：") + body.reason.strip()}}]}}
    if body.dry_run:
        return {"submitted": False, "key": issue_key, "current_status": status, "target_status": target,
                "resolution": chosen_resolution, "payload": payload,
                "note": "预检查不修改需求；工作流后置动作及最终解决结果需提交后读回确认"}
    cached = claim(token, digest)
    if cached:
        return {"key": cached, "url": BASE + "/browse/" + cached, "replayed": True}
    try:
        jira("POST", "/rest/api/2/issue/" + quote(issue_key) + "/transitions", payload)
    except Exception:
        finish(token, "unknown")
        raise
    finish(token, "created", issue_key)
    try:
        verified = issue_state(issue_key)
    except HTTPException:
        return {"key": issue_key, "submitted": True, "verified": False,
                "note": "Jira 已接受转换，读回失败；先核对状态和原因备注，不要重试"}
    actual = verified["fields"]
    matches = actual["status"]["id"] == target["id"]
    if body.resolution_id:
        matches = matches and (actual.get("resolution") or {}).get("id") == body.resolution_id
    return {"key": issue_key, "submitted": True, "verified": matches, "fields": actual,
            "note": "已核对目标状态及显式解决结果" if matches else "实际状态/解决结果与请求不符，请人工核对，勿重试"}


class QueryRequest(BaseModel):
    jql: str = Field(min_length=1, max_length=10000)
    limit: int = Field(default=1000, ge=1, le=10000)
    fields: list[str] = Field(default_factory=lambda: ["summary", "description", "project", "issuetype",
        "status", "priority", "assignee", "reporter", "created", "updated", "labels"])


def search(body):
    issues = []
    total = 0
    jql = body.jql if re.search(r"\border\s+by\b", body.jql, re.I) else body.jql + " ORDER BY key ASC"
    while len(issues) < body.limit:
        page = jira("POST", "/rest/api/2/search", {"jql": jql, "startAt": len(issues),
                    "maxResults": min(100, body.limit - len(issues)), "fields": body.fields})
        total = page["total"]
        batch = page.get("issues", [])
        issues.extend(batch)
        if len(issues) >= total:
            break
        if not batch:
            raise HTTPException(502, "Jira 分页提前结束；未返回不完整导出")
    return issues, total


def summary(issues):
    result = {}
    for field in ("project", "status", "issuetype", "assignee"):
        result[field] = dict(Counter((i["fields"].get(field) or {}).get("displayName") or
                                    (i["fields"].get(field) or {}).get("name") or "未设置" for i in issues))
    return result


@app.post("/requirements/query", dependencies=[Depends(authorize)])
def query(body: QueryRequest):
    issues, total = search(body)
    return {"jira_total": total, "returned": len(issues), "truncated": len(issues) < total,
            "summary_scope": "returned_issues", "summary": summary(issues), "issues": issues}


class ExportRequest(QueryRequest):
    all_fields: bool = False
    column_names: dict[str, str] = Field(default_factory=dict)


def csv_value(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    else:
        value = str(value)
    # Prevent spreadsheet formula execution, including leading control characters.
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        value = "'" + value
    return value


def render_csv(issues, columns, names):
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow([csv_value(names.get(c, c)) for c in columns])
    for issue in issues:
        writer.writerow([csv_value(issue["key"] if col == "key" else issue["fields"].get(col))
                         for col in columns])
    return b"\xef\xbb\xbf" + out.getvalue().encode("utf-8")


@app.post("/requirements/export", dependencies=[Depends(authorize)])
def export(body: ExportRequest):
    names = dict(body.column_names)
    if body.all_fields:
        catalog = jira("GET", "/rest/api/2/field")
        field_ids = [f["id"] for f in catalog if f["id"] != "key"]
        # Include all known fields, even on an empty result or if all values are null.
        for field in catalog:
            names.setdefault(field["id"], f'{field["name"]} [{field["id"]}]')
        body.fields = ["*all"]
    else:
        if any(f.startswith("*") for f in body.fields):
            raise HTTPException(422, "通配字段请使用 all_fields=true")
        field_ids = body.fields
    issues, total = search(body)
    if len(issues) < total:
        raise HTTPException(422, {"message": "结果超过 limit，请缩小查询范围或提高 limit；拒绝导出截断数据",
                                  "jira_total": total, "limit": body.limit})
    if body.all_fields:
        field_ids = list(dict.fromkeys(field_ids + sorted({k for i in issues for k in i["fields"]})))
    columns = list(dict.fromkeys(["key"] + field_ids))
    return Response(render_csv(issues, columns, names), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="jira-requirements.csv"',
                             "X-Export-Count": str(len(issues)), "Cache-Control": "no-store"})


# A focused report avoids retrieving descriptions, comments and unrelated custom fields.
from reporting import ResolvedReportRequest, REPORT_FIELDS, REPORT_COLUMNS, REPORT_NAMES, report_window, report_rows


@app.post("/reports/resolved/export", dependencies=[Depends(authorize)])
def resolved_report(body: ResolvedReportRequest):
    account = jira("GET", "/rest/api/2/myself")
    start, end, zone, jql = report_window(body, account.get("timeZone"))
    issues, total = search(QueryRequest(jql=jql, fields=REPORT_FIELDS, limit=body.limit))
    if len(issues) != total:
        raise HTTPException(422, {"message": "结果超限，拒绝导出截断报表；请缩小项目或日期范围", "jira_total": total})
    rows = report_rows(issues, start, end, zone)
    return Response(render_csv(rows, REPORT_COLUMNS, REPORT_NAMES), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="jira-resolved-{body.start_date}-{body.end_date}.csv"',
                             "X-Export-Count": str(len(rows)), "X-Report-Timezone": body.timezone,
                             "Cache-Control": "no-store"})
