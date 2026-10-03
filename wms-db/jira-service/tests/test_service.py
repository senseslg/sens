import csv
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, str(Path(__file__).parents[1]))

spec = importlib.util.spec_from_file_location("service", Path(__file__).parents[1] / "app.py")
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.state = patch.object(service, "STATE", Path(self.directory.name))
        self.state.start()
        self.env = patch.dict(os.environ, {"JIRA_SERVICE_API_KEY": "test-key"})
        self.env.start()
        self.client = TestClient(service.app)
        self.headers = {"X-API-Key": "test-key", "Idempotency-Key": "test-request"}
        self.body = {"project": "TEST", "issue_type_id": "1", "summary": "需求", "dry_run": False}
        self.meta = {"projects": [{"issuetypes": [{"fields": {
            "project": {"required": True}, "issuetype": {"required": True},
            "summary": {"required": True}, "description": {}, "labels": {}}}]}]}

    def tearDown(self):
        self.env.stop()
        self.state.stop()
        self.directory.cleanup()

    def fake_jira(self, method, path, data=None):
        if "createmeta" in path:
            return self.meta
        if method == "POST" and path == "/rest/api/2/issue":
            return {"key": "TEST-1"}
        return {"key": "TEST-1", "fields": {"summary": "需求", "status": {"name": "待办"}}}

    def test_authentication_required(self):
        with patch.object(service, "jira") as upstream:
            self.assertEqual(self.client.get("/projects").status_code, 401)
            upstream.assert_not_called()

    def test_preview_never_creates(self):
        with patch.object(service, "jira", side_effect=self.fake_jira) as upstream:
            body = dict(self.body, dry_run=True)
            response = self.client.post("/requirements", json=body, headers=self.headers)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()["submitted"])
            self.assertTrue(all(call.args[0] == "GET" for call in upstream.call_args_list))

    def test_required_custom_field_blocks_submission(self):
        self.meta["projects"][0]["issuetypes"][0]["fields"]["customfield_1"] = {"required": True}
        with patch.object(service, "jira", side_effect=self.fake_jira) as upstream:
            response = self.client.post("/requirements", json=self.body, headers=self.headers)
            self.assertEqual(response.status_code, 422)
            self.assertEqual(upstream.call_count, 1)

    def test_replay_and_conflicting_payload(self):
        with patch.object(service, "jira", side_effect=self.fake_jira) as upstream:
            first = self.client.post("/requirements", json=self.body, headers=self.headers)
            second = self.client.post("/requirements", json=self.body, headers=self.headers)
            self.assertTrue(first.json()["verified"])
            self.assertTrue(second.json()["replayed"])
            creates = [c for c in upstream.call_args_list if c.args[:2] == ("POST", "/rest/api/2/issue")]
            self.assertEqual(len(creates), 1)
            conflict = self.client.post("/requirements", json=dict(self.body, summary="另一条"), headers=self.headers)
            self.assertEqual(conflict.status_code, 409)

    def test_uncertain_create_is_not_retried(self):
        def upstream(method, path, data=None):
            if "createmeta" in path:
                return self.meta
            raise HTTPException(502, "timeout")
        with patch.object(service, "jira", side_effect=upstream) as mock:
            self.assertEqual(self.client.post("/requirements", json=self.body, headers=self.headers).status_code, 502)
            self.assertEqual(self.client.post("/requirements", json=self.body, headers=self.headers).status_code, 409)
            self.assertEqual(sum(c.args[0] == "POST" for c in mock.call_args_list), 1)

    def test_readback_failure_still_returns_created_key(self):
        def upstream(method, path, data=None):
            if path.startswith("/rest/api/2/issue/TEST"):
                raise HTTPException(502, "timeout")
            return self.fake_jira(method, path, data)
        with patch.object(service, "jira", side_effect=upstream):
            response = self.client.post("/requirements", json=self.body, headers=self.headers)
            self.assertEqual(response.json()["key"], "TEST-1")
            self.assertFalse(response.json()["verified"])

    def test_pagination_and_truncation(self):
        def upstream(method, path, data=None):
            start, size = data["startAt"], data["maxResults"]
            self.assertIn("ORDER BY key ASC", data["jql"])
            return {"total": 103, "issues": [{"key": f"TEST-{n}", "fields": {"summary": str(n)}}
                    for n in range(start, min(start + size, 103))]}
        with patch.object(service, "jira", side_effect=upstream):
            full = self.client.post("/requirements/query", json={"jql": "project=TEST"}, headers=self.headers)
            self.assertEqual(full.json()["returned"], 103)
            limited = self.client.post("/requirements/query", json={"jql": "project=TEST", "limit": 5}, headers=self.headers)
            self.assertTrue(limited.json()["truncated"])
            export = self.client.post("/requirements/export", json={"jql": "project=TEST", "limit": 5}, headers=self.headers)
            self.assertEqual(export.status_code, 422)

    def test_csv_all_fields_unicode_and_formula_safety(self):
        def upstream(method, path, data=None):
            if path.endswith("/field"):
                return [{"id": "summary", "name": "概要"}, {"id": "customfield_1", "name": "空字段"}]
            self.assertEqual(data["fields"], ["*all"])
            return {"total": 1, "issues": [{"key": "TEST-1", "fields": {"summary": "=危险公式", "description": "中文,换行\n说明"}}]}
        with patch.object(service, "jira", side_effect=upstream):
            response = self.client.post("/requirements/export", json={"jql": "project=TEST", "all_fields": True}, headers=self.headers)
            self.assertEqual(response.status_code, 200)
            rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
            self.assertIn("空字段 [customfield_1]", rows[0])
            self.assertEqual(rows[1][1], "'=危险公式")
            self.assertIn("中文,换行\n说明", rows[1])

    def workflow_jira(self, method, path, data=None):
        if path.endswith('/resolution'):
            return [{"id": "1", "name": "Fixed"}, {"id": "2", "name": "Won't Fix"}]
        if '/transitions' in path:
            if method == 'POST':
                self.workflow_post = data
                self.workflow_status = "6"
                return {}
            return {"transitions": [{"id": "2", "name": "关闭问题",
                "to": {"id": "6", "name": "关闭", "statusCategory": {"key": "done"}},
                "fields": {"resolution": {"required": True, "allowedValues": [{"id": "1"}, {"id": "2"}]}}}]}
        return {"key": "TEST-1", "fields": {"status": {"id": self.workflow_status, "name": "开放"},
            "resolution": {"id": "2", "name": "Won't Fix"} if self.workflow_status == "6" else None}}

    def close_body(self, **extra):
        return {"transition_id": "2", "intent": "wont_do", "reason": "用户取消计划",
                "resolution_id": "2", "expected_status_id": "1", "dry_run": True, **extra}

    def test_close_preview_no_write(self):
        self.workflow_status = "1"
        with patch.object(service, "jira", side_effect=self.workflow_jira) as upstream:
            result = self.client.post('/requirements/TEST-1/close', json=self.close_body(), headers=self.headers)
            self.assertEqual(result.status_code, 200)
            self.assertFalse(result.json()['submitted'])
            self.assertTrue(all(c.args[0] == 'GET' for c in upstream.call_args_list))

    def test_close_submit_atomic_comment_and_replay_after_state_change(self):
        self.workflow_status = "1"
        with patch.object(service, "jira", side_effect=self.workflow_jira) as upstream:
            body = self.close_body(dry_run=False)
            result = self.client.post('/requirements/TEST-1/close', json=body, headers=self.headers)
            self.assertEqual(result.status_code, 200)
            self.assertTrue(result.json()['verified'])
            self.assertEqual(self.workflow_post['fields']['resolution'], {'id': '2'})
            self.assertIn('不做原因：用户取消计划', self.workflow_post['update']['comment'][0]['add']['body'])
            replay = self.client.post('/requirements/TEST-1/close', json=body, headers=self.headers)
            self.assertTrue(replay.json()['replayed'])
            self.assertEqual(sum(c.args[0] == 'POST' for c in upstream.call_args_list), 1)

    def test_wont_do_cannot_use_fixed_or_missing_resolution(self):
        self.workflow_status = "1"
        with patch.object(service, "jira", side_effect=self.workflow_jira):
            for resolution in ('1', None):
                result = self.client.post('/requirements/TEST-1/close', json=self.close_body(resolution_id=resolution), headers=self.headers)
                self.assertEqual(result.status_code, 422)

    def test_close_stale_status_and_invalid_transition(self):
        self.workflow_status = "1"
        with patch.object(service, "jira", side_effect=self.workflow_jira) as upstream:
            result = self.client.post('/requirements/TEST-1/close', json=self.close_body(expected_status_id="3"), headers=self.headers)
            self.assertEqual(result.status_code, 409)
            invalid = self.client.post('/requirements/TEST-1/close', json=self.close_body(transition_id="99"), headers=self.headers)
            self.assertEqual(invalid.status_code, 422)
            self.assertTrue(all(c.args[0] == 'GET' for c in upstream.call_args_list))

    def test_close_timeout_blocks_repeated_write(self):
        self.workflow_status = "1"
        def upstream(method, path, data=None):
            if method == 'POST':
                raise HTTPException(502, 'timeout')
            return self.workflow_jira(method, path, data)
        with patch.object(service, "jira", side_effect=upstream) as mock:
            body = self.close_body(dry_run=False)
            self.assertEqual(self.client.post('/requirements/TEST-1/close', json=body, headers=self.headers).status_code, 502)
            self.assertEqual(self.client.post('/requirements/TEST-1/close', json=body, headers=self.headers).status_code, 409)
            self.assertEqual(sum(c.args[0] == 'POST' for c in mock.call_args_list), 1)

    def test_transport_accepts_204_empty_response(self):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b''
        with patch.dict(os.environ, {'JIRA_USERNAME': 'test', 'JIRA_PASSWORD': 'test'}), \
                patch.object(service.urllib.request, 'urlopen', return_value=response):
            self.assertEqual(service.jira('POST', '/rest/api/2/issue/TEST-1/transitions', {}), {})


class ReportTests(unittest.TestCase):
    def test_timezone_window_and_csv(self):
        from reporting import ResolvedReportRequest, report_window, report_rows, REPORT_FIELDS
        body = ResolvedReportRequest(start_date="2026-09-01", end_date="2026-10-01")
        start, end, zone, jql = report_window(body, "UTC")
        self.assertIn('resolved >= "2026-08-31 17:00"', jql)
        self.assertIn('resolved < "2026-09-30 17:00"', jql)
        issue = {"key": "CE-1", "fields": {"summary": "中文,标题", "issuetype": {"name": "任务"},
                 "assignee": None, "reporter": {"name": "sens", "displayName": "其他显示名"},
                 "project": {"name": "CE"}, "resolutiondate": "2026-08-31T17:00:00.000+0000",
                 "created": "2026-08-01T12:20:21.000+0800"}}
        rows = report_rows([issue], start, end, zone)
        self.assertEqual(rows[0]["fields"]["resolutiondate"], "2026-09-01 00:00:00")
        self.assertEqual(rows[0]["fields"]["created"], "2026-08-01 11:20:21")
        self.assertEqual(rows[0]["fields"]["reporter"], "sens")
        def upstream(method, path, payload=None):
            if path.endswith("myself"):
                return {"timeZone": "UTC"}
            self.assertEqual(payload["fields"], REPORT_FIELDS)
            return {"total": 1, "issues": [issue]}
        with patch.dict(os.environ, {"JIRA_SERVICE_API_KEY": "test-key"}), patch.object(service, "jira", side_effect=upstream):
            result = TestClient(service.app).post("/reports/resolved/export", json=body.model_dump(mode="json"), headers={"X-API-Key": "test-key"})
        self.assertEqual(result.status_code, 200)
        csv_rows = list(csv.reader(io.StringIO(result.content.decode("utf-8-sig"))))
        self.assertEqual(csv_rows[0], ["问题关键字", "概要", "问题类型", "经办人", "已解决", "报告人", "创建时间", "项目名称"])
        self.assertEqual(len(csv_rows[1]), 8)
        self.assertEqual(csv_rows[1][3], "")

    def test_invalid_period_dates_and_duplicates(self):
        from reporting import ResolvedReportRequest, report_window, report_rows
        with self.assertRaises(HTTPException):
            report_window(ResolvedReportRequest(start_date="2026-10-01", end_date="2026-09-01"), "UTC")
        start, end, zone, _ = report_window(ResolvedReportRequest(start_date="2026-09-01", end_date="2026-10-01"), "Asia/Bangkok")
        for stamp in (None, "2026-09-01T00:00:00", "2026-10-01T00:00:00+0700"):
            with self.assertRaises(HTTPException):
                report_rows([{"key": "CE-1", "fields": {"resolutiondate": stamp}}], start, end, zone)
        issue = {"key": "CE-1", "fields": {"resolutiondate": "2026-09-01T00:00:00+0700", "created": "2026-08-01T00:00:00+0700"}}
        with self.assertRaises(HTTPException):
            report_rows([issue, issue], start, end, zone)


if __name__ == "__main__":
    unittest.main()
