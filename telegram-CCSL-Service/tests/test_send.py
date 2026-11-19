"""Offline regression checks; never contact Telegram."""
import importlib.util
import io
import os
from pathlib import Path
import ssl
import subprocess
import unittest
from unittest.mock import patch, Mock
from urllib.error import URLError

spec = importlib.util.spec_from_file_location('telegram_send', Path(__file__).resolve().parents[1] / 'scripts/send.py')
send = importlib.util.module_from_spec(spec)
spec.loader.exec_module(send)


class SendTests(unittest.TestCase):
    def test_macos_loads_both_system_keychains(self):
        context = Mock()
        with patch.dict(os.environ, {}, clear=True), patch.object(send.sys, 'platform', 'darwin'), patch.object(send.ssl, 'create_default_context', return_value=context), patch.object(send.subprocess, 'run', return_value=Mock(stdout='PEM')) as run:
            self.assertIs(send.build_ssl_context(), context)
        self.assertEqual(run.call_count, 2)
        self.assertEqual(context.load_verify_locations.call_count, 2)
        self.assertIn('/Library/Keychains/System.keychain', run.call_args.args[0])

    def test_explicit_ca_settings_take_precedence(self):
        for name in ('SSL_CERT_FILE', 'SSL_CERT_DIR'):
            with self.subTest(name=name), patch.dict(os.environ, {name: '/custom-ca'}, clear=True), patch.object(send.sys, 'platform', 'darwin'), patch.object(send.ssl, 'create_default_context'), patch.object(send.subprocess, 'run') as run:
                send.build_ssl_context()
                run.assert_not_called()

    def test_system_ca_failure_stops_before_send(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(send.sys, 'platform', 'darwin'), patch.object(send.subprocess, 'run', side_effect=subprocess.TimeoutExpired('security', 10)), patch.object(send, 'load_config', return_value=('fake-token', 'fake-chat')), patch.object(send, 'urlopen') as request:
            with self.assertRaisesRegex(RuntimeError, 'System CA loading failed'):
                send.send_message('test')
            request.assert_not_called()

    def test_real_context_preserves_tls_verification(self):
        with patch.object(send.sys, 'platform', 'linux'):
            context = send.build_ssl_context()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)

    def test_send_uses_context_and_never_retries(self):
        context = object()
        with patch.object(send, 'load_config', return_value=('fake-token', 'fake-chat')), patch.object(send, 'build_ssl_context', return_value=context), patch.object(send, 'urlopen', side_effect=URLError('failure')) as request:
            with self.assertRaisesRegex(RuntimeError, 'no retry performed'):
                send.send_message('test')
            request.assert_called_once()
            self.assertIs(request.call_args.kwargs['context'], context)

    def test_check_does_not_send(self):
        with patch.object(send.sys, 'argv', ['send.py', '--check']), patch.object(send, 'load_config'), patch.object(send, 'build_ssl_context') as context, patch.object(send, 'urlopen') as request, patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(send.main(), 0)
            context.assert_called_once()
            request.assert_not_called()


if __name__ == '__main__':
    unittest.main()
