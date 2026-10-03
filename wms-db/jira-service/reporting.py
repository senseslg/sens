"""Narrow resolved-issue CSV report; dates are half-open in the requested timezone."""
from datetime import date, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException
from pydantic import BaseModel, Field

REPORT_FIELDS = ["summary", "issuetype", "assignee", "resolutiondate", "reporter", "created", "project"]
REPORT_COLUMNS = ["key"] + REPORT_FIELDS
REPORT_NAMES = dict(zip(REPORT_COLUMNS, ["问题关键字", "概要", "问题类型", "经办人", "已解决", "报告人", "创建时间", "项目名称"]))


class ResolvedReportRequest(BaseModel):
    start_date: date
    end_date: date
    timezone: str = "Asia/Phnom_Penh"
    projects: list[str] = Field(default_factory=list)
    limit: int = Field(default=10000, ge=1, le=10000)


def report_window(body, account_timezone):
    if body.end_date <= body.start_date:
        raise HTTPException(422, "end_date 必须晚于 start_date（不包含结束日）")
    try:
        zone = ZoneInfo(body.timezone)
        account_zone = ZoneInfo(account_timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise HTTPException(422, "报表或 Jira 账号时区无效，无法可靠确定筛选边界")
    start = datetime.combine(body.start_date, time.min, zone)
    end = datetime.combine(body.end_date, time.min, zone)
    # JQL timestamps are interpreted in the authenticated Jira user's timezone.
    lo = start.astimezone(account_zone).strftime("%Y-%m-%d %H:%M")
    hi = end.astimezone(account_zone).strftime("%Y-%m-%d %H:%M")
    jql = f'resolved >= "{lo}" AND resolved < "{hi}"'
    if body.projects:
        import re
        if any(not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", p) for p in body.projects):
            raise HTTPException(422, "项目必须是合法项目代号")
        jql += " AND project IN (" + ",".join(body.projects) + ")"
    return start, end, zone, jql + " ORDER BY resolved ASC, key ASC"


def parse_timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone missing")
        return parsed
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(502, "Jira 返回缺失或无时区的日期，已拒绝生成不可靠报表")


def report_rows(issues, start, end, zone):
    rows = []
    seen = set()
    for issue in issues:
        if issue["key"] in seen:
            raise HTTPException(502, "分页出现重复问题，请重新导出")
        seen.add(issue["key"])
        fields = issue["fields"]
        resolved = parse_timestamp(fields.get("resolutiondate"))
        if not start <= resolved < end:
            raise HTTPException(502, "结果包含筛选范围之外的解决日期，请核对时区或重新查询")
        row = {"summary": fields.get("summary"),
               "issuetype": (fields.get("issuetype") or {}).get("name", ""),
               # Jira Server native CSV uses usernames rather than API user JSON.
               "assignee": (fields.get("assignee") or {}).get("name", ""),
               "reporter": (fields.get("reporter") or {}).get("name", ""),
               "project": (fields.get("project") or {}).get("name", ""),
               "resolutiondate": resolved.astimezone(zone).strftime("%Y-%m-%d %H:%M:%S"),
               "created": parse_timestamp(fields.get("created")).astimezone(zone).strftime("%Y-%m-%d %H:%M:%S")}
        rows.append({"key": issue["key"], "fields": row})
    return rows
