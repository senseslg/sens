"""Offline checks for sending boundaries, credential handling and request format."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib import error, parse

spec = importlib.util.spec_from_file_location("send_sms", Path(__file__).parents[1] / "scripts/send_sms.py")
sms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sms)


class SmsTests(unittest.TestCase):
    def setUp(self):
        self.payload = {"sender": "SMS Info", "to": "85512345678", "content": "你好 #ma#test#ma#"}

    def test_default_dry_run_never_loads_credentials_or_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "message.json"
            path.write_text(json.dumps(self.payload))
            with patch.object(sms, "send_request") as send, patch.object(sms, "load_credentials") as creds:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(sms.main(["--payload", str(path)]), 0)
                send.assert_not_called()
                creds.assert_not_called()
                self.assertNotIn(self.payload["to"], output.getvalue())
                self.assertFalse(json.loads(output.getvalue())["network_called"])

    def test_request_format_and_no_redirect(self):
        response = unittest.mock.MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = b'{}'
        with patch.object(sms.request, "build_opener") as build:
            build.return_value.open.return_value = response
            credentials = {"private_key": "fake &+key", "X-Secret": "fake-secret"}
            self.assertEqual(sms.send_request(self.payload, credentials), (200, b'{}'))
            req = build.return_value.open.call_args.args[0]
            self.assertEqual(parse.parse_qs(parse.urlsplit(req.full_url).query)["private_key"], ["fake &+key"])
            self.assertEqual(req.get_header("X-secret"), "fake-secret")
            self.assertEqual(json.loads(req.data), self.payload)
            self.assertEqual(req.method, "POST")
        self.assertIsNone(sms.NoRedirect().redirect_request(None, None, 302, None, None, "https://example.com"))

    def test_http_error_is_not_retried(self):
        with patch.object(sms.request, "build_opener") as build:
            build.return_value.open.side_effect = error.HTTPError("https://example.com", 429, "limited", {}, io.BytesIO(b'{}'))
            self.assertEqual(sms.send_request(self.payload, {"private_key": "fake", "X-Secret": "fake"})[0], 429)
            self.assertEqual(build.return_value.open.call_count, 1)

    def test_credentials_permissions_and_env(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {}, clear=True):
            path = Path(tmp) / "config.json"
            path.write_text('{"private_key":"fake","X-Secret":"fake"}')
            path.chmod(0o644)
            with self.assertRaises(ValueError):
                sms.load_credentials(path)
            path.chmod(0o600)
            self.assertEqual(sms.load_credentials(path)["private_key"], "fake")
            with patch.dict(os.environ, {"PLASGATE_PRIVATE_KEY": "env-fake", "PLASGATE_X_SECRET": "env-fake"}):
                self.assertEqual(sms.load_credentials(Path(tmp) / "absent")["private_key"], "env-fake")
            link = Path(tmp) / "link"
            link.symlink_to(path)
            with self.assertRaises(OSError):
                sms.load_credentials(link)

    def test_batch_and_bad_input(self):
        self.assertEqual(sms.validate_payload({"globals": {"sender": "Test"}, "messages": [{"to": ["8551", "8552"], "content": "Test"}]}, True), 2)
        for bad in [{}, {**self.payload, "to": "8551,8552"}, {**self.payload, "content": ""}]:
            with self.assertRaises(ValueError):
                sms.validate_payload(bad)
        for url in ["http://example.com", "https://user@example.com", "https://example.com/path", "https://example.com?secret=x"]:
            with self.assertRaises(ValueError):
                sms.endpoint(url)


if __name__ == "__main__":
    unittest.main()
