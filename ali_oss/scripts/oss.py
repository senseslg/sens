#!/usr/bin/env python3
"""Alibaba Cloud OSS helper (stdlib only, OSS V1 signature).

Read commands contact OSS directly. Write commands (upload / delete / put-bucket-acl)
only print a preview unless --apply is given; production buckets also need
--confirm-bucket <name>. Secrets are never printed.

Python use:
    from oss import OssClient
    c = OssClient.from_file()                    # or OssClient(key_id, secret)
    c.list_objects('uat-ccsl', prefix='img/', max_keys=20)
"""
import argparse
import base64
import csv
import datetime as _dt
import hashlib
import hmac
import json
import mimetypes
import os
import ssl
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CREDENTIALS = ROOT / '.local' / 'credentials.json'
DEFAULT_REGION = 'cn-hongkong'
# Production or business-critical buckets (console 2026-11-27; uat-mallgogo carries ~94%
# of account egress, so treat it as live until proven otherwise). Writes need --confirm-bucket.
PROTECTED_BUCKETS = {'cambodianexpress-ccsl', 'ccsl-mallgogo', 'ceccsl', 'uat-mallgogo'}
ACLS = ('private', 'public-read', 'public-read-write')
# Sub-resources that are part of the V1 canonicalized resource.
SUBRESOURCES = {
    'acl', 'bucketInfo', 'cors', 'lifecycle', 'location', 'logging', 'referer',
    'stat', 'versioning', 'versions', 'versionId', 'website', 'uploads', 'uploadId',
    'partNumber', 'objectMeta', 'tagging', 'security-token', 'response-content-type',
    'response-content-disposition', 'response-cache-control', 'response-expires',
    'continuation-token',
}


class OssError(RuntimeError):
    def __init__(self, status, code, message, request_id=''):
        super().__init__(f'HTTP {status} {code}: {message}'.strip())
        self.status, self.code, self.request_id = status, code, request_id


def build_ssl_context():
    """Honour SSL_CERT_FILE/DIR; on macOS add system keychain CAs (same as telegram-CCSL-Service)."""
    context = ssl.create_default_context()
    if sys.platform == 'darwin' and not any(n in os.environ for n in ('SSL_CERT_FILE', 'SSL_CERT_DIR')):
        for keychain in ('/System/Library/Keychains/SystemRootCertificates.keychain',
                         '/Library/Keychains/System.keychain'):
            try:
                out = subprocess.run(['/usr/bin/security', 'find-certificate', '-a', '-p', keychain],
                                     capture_output=True, text=True, timeout=10, check=True).stdout
                if out.strip():
                    context.load_verify_locations(cadata=out)
            except (OSError, subprocess.SubprocessError, ssl.SSLError):
                raise RuntimeError('System CA loading failed; no request sent') from None
    return context


def load_credentials(path=None):
    """Read {access_key_id, access_key_secret[, security_token, region]} from a 0600 JSON file."""
    p = Path(path or os.environ.get('ALI_OSS_CREDENTIALS') or DEFAULT_CREDENTIALS).expanduser()
    if not p.is_file():
        raise RuntimeError(f'credentials file not found: {p} (see ali_oss/RUNBOOK.md)')
    if p.stat().st_mode & 0o077:
        raise RuntimeError(f'credentials file must be 0600: {p}')
    data = json.loads(p.read_text())
    for key in ('access_key_id', 'access_key_secret'):
        if not str(data.get(key, '')).strip() or 'REPLACE' in str(data.get(key)):
            raise RuntimeError(f'credentials file missing {key}: {p}')
    return data, p


def import_csv(csv_path, dest=None, region=DEFAULT_REGION):
    """Convert the RAM console AccessKey CSV into the 0600 credentials JSON; secret never printed."""
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 1:
        raise RuntimeError(f'expected exactly 1 AccessKey row, got {len(rows)}')
    norm = {k.strip().lower().replace(' ', '').replace('_', ''): (v or '').strip() for k, v in rows[0].items() if k}
    key_id, secret = norm.get('accesskeyid'), norm.get('accesskeysecret')
    if not key_id or not secret:
        raise RuntimeError('CSV lacks AccessKey ID / AccessKey Secret columns')
    dest = Path(dest or DEFAULT_CREDENTIALS)
    dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump({'access_key_id': key_id, 'access_key_secret': secret, 'region': region}, f, indent=2)
    os.chmod(dest, 0o600)
    return {'ok': True, 'path': str(dest), 'access_key_id': key_id[:4] + '****'}


def _text(el, tag, default=''):
    found = el.find(tag)
    return found.text if found is not None and found.text is not None else default


def _strip_ns(xml_bytes):
    root = ET.fromstring(xml_bytes)
    for el in root.iter():
        if '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]
    return root


class OssClient:
    def __init__(self, access_key_id, access_key_secret, security_token=None,
                 region=DEFAULT_REGION, internal=False, timeout=30):
        self._id, self._secret, self._token = access_key_id, access_key_secret, security_token
        self.region = region
        self.endpoint = f'oss-{region}{"-internal" if internal else ""}.aliyuncs.com'
        self.timeout = timeout
        self._ctx = None

    @classmethod
    def from_file(cls, path=None, **kw):
        data, _ = load_credentials(path)
        kw.setdefault('region', data.get('region') or DEFAULT_REGION)
        return cls(data['access_key_id'], data['access_key_secret'], data.get('security_token'), **kw)

    # ---------- signing ----------
    @staticmethod
    def _canonical_resource(bucket, key, params):
        res = '/'
        if bucket:
            res += f'{bucket}/' + (key or '')
        subs = sorted(k for k in params if k in SUBRESOURCES)
        if subs:
            res += '?' + '&'.join(k if params[k] in (None, '') else f'{k}={params[k]}' for k in subs)
        return res

    def string_to_sign(self, method, bucket, key, params, headers):
        oss_headers = ''.join(f'{k}:{v}\n' for k, v in sorted(
            (k.lower(), str(v).strip()) for k, v in headers.items() if k.lower().startswith('x-oss-')))
        string_to_sign = '\n'.join([method, headers.get('Content-MD5', ''), headers.get('Content-Type', ''),
                                    headers['Date']]) + '\n' + oss_headers + \
            self._canonical_resource(bucket, key, params)
        return string_to_sign

    def sign(self, method, bucket, key, params, headers):
        string_to_sign = self.string_to_sign(method, bucket, key, params, headers)
        digest = hmac.new(self._secret.encode(), string_to_sign.encode(), hashlib.sha1).digest()
        return base64.b64encode(digest).decode()

    def _url(self, bucket, key, params):
        host = f'{bucket}.{self.endpoint}' if bucket else self.endpoint
        path = '/' + quote(key or '', safe='/~')
        query = '&'.join(k if v in (None, '') else urlencode({k: v}) for k, v in params.items())
        return f'https://{host}{path}' + (f'?{query}' if query else '')

    def request(self, method, bucket=None, key=None, params=None, headers=None, body=None):
        params, headers = dict(params or {}), dict(headers or {})
        headers['Date'] = _dt.datetime.now(_dt.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
        if self._token:
            headers['x-oss-security-token'] = self._token
        headers['Authorization'] = f'OSS {self._id}:{self.sign(method, bucket, key, params, headers)}'
        if self._ctx is None:
            self._ctx = build_ssl_context()
        req = Request(self._url(bucket, key, params), data=body, headers=headers, method=method)
        try:
            with urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except HTTPError as e:
            raw = e.read()
            code, msg, rid = '', e.reason, e.headers.get('x-oss-request-id', '')
            try:
                root = _strip_ns(raw)
                code, msg = _text(root, 'Code'), _text(root, 'Message', msg)
            except ET.ParseError:
                pass
            raise OssError(e.code, code, msg, rid) from None
        except URLError as e:
            raise OssError(0, 'NetworkError', str(e.reason)) from None

    def presign_url(self, bucket, key, expires=3600):
        """Signed GET URL; computed locally, no request sent."""
        exp = str(int(_dt.datetime.now(_dt.timezone.utc).timestamp()) + int(expires))
        params = {'security-token': self._token} if self._token else {}
        sig = self.sign('GET', bucket, key, params, {'Date': exp})
        q = {'OSSAccessKeyId': self._id, 'Expires': exp, 'Signature': sig, **params}
        return f'https://{bucket}.{self.endpoint}/{quote(key, safe="/~")}?{urlencode(q)}'

    # ---------- read ----------
    def list_buckets(self):
        _, _, body = self.request('GET')
        root = _strip_ns(body)
        return [{'name': _text(b, 'Name'), 'region': _text(b, 'Region'), 'location': _text(b, 'Location'),
                 'storage_class': _text(b, 'StorageClass'), 'created': _text(b, 'CreationDate')}
                for b in root.iter('Bucket')]

    def bucket_info(self, bucket):
        _, _, body = self.request('GET', bucket, params={'bucketInfo': ''})
        b = _strip_ns(body).find('Bucket')
        return {'name': _text(b, 'Name'), 'location': _text(b, 'Location'), 'created': _text(b, 'CreationDate'),
                'storage_class': _text(b, 'StorageClass'), 'redundancy': _text(b, 'DataRedundancyType'),
                'acl': _text(b.find('AccessControlList'), 'Grant') if b.find('AccessControlList') is not None else '',
                'versioning': _text(b, 'Versioning'), 'extranet_endpoint': _text(b, 'ExtranetEndpoint')}

    def bucket_stat(self, bucket):
        _, _, body = self.request('GET', bucket, params={'stat': ''})
        return {el.tag: el.text for el in _strip_ns(body)}

    def get_config(self, bucket, sub):
        """Raw config for sub in acl/referer/cors/lifecycle/logging/versioning; None if not set."""
        try:
            _, _, body = self.request('GET', bucket, params={sub: ''})
        except OssError as e:
            if e.status == 404:
                return None
            raise
        return body.decode()

    def list_objects(self, bucket, prefix='', max_keys=100, delimiter='', token=''):
        params = {'list-type': '2', 'max-keys': str(max_keys)}
        if prefix:
            params['prefix'] = prefix
        if delimiter:
            params['delimiter'] = delimiter
        if token:
            params['continuation-token'] = token
        _, _, body = self.request('GET', bucket, params=params)
        root = _strip_ns(body)
        return {'objects': [{'key': _text(c, 'Key'), 'size': int(_text(c, 'Size', '0')),
                             'modified': _text(c, 'LastModified'), 'storage_class': _text(c, 'StorageClass')}
                            for c in root.findall('Contents')],
                'prefixes': [_text(p, 'Prefix') for p in root.findall('CommonPrefixes')],
                'next_token': _text(root, 'NextContinuationToken'),
                'truncated': _text(root, 'IsTruncated') == 'true'}

    def head_object(self, bucket, key):
        _, headers, _ = self.request('HEAD', bucket, key)
        keep = ('Content-Length', 'Content-Type', 'Last-Modified', 'ETag', 'x-oss-object-type',
                'x-oss-storage-class', 'x-oss-object-acl')
        lower = {k.lower(): v for k, v in headers.items()}
        return {k: lower[k.lower()] for k in keep if k.lower() in lower}

    def get_object(self, bucket, key, dest):
        _, _, body = self.request('GET', bucket, key)
        Path(dest).write_bytes(body)
        return len(body)

    # ---------- write (callers must guard) ----------
    def put_object(self, bucket, key, data, content_type=None, acl=None):
        headers = {'Content-Type': content_type or 'application/octet-stream',
                   'Content-MD5': base64.b64encode(hashlib.md5(data).digest()).decode()}
        if acl:
            headers['x-oss-object-acl'] = acl
        _, h, _ = self.request('PUT', bucket, key, headers=headers, body=data)
        return {'etag': h.get('ETag', ''), 'size': len(data)}

    def delete_object(self, bucket, key):
        status, _, _ = self.request('DELETE', bucket, key)
        return status

    def put_bucket_acl(self, bucket, acl):
        status, _, _ = self.request('PUT', bucket, params={'acl': ''}, headers={'x-oss-acl': acl}, body=b'')
        return status


# ---------- CLI ----------
WRITE_COMMANDS = {'upload', 'delete', 'put-bucket-acl'}


def guard_write(args):
    """Return None when the write may run, else a preview/refusal message."""
    if args.bucket in PROTECTED_BUCKETS and args.confirm_bucket != args.bucket:
        return f'REFUSED: {args.bucket} is production; add --confirm-bucket {args.bucket}'
    if not args.apply:
        return 'DRY-RUN: no request sent; add --apply to execute'
    return None


def build_parser():
    p = argparse.ArgumentParser(description='Alibaba Cloud OSS helper (read-only unless --apply).')
    p.add_argument('--credentials', help='JSON path (default $ALI_OSS_CREDENTIALS or ali_oss/.local/credentials.json)')
    p.add_argument('--region', help=f'default from credentials or {DEFAULT_REGION}')
    p.add_argument('--internal', action='store_true', help='use -internal endpoint (Alibaba Cloud ECS only)')
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('check', help='validate local credentials file; no network')
    s = sub.add_parser('import-csv', help='RAM console AccessKey CSV -> credentials JSON (0600); no network')
    s.add_argument('csv_path'); s.add_argument('--delete-csv', action='store_true', help='remove the CSV afterwards')
    sub.add_parser('buckets', help='list buckets')
    for name in ('info', 'stat'):
        s = sub.add_parser(name); s.add_argument('bucket')
    s = sub.add_parser('config', help='raw bucket config XML')
    s.add_argument('bucket'); s.add_argument('kind', choices=['acl', 'referer', 'cors', 'lifecycle', 'logging', 'versioning'])
    s = sub.add_parser('ls'); s.add_argument('bucket'); s.add_argument('--prefix', default='')
    s.add_argument('--max-keys', type=int, default=100); s.add_argument('--delimiter', default='')
    s.add_argument('--token', default='', help='continuation token from previous page')
    s = sub.add_parser('head'); s.add_argument('bucket'); s.add_argument('key')
    s = sub.add_parser('download'); s.add_argument('bucket'); s.add_argument('key'); s.add_argument('dest')
    s = sub.add_parser('sign-url', help='presigned GET URL, computed locally')
    s.add_argument('bucket'); s.add_argument('key'); s.add_argument('--expires', type=int, default=3600)
    s = sub.add_parser('upload'); s.add_argument('bucket'); s.add_argument('key'); s.add_argument('src')
    s.add_argument('--content-type'); s.add_argument('--acl', choices=ACLS)
    s = sub.add_parser('delete', help='delete ONE object'); s.add_argument('bucket'); s.add_argument('key')
    s = sub.add_parser('put-bucket-acl'); s.add_argument('bucket'); s.add_argument('acl', choices=ACLS)
    for name in WRITE_COMMANDS:
        sp = sub.choices[name]
        sp.add_argument('--apply', action='store_true', help='actually send the write request')
        sp.add_argument('--confirm-bucket', default='', help='required for production buckets')
    return p


def run(args, client=None):
    if args.cmd == 'import-csv':
        out = import_csv(args.csv_path, args.credentials, args.region or DEFAULT_REGION)
        if args.delete_csv:
            os.remove(args.csv_path); out['csv_deleted'] = True
        return out
    if args.cmd == 'check':
        data, path = load_credentials(args.credentials)
        return {'ok': True, 'path': str(path), 'access_key_id': data['access_key_id'][:4] + '****',
                'security_token': bool(data.get('security_token')), 'region': data.get('region') or DEFAULT_REGION}
    if args.cmd in WRITE_COMMANDS:
        preview = {'cmd': args.cmd, 'bucket': args.bucket,
                   **{k: getattr(args, k) for k in ('key', 'src', 'acl') if getattr(args, k, None)}}
        if args.cmd == 'upload':
            preview['size'] = Path(args.src).stat().st_size
        if args.cmd == 'put-bucket-acl' or args.cmd == 'delete':
            preview['irreversible'] = args.cmd == 'delete'
        blocked = guard_write(args)
        if blocked:
            return {'ok': False, 'result': blocked, 'preview': preview}
    kw = {'internal': args.internal}
    if args.region:
        kw['region'] = args.region
    c = client or OssClient.from_file(args.credentials, **kw)
    if args.cmd == 'buckets':
        return c.list_buckets()
    if args.cmd == 'info':
        return c.bucket_info(args.bucket)
    if args.cmd == 'stat':
        return c.bucket_stat(args.bucket)
    if args.cmd == 'config':
        return {'kind': args.kind, 'xml': c.get_config(args.bucket, args.kind)}
    if args.cmd == 'ls':
        return c.list_objects(args.bucket, args.prefix, args.max_keys, args.delimiter, args.token)
    if args.cmd == 'head':
        return c.head_object(args.bucket, args.key)
    if args.cmd == 'download':
        return {'dest': args.dest, 'bytes': c.get_object(args.bucket, args.key, args.dest)}
    if args.cmd == 'sign-url':
        return {'url': c.presign_url(args.bucket, args.key, args.expires), 'expires_in': args.expires}
    if args.cmd == 'upload':
        data = Path(args.src).read_bytes()
        ctype = args.content_type or mimetypes.guess_type(args.src)[0]
        return {'ok': True, **c.put_object(args.bucket, args.key, data, ctype, args.acl)}
    if args.cmd == 'delete':
        return {'ok': True, 'status': c.delete_object(args.bucket, args.key)}
    if args.cmd == 'put-bucket-acl':
        return {'ok': True, 'status': c.put_bucket_acl(args.bucket, args.acl)}
    raise ValueError(args.cmd)


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        out = run(args)
    except OssError as e:
        print(json.dumps({'ok': False, 'status': e.status, 'code': e.code, 'error': str(e),
                          'request_id': e.request_id}, ensure_ascii=False), file=sys.stderr)
        return 2
    except (RuntimeError, OSError, ValueError) as e:
        print(json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if not (isinstance(out, dict) and out.get('ok') is False) else 3


if __name__ == '__main__':
    sys.exit(main())
