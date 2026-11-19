import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).parents[1]))
import private_config as config

class PrivateConfigTests(unittest.TestCase):
    def test_windows_owner_system_admin_and_owner_rights_are_allowed(self):
        config.validate_windows_acl({"owner":"owner", "current":"current", "rules":[
            {"sid":sid,"allow":True,"rights":1} for sid in
            ("owner","current","S-1-5-18","S-1-5-32-544","S-1-3-4")]})

    def test_windows_broad_read_permissions_are_rejected(self):
        for sid in ("S-1-1-0","S-1-5-11","S-1-5-32-545","untrusted"):
            with self.assertRaises(ValueError):
                config.validate_windows_acl({"owner":"owner","current":"current","rules":[
                    {"sid":sid,"allow":True,"rights":1}]})

    def test_deny_and_non_read_rules_do_not_grant_read(self):
        config.validate_windows_acl({"owner":"owner","current":"current","rules":[
            {"sid":"untrusted","allow":False,"rights":1},
            {"sid":"untrusted","allow":True,"rights":256}]})

    def test_bom_configuration_and_environment_override(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"config.json"
            path.write_text(json.dumps({"JIRA_USERNAME":"test-user"}),encoding="utf-8-sig")
            with patch.object(config,"assert_private_file") as check, patch.dict(os.environ,{"JIRA_SERVICE_CONFIG":str(path)}):
                self.assertEqual(config.load_private_config()["JIRA_USERNAME"],"test-user")
                check.assert_called_once_with(path)

    def test_missing_config_can_use_environment_only(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(config.load_private_config(Path(directory)/"missing.json"),{})

if __name__ == "__main__":unittest.main()
