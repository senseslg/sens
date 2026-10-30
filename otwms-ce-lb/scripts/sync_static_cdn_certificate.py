#!/usr/bin/env python3
"""Safely upload the renewed static certificate to CAS and bind it to CDN."""
from __future__ import print_function

import argparse
import datetime
import fcntl
import hashlib
import hmac
import json
import os
import socket
import ssl
import subprocess
import sys
import time
import uuid
try:
    from urllib.request import Request, urlopen
    from urllib.parse import urlencode, quote
    from urllib.error import HTTPError, URLError
except ImportError:  # pragma: no cover - Python 2 is intentionally unsupported
    raise

DOMAIN = 'static.cambodianexpress.com'
CDN_REGION = 'ap-southeast-1'
CAS_HOST = 'cas.ap-southeast-1.aliyuncs.com'
CDN_HOST = 'cdn.aliyuncs.com'
CDN_VERSION = '2018-05-10'
CAS_VERSION = '2020-04-07'
ACCOUNT_FILE = '/etc/letsencrypt-oss-static/secrets/aliyun.json'
CERT_DIR = '/etc/letsencrypt-oss-static/live/static.cambodianexpress.com'


class SafeError(Exception):
    pass


def run(args):
    try:
        return subprocess.check_output(args, stderr=subprocess.PIPE).decode('utf-8').strip()
    except subprocess.CalledProcessError as exc:
        raise SafeError('certificate_validation_failed')


def read_secure_json(path):
    st = os.stat(path)
    if not os.path.isfile(path) or st.st_uid != os.geteuid() or (st.st_mode & 0o077):
        raise SafeError('credentials_permissions_invalid')
    with open(path, 'r') as handle:
        data = json.load(handle)
    if not data.get('access_key_id') or not data.get('access_key_secret'):
        raise SafeError('credentials_incomplete')
    return data


def api_call(credentials, host, action, version, params, method='GET'):
    body = json.dumps(params, ensure_ascii=False, separators=(',', ':')).encode('utf-8') if method == 'POST' else b''
    headers = {
        'host': host,
        'x-acs-action': action,
        'x-acs-version': version,
        'x-acs-date': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'x-acs-signature-nonce': str(uuid.uuid4()),
        'x-acs-content-sha256': hashlib.sha256(body).hexdigest(),
    }
    if method == 'POST':
        headers['content-type'] = 'application/json; charset=utf-8'
    if credentials.get('security_token'):
        headers['x-acs-security-token'] = credentials['security_token']
    signed_names = sorted(headers)
    canonical_headers = ''.join('%s:%s\n' % (key, headers[key].strip()) for key in signed_names)
    signed_headers = ';'.join(signed_names)
    query_params = {} if method == 'POST' else params
    query = urlencode(sorted(query_params.items()), quote_via=quote, safe='~')
    canonical = '%s\n/\n%s\n%s\n%s\n%s' % (
        method, query, canonical_headers, signed_headers, hashlib.sha256(body).hexdigest())
    string_to_sign = 'ACS3-HMAC-SHA256\n' + hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    signature = hmac.new(credentials['access_key_secret'].encode('utf-8'),
                         string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
    headers['Authorization'] = 'ACS3-HMAC-SHA256 Credential=%s,SignedHeaders=%s,Signature=%s' % (
        credentials['access_key_id'], signed_headers, signature)
    request_url = 'https://%s/' % host + (('?' + query) if query else '')
    request = Request(request_url, data=body if method == 'POST' else None,
                      headers=headers, method=method)
    try:
        ca_file = '/etc/ssl/cert.pem' if os.path.isfile('/etc/ssl/cert.pem') else None
        with urlopen(request, context=ssl.create_default_context(cafile=ca_file), timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except HTTPError as exc:
        try:
            data = json.loads(exc.read().decode('utf-8'))
            raise SafeError('aliyun_api_error_%s' % data.get('Code', 'unknown'))
        except (ValueError, UnicodeError):
            raise SafeError('aliyun_http_error_%s' % exc.code)
    except URLError as exc:
        raise SafeError('aliyun_network_error_%s' % type(exc.reason).__name__)
    except socket.timeout:
        raise SafeError('aliyun_network_timeout')


def certificate_facts(cert_path, key_path):
    cert_text = run(['openssl', 'x509', '-in', cert_path, '-noout', '-text'])
    sans = []
    in_san = False
    for line in cert_text.splitlines():
        if 'X509v3 Subject Alternative Name:' in line:
            in_san = True
            continue
        if in_san:
            sans.extend(item.strip()[4:] for item in line.strip().split(',')
                         if item.strip().startswith('DNS:'))
            if sans or not line.startswith(' '):
                break
    if DOMAIN not in sans:
        raise SafeError('certificate_san_mismatch')
    cert_pub = run(['openssl', 'x509', '-in', cert_path, '-pubkey', '-noout'])
    key_pub = run(['openssl', 'pkey', '-in', key_path, '-pubout'])
    if cert_pub != key_pub:
        raise SafeError('certificate_key_mismatch')
    expiry = run(['openssl', 'x509', '-in', cert_path, '-noout', '-enddate']).split('=', 1)[1]
    end = datetime.datetime.strptime(expiry, '%b %d %H:%M:%S %Y %Z')
    if end <= datetime.datetime.utcnow() + datetime.timedelta(days=14):
        raise SafeError('certificate_expiry_too_near')
    der = subprocess.check_output(['openssl', 'x509', '-in', cert_path, '-outform', 'DER'])
    public_key_der = subprocess.check_output(
        ['openssl', 'x509', '-in', cert_path, '-pubkey', '-noout'])
    public_key_der = subprocess.check_output(
        ['openssl', 'pkey', '-pubin', '-outform', 'DER'], input=public_key_der)
    serial = run(['openssl', 'x509', '-in', cert_path, '-noout', '-serial']).split('=', 1)[1].upper()
    return {'sha2': hashlib.sha256(public_key_der).hexdigest().upper(),
            'cert_sha256': hashlib.sha256(der).hexdigest().upper(),
            'serial': serial, 'end_date': end.strftime('%Y-%m-%d')}


def get_cdn_info(credentials):
    result = api_call(credentials, CDN_HOST, 'DescribeDomainCertificateInfo', CDN_VERSION,
                      {'DomainName': DOMAIN})
    items = result.get('CertInfos', {}).get('CertInfo', [])
    if len(items) != 1:
        raise SafeError('cdn_certificate_binding_missing_or_ambiguous')
    return items[0]


def find_cas_certificate(credentials, facts, current_id):
    matches = []
    page = 1
    while True:
        result = api_call(credentials, CAS_HOST, 'ListUserCertificateOrder', CAS_VERSION,
                          {'OrderType': 'UPLOAD', 'CurrentPage': page, 'ShowSize': 100})
        matches.extend(item for item in result.get('CertificateOrderList', [])
                       if (str(item.get('Sha2', '')).upper() == facts['sha2'] and
                           str(item.get('SerialNo', '')).replace(':', '').upper() == facts['serial'] and
                           item.get('EndDate') == facts['end_date']))
        if page * 100 >= int(result.get('TotalCount', 0)):
            break
        page += 1
    if not matches:
        return None
    expected_name = 'static_cambodianexpress_com_' + facts['serial'][:12].lower()
    named = [item for item in matches if item.get('Name') == expected_name]
    if len(named) == 1:
        return named[0]
    bound = [item for item in matches
             if str(item.get('CertificateId')) == str(current_id)]
    if len(bound) == 1:
        return bound[0]
    if len(matches) == 1:
        return matches[0]
    raise SafeError('ambiguous_matching_certificates_in_cas')


def upload_certificate(credentials, cert_path, key_path, facts):
    with open(cert_path, 'r') as cert_file, open(key_path, 'r') as key_file:
        cert = cert_file.read()
        key = key_file.read()
    name = 'static_cambodianexpress_com_' + facts['serial'][:12].lower()
    token = hashlib.sha256((DOMAIN + facts['serial'] + facts['end_date']).encode('ascii')).hexdigest()
    result = api_call(credentials, CAS_HOST, 'UploadUserCertificate', CAS_VERSION, {
        'RegionId': CDN_REGION, 'Name': name, 'Cert': cert, 'Key': key, 'ClientToken': token,
    }, method='POST')
    cert_id = result.get('CertId')
    if not cert_id:
        raise SafeError('cas_upload_missing_certificate_id')
    return {'CertificateId': cert_id, 'Sha2': facts['sha2'], 'SerialNo': facts['serial'],
            'EndDate': facts['end_date'], 'Name': name}


def verify_public_certificate(expected_sha2):
    ca_file = '/etc/ssl/cert.pem' if os.path.isfile('/etc/ssl/cert.pem') else None
    context = ssl.create_default_context(cafile=ca_file)
    with socket.create_connection((DOMAIN, 443), timeout=20) as raw:
        with context.wrap_socket(raw, server_hostname=DOMAIN) as sock:
            pem = ssl.DER_cert_to_PEM_cert(sock.getpeercert(binary_form=True))
    import tempfile
    fd, path = tempfile.mkstemp(prefix='static-cdn-cert-', suffix='.pem')
    try:
        with os.fdopen(fd, 'w') as handle:
            handle.write(pem)
        der = subprocess.check_output(['openssl', 'x509', '-in', path, '-outform', 'DER'])
        return hashlib.sha256(der).hexdigest().upper() == expected_sha2
    finally:
        os.unlink(path)


def sync(args):
    credentials = read_secure_json(args.credentials)
    cert_path = os.path.join(args.cert_dir, 'fullchain.pem')
    key_path = args.key_path or os.path.join(args.cert_dir, 'privkey.pem')
    facts = certificate_facts(cert_path, key_path)
    current = get_cdn_info(credentials)
    cas_item = find_cas_certificate(credentials, facts, current.get('CertId'))
    if not cas_item and args.dry_run:
        print(json.dumps({'status': 'would_upload_and_bind', 'domain': DOMAIN,
                          'sha2': facts['sha2'], 'end_date': facts['end_date'],
                          'current_cert_id': current.get('CertId')}))
        return
    if not cas_item:
        cas_item = upload_certificate(credentials, cert_path, key_path, facts)
    cert_id = str(cas_item.get('CertificateId') or cas_item.get('CertId'))
    if str(current.get('CertId')) == cert_id and current.get('CertRegion') == CDN_REGION:
        if not verify_public_certificate(facts['cert_sha256']):
            raise SafeError('public_tls_certificate_verification_failed')
        print(json.dumps({'status': 'already_current', 'domain': DOMAIN,
                          'cert_id': cert_id, 'end_date': facts['end_date']}))
        return
    if args.dry_run:
        print(json.dumps({'status': 'would_bind', 'domain': DOMAIN, 'cert_id': cert_id,
                          'current_cert_id': current.get('CertId')}))
        return
    api_call(credentials, CDN_HOST, 'SetCdnDomainSSLCertificate', CDN_VERSION, {
        'DomainName': DOMAIN, 'SSLProtocol': 'on', 'CertType': 'cas',
        'CertId': cert_id, 'CertRegion': CDN_REGION,
    }, method='POST')
    updated = None
    for attempt in range(12):
        time.sleep(10 if attempt else 2)
        updated = get_cdn_info(credentials)
        if (str(updated.get('CertId')) == cert_id and
                updated.get('ServerCertificateStatus') == 'on' and
                verify_public_certificate(facts['cert_sha256'])):
            break
    else:
        raise SafeError('cdn_or_public_tls_verification_failed')
    print(json.dumps({'status': 'synced_and_verified', 'domain': DOMAIN,
                      'cert_id': cert_id, 'previous_cert_id': current.get('CertId'),
                      'end_date': facts['end_date']}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='validate and report planned action')
    parser.add_argument('--apply', action='store_true', help='upload/bind production certificate')
    parser.add_argument('--credentials', default=ACCOUNT_FILE)
    parser.add_argument('--cert-dir', default=CERT_DIR)
    parser.add_argument('--key-path')
    args = parser.parse_args()
    if args.dry_run == args.apply:
        parser.error('specify exactly one of --dry-run or --apply')
    try:
        if os.geteuid() == 0:
            lock_handle = open('/var/lock/static-cdn-sync.lock', 'w')
            try:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except IOError:
                raise SafeError('sync_already_running')
            sync(args)
        else:
            sync(args)
    except (SafeError, IOError, OSError, ValueError, KeyError) as exc:
        message = str(exc) if isinstance(exc, SafeError) else 'local_validation_failed'
        print(json.dumps({'status': 'failed', 'error': message}), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
