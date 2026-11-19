"""CCSL Telegram helper. Importing or --check never sends messages."""
import argparse
import json
import os
import ssl
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / '.local' / 'credentials.json'

def build_ssl_context():
    """Use explicit CA settings, or augment Python trust with macOS system CAs."""
    context = ssl.create_default_context()
    if sys.platform == 'darwin' and not any(
        name in os.environ for name in ('SSL_CERT_FILE', 'SSL_CERT_DIR')
    ):
        for keychain in (
            '/System/Library/Keychains/SystemRootCertificates.keychain',
            '/Library/Keychains/System.keychain',
        ):
            try:
                result = subprocess.run(
                    ['/usr/bin/security', 'find-certificate', '-a', '-p', keychain],
                    capture_output=True, text=True, timeout=10, check=True,
                )
                if result.stdout.strip():
                    context.load_verify_locations(cadata=result.stdout)
            except (OSError, subprocess.SubprocessError, ssl.SSLError):
                raise RuntimeError('System CA loading failed; no request sent') from None
    return context

def load_config(config=None):
    path = Path(config or DEFAULT_CONFIG)
    data = {}
    if path.exists():
        if path.stat().st_mode & 0o077:
            raise ValueError('Credential file must have mode 600')
        data = json.loads(path.read_text())
    token = os.environ.get('TELEGRAM_BOT_TOKEN') or data.get('bot_token')
    chat = os.environ.get('TELEGRAM_CHAT_ID') or data.get('chat_id')
    if not token or not chat:
        raise ValueError('Missing Telegram credentials')
    return str(token), str(chat)

def send_message(text, *, prefix=None, config=None, parse_mode=None):
    token, chat = load_config(config)
    if not text or not text.strip():
        raise ValueError('Message is empty')
    text = ('[' + prefix + '] ' if prefix else '') + text
    if len(text) > 4096:
        raise ValueError('Message exceeds 4096 characters')
    body = {'chat_id': chat, 'text': text}
    if parse_mode:
        if parse_mode not in ('Markdown', 'MarkdownV2', 'HTML'):
            raise ValueError('Unsupported parse mode')
        body['parse_mode'] = parse_mode
    request = Request('https://api.telegram.org/bot' + token + '/sendMessage', data=urlencode(body).encode(), method='POST')
    context = build_ssl_context()
    try:
        with urlopen(request, timeout=15, context=context) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise RuntimeError('Telegram HTTP failure: ' + str(exc.code)) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise RuntimeError('Telegram request failed; delivery may be unknown; no retry performed') from None
    if not isinstance(result, dict) or result.get('ok') is not True:
        raise RuntimeError('Telegram rejected request')
    return {'ok': True, 'message_id': result.get('result', {}).get('message_id')}

def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--send', action='store_true')
    parser.add_argument('--config')
    parser.add_argument('--prefix')
    parser.add_argument('--parse-mode', choices=['Markdown','MarkdownV2','HTML'])
    args = parser.parse_args()
    try:
        if args.check:
            load_config(args.config)
            build_ssl_context()
            print('Configuration and TLS context valid; no request sent')
        else:
            result = send_message(sys.stdin.read(), prefix=args.prefix, config=args.config, parse_mode=args.parse_mode)
            print(json.dumps(result))
    except Exception:
        print('Check or send failed; credentials and response content suppressed', file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
