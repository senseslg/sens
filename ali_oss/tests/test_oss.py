"""Offline regression checks; never contact OSS."""
import argparse
import importlib.util
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

spec = importlib.util.spec_from_file_location('oss', Path(__file__).resolve().parents[1] / 'scripts/oss.py')
oss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oss)


def args(*argv):
    return oss.build_parser().parse_args(list(argv))


class SignTests(unittest.TestCase):
    def test_v1_string_to_sign_layout(self):
        # Alibaba Cloud OSS V1 signature doc example.
        c = oss.OssClient('44CF9590006BF252F707', 'OtxrzxIsfpFjA7SwPzILwy8Bw21TLhquhboDYROV')
        headers = {'Content-MD5': 'eB5eJF1ptWaXm4bijSPyxw==', 'Content-Type': 'text/html',
                   'Date': 'Thu, 17 Nov 2005 18:49:58 GMT', 'x-oss-magic': 'abracadabra',
                   'x-oss-meta-author': 'foo@example.com'}
        self.assertEqual(c.string_to_sign('PUT', 'examplebucket', 'nelson', {}, headers),
                         'PUT\neB5eJF1ptWaXm4bijSPyxw==\ntext/html\nThu, 17 Nov 2005 18:49:58 GMT\n'
                         'x-oss-magic:abracadabra\nx-oss-meta-author:foo@example.com\n/examplebucket/nelson')

    def test_subresources_sorted_and_query_params_excluded(self):
        res = oss.OssClient._canonical_resource('b', '', {'prefix': 'x', 'acl': '', 'stat': ''})
        self.assertEqual(res, '/b/?acl&stat')
        self.assertEqual(oss.OssClient._canonical_resource(None, None, {}), '/')

    def test_presign_contains_no_secret(self):
        url = oss.OssClient('KEYID', 'SECRET').presign_url('uat-ccsl', 'a b.png', 60)
        self.assertIn('uat-ccsl.oss-cn-hongkong.aliyuncs.com/a%20b.png', url)
        self.assertNotIn('SECRET', url)


class GuardTests(unittest.TestCase):
    def test_write_defaults_to_dry_run(self):
        client = Mock()
        out = oss.run(args('delete', 'uat-ccsl', 'k'), client=client)
        self.assertFalse(out['ok']); self.assertIn('DRY-RUN', out['result'])
        client.delete_object.assert_not_called()

    def test_production_requires_confirm_even_with_apply(self):
        client = Mock()
        out = oss.run(args('put-bucket-acl', 'cambodianexpress-ccsl', 'private', '--apply'), client=client)
        self.assertIn('REFUSED', out['result'])
        client.put_bucket_acl.assert_not_called()

    def test_apply_with_confirm_runs(self):
        client = Mock(); client.delete_object.return_value = 204
        out = oss.run(args('delete', 'ceccsl', 'k', '--apply', '--confirm-bucket', 'ceccsl'), client=client)
        self.assertEqual(out, {'ok': True, 'status': 204})


class CredentialTests(unittest.TestCase):
    def _write(self, mode, data):
        d = tempfile.mkdtemp(); p = Path(d) / 'c.json'
        p.write_text(json.dumps(data)); os.chmod(p, mode)
        return p

    def test_rejects_loose_permissions(self):
        p = self._write(0o644, {'access_key_id': 'a', 'access_key_secret': 'b'})
        with self.assertRaisesRegex(RuntimeError, '0600'):
            oss.load_credentials(p)

    def test_check_masks_key(self):
        p = self._write(0o600, {'access_key_id': 'LTAIabcdef', 'access_key_secret': 'zzz'})
        out = oss.run(args('--credentials', str(p), 'check'))
        self.assertEqual(out['access_key_id'], 'LTAI****')
        self.assertNotIn('zzz', json.dumps(out))

    def test_import_csv_writes_0600_and_masks(self):
        d = Path(tempfile.mkdtemp()); src = d / 'k.csv'; dest = d / 'out' / 'c.json'
        src.write_text('\ufeffUserPrincipalName,AccessKey ID,AccessKey Secret\nu@x,LTAIabcdef,s3cr3t\n')
        out = oss.run(args('--credentials', str(dest), 'import-csv', str(src), '--delete-csv'))
        self.assertEqual(out['access_key_id'], 'LTAI****'); self.assertNotIn('s3cr3t', json.dumps(out))
        self.assertEqual(stat.S_IMODE(dest.stat().st_mode), 0o600); self.assertFalse(src.exists())
        self.assertEqual(oss.load_credentials(dest)[0]['access_key_secret'], 's3cr3t')

    def test_placeholder_rejected(self):
        p = self._write(0o600, {'access_key_id': 'REPLACE_WITH_REAL_VALUE', 'access_key_secret': 'x'})
        with self.assertRaisesRegex(RuntimeError, 'missing access_key_id'):
            oss.load_credentials(p)


if __name__ == '__main__':
    unittest.main()
