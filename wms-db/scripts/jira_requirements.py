#!/usr/bin/env python3
"""Jira Server REST helper. Reads by default; create requires --submit."""
import argparse
import base64
import collections
import json
import os
from pathlib import Path
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request


BASE = "https://issue.cambodianexpress.com"


def request(method, path, data=None):
    headers = {"Accept": "application/json"}
    user, password = os.getenv("JIRA_USERNAME"), os.getenv("JIRA_PASSWORD")
    if user and password:
        value = base64.b64encode(f"{user}:{password}".encode()).decode()
        headers["Authorization"] = "Basic " + value
    if data is not None:
        headers["Content-Type"] = "application/json"
    context = ssl.create_default_context()
    # macOS system bundle; retain verification, never use an insecure context.
    if Path("/etc/ssl/cert.pem").exists():
        context.load_verify_locations("/etc/ssl/cert.pem")
    req = urllib.request.Request(BASE + path, headers=headers, method=method,
                                 data=None if data is None else json.dumps(data).encode())
    with urllib.request.urlopen(req, context=context, timeout=30) as response:
        return json.load(response)


def metadata(project, issue_type=None):
    query = {"projectKeys": project, "expand": "projects.issuetypes.fields"}
    if issue_type:
        query["issuetypeIds"] = issue_type
    return request("GET", "/rest/api/2/issue/createmeta?" + urllib.parse.urlencode(query))


def export(jql, output):
    issues = []
    while True:
        page = request("POST", "/rest/api/2/search", {
            "jql": jql, "startAt": len(issues), "maxResults": 100,
            "fields": ["summary", "description", "project", "issuetype", "status",
                       "priority", "assignee", "reporter", "created", "updated", "labels"],
        })
        batch = page.get("issues", [])
        issues.extend(batch)
        if len(issues) >= page["total"]:
            break
        if not batch:
            raise ValueError("分页提前结束，未导出完整结果")
    counts = collections.Counter(i["fields"]["status"]["name"] for i in issues)
    result = {"jql": jql, "count": len(issues), "status_counts": dict(counts), "issues": issues}
    # Exclusive creation prevents accidental overwrite of an existing export.
    with Path(output).open("x", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    print(json.dumps({"count": len(issues), "status_counts": dict(counts), "output": output}, ensure_ascii=False))


def create(path, submit):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    fields = payload["fields"]
    project, issue_type = fields["project"]["key"], fields["issuetype"]["id"]
    meta = metadata(project, issue_type)
    projects = meta.get("projects", [])
    types = projects[0].get("issuetypes", []) if projects else []
    if len(types) != 1:
        raise ValueError("无法读取目标项目/问题类型的创建字段，请检查账号权限")
    schema = types[0]["fields"]
    missing = [key for key, value in schema.items()
               if value.get("required") and not value.get("hasDefaultValue")
               and (key not in fields or fields[key] in (None, "", []))]
    unknown = set(fields) - set(schema)
    if missing or unknown:
        raise ValueError(f"必填字段缺失: {missing}; 创建页面不支持字段: {sorted(unknown)}")
    if set(payload) - {"fields"}:
        raise ValueError("仅接受 fields，避免未校验的额外操作")
    if not submit:
        print(json.dumps({"submitted": False, "project": project, "issue_type": issue_type,
                          "summary": fields["summary"], "validation": "本地字段检查通过；提交时仍由 Jira 校验字段值和权限"}, ensure_ascii=False))
        return
    created = request("POST", "/rest/api/2/issue", payload)
    # Do not retry creates: a network failure may occur after Jira has committed.
    print(json.dumps({"created": created["key"], "url": BASE + "/browse/" + created["key"]}, ensure_ascii=False), flush=True)
    verified = request("GET", "/rest/api/2/issue/" + urllib.parse.quote(created["key"]) + "?fields=summary,status")
    print(json.dumps({"verified": verified["key"], "fields": verified["fields"]}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("info")
    commands.add_parser("projects")
    meta = commands.add_parser("metadata")
    meta.add_argument("project")
    meta.add_argument("--issue-type")
    exp = commands.add_parser("export")
    exp.add_argument("--jql", required=True, help="使用带 ORDER BY 的稳定排序查询")
    exp.add_argument("--output", required=True, help="新建本地 JSON 文件")
    new = commands.add_parser("create")
    new.add_argument("payload", help="含 fields 的 JSON；project.key 和 issuetype.id 必填")
    new.add_argument("--submit", action="store_true", help="明确执行 Jira 创建；默认仅检查字段")
    args = parser.parse_args()
    if args.command == "info":
        data = request("GET", "/rest/api/2/serverInfo")
        print(json.dumps({k: data.get(k) for k in ("version", "deploymentType", "baseUrl")}, ensure_ascii=False))
    else:
        request("GET", "/rest/api/2/myself")
        if args.command == "projects":
            data = request("GET", "/rest/api/2/project")
            print(json.dumps([{k: p[k] for k in ("id", "key", "name")} for p in data], ensure_ascii=False))
        elif args.command == "metadata":
            print(json.dumps(metadata(args.project, args.issue_type), ensure_ascii=False, indent=2))
        elif args.command == "export":
            export(args.jql, args.output)
        elif args.command == "create":
            create(args.payload, args.submit)


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as error:
        print(f"Jira HTTP {error.code}；检查认证、权限和请求字段。创建请求失败后应先查询，避免重复提交。", file=sys.stderr)
        sys.exit(2)
    except (ValueError, KeyError, OSError, urllib.error.URLError) as error:
        print(f"操作未完成 ({type(error).__name__})；检查输入、网络和本地文件。创建请求未自动重试。", file=sys.stderr)
        sys.exit(1)
