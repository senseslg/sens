#!/usr/bin/env python3
"""只读调用公司 Bitbucket（4.0.2）REST API。

Bitbucket 4.0.2 没有个人访问令牌，只能用账号密码（Basic 认证）。凭据放在 Git 忽略的
../.local/config.json（权限必须为 600），或环境变量 BITBUCKET_USERNAME / BITBUCKET_PASSWORD。
本脚本只发 GET 请求，不创建、合并、删除或修改任何内容。

用法：
  python3 bitbucket_api.py init                                  # 生成本地配置（不含密码）
  python3 bitbucket_api.py check                                 # 连通性与认证
  python3 bitbucket_api.py projects
  python3 bitbucket_api.py repos [--project CCSL]
  python3 bitbucket_api.py branches --repo CCSL/ccsl-backend [--filter qa]
  python3 bitbucket_api.py commits  --repo CCSL/ccsl-backend [--branch qa] [-n 10]
  python3 bitbucket_api.py contains --repo CCSL/ccsl-backend --commit <sha>   # 提交在哪些分支
  python3 bitbucket_api.py prs      --repo CCSL/ccsl-backend [--state OPEN|MERGED|DECLINED|ALL]
  python3 bitbucket_api.py users    [--all]                      # 默认只列启用账号（需管理员）
  python3 bitbucket_api.py groups
  python3 bitbucket_api.py perms    --project CCSL [--repo ccsl-backend]
  python3 bitbucket_api.py whitelist --allow sens,huzw,...       # 启用账号与白名单比对
任意子命令可加 --json 输出原始结构。

退出码：0 成功；1 请求失败或白名单有多余账号；2 参数或配置错误。
"""
import argparse
import base64
import json
import os
import ssl
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = Path(os.environ.get('BITBUCKET_SERVICE_CONFIG', ROOT / '.local' / 'config.json'))
DEFAULT_BASE = 'https://code.cambodianexpress.com'
SSL_CTX = None
REPO_PART = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-~')


def fail(msg, code=2):
    print(msg, file=sys.stderr)
    sys.exit(code)


def load_config():
    cfg = {}
    if CONFIG.exists():
        if os.name != 'nt' and CONFIG.stat().st_mode & 0o077:
            fail(f'配置权限过宽，请执行 chmod 600 {CONFIG}')
        cfg = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
    base = os.environ.get('BITBUCKET_BASE_URL') or cfg.get('BITBUCKET_BASE_URL') or DEFAULT_BASE
    user = os.environ.get('BITBUCKET_USERNAME') or cfg.get('BITBUCKET_USERNAME')
    pw = os.environ.get('BITBUCKET_PASSWORD') or cfg.get('BITBUCKET_PASSWORD')
    if not base.startswith('https://'):
        fail('BITBUCKET_BASE_URL 必须是 https 地址')
    return base.rstrip('/'), user, pw


def ssl_context():
    """始终校验证书；python.org 版 Python 无 CA 时依次用 certifi、macOS 系统证书。"""
    ctx = ssl.create_default_context()
    if ctx.cert_store_stats().get('x509_ca'):
        return ctx
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    if Path('/etc/ssl/cert.pem').exists():
        return ssl.create_default_context(cafile='/etc/ssl/cert.pem')
    return ctx


class Client:
    def __init__(self, base, user, pw):
        self.base = base
        self.auth = None
        if user and pw:
            self.auth = 'Basic ' + base64.b64encode(f'{user}:{pw}'.encode()).decode()

    def get(self, path, params=None, need_auth=True):
        if need_auth and not self.auth:
            fail(f'缺少凭据：在 {CONFIG} 填写 BITBUCKET_PASSWORD，或设置环境变量')
        url = self.base + path + ('?' + urllib.parse.urlencode(params) if params else '')
        req = urllib.request.Request(url, headers={'Accept': 'application/json'})
        if self.auth:
            req.add_header('Authorization', self.auth)
        try:
            with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as r:
                return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            detail = ''
            try:
                detail = '; '.join(x.get('message', '') for x in json.loads(e.read()).get('errors', []))
            except (ValueError, AttributeError):
                pass
            msg = {401: '认证失败（账号或密码错误，多次失败可能触发验证码）',
                   403: '无权限（该接口可能需要管理员）', 404: '不存在'}.get(e.code, '')
            fail(f'HTTP {e.code} {msg} {detail}'.strip(), 1)
        except urllib.error.URLError as e:
            fail(f'连接失败：{e.reason}', 1)

    def paged(self, path, params=None, limit=None):
        params, out, start = dict(params or {}), [], 0
        while True:
            params.update(start=start, limit=min(100, limit or 100))
            page = self.get(path, params)
            out.extend(page.get('values', []))
            if page.get('isLastPage', True) or (limit and len(out) >= limit):
                return out[:limit] if limit else out
            start = page['nextPageStart']


def seg(value):
    if not value or any(c not in REPO_PART for c in value):
        fail(f'非法名称：{value!r}')
    return value


def repo_path(repo):
    if '/' not in repo:
        fail('--repo 格式为 项目KEY/仓库slug，如 CCSL/ccsl-backend')
    p, r = repo.split('/', 1)
    return f'/rest/api/1.0/projects/{seg(p)}/repos/{seg(r)}'


def show(rows, as_json, fmt):
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            print(fmt(row))
        print(f'共 {len(rows)} 条', file=sys.stderr)


def cmd_init(_a, _c):
    if CONFIG.exists():
        print('本地配置已存在，未覆盖')
        return 0
    CONFIG.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(CONFIG, os.O_WRONLY | os.O_CREAT | os.O_EXCL, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        json.dump({'BITBUCKET_BASE_URL': DEFAULT_BASE, 'BITBUCKET_USERNAME': 'sens',
                   'BITBUCKET_PASSWORD': ''}, f, indent=2)
    print(f'已生成 {CONFIG}（600）；请本人填写 BITBUCKET_PASSWORD，不要提交或贴到聊天')
    return 0


def cmd_check(a, c):
    info = c.get('/rest/api/1.0/application-properties', need_auth=False)
    print(f"Bitbucket {info.get('version')} 可访问")
    me = c.get('/rest/api/1.0/users/' + urllib.parse.quote(load_config()[1] or ''))
    print(f"认证成功：{me.get('name')}（{me.get('displayName')}）")
    return 0


def cmd_projects(a, c):
    show(c.paged('/rest/api/1.0/projects'), a.json, lambda p: f"{p['key']:<12} {p['name']}")


def cmd_repos(a, c):
    path = f'/rest/api/1.0/projects/{seg(a.project)}/repos' if a.project else '/rest/api/1.0/repos'
    show(c.paged(path), a.json, lambda r: f"{r['project']['key']}/{r['slug']}")


def cmd_branches(a, c):
    params = {'filterText': a.filter} if a.filter else {}
    show(c.paged(repo_path(a.repo) + '/branches', params), a.json,
         lambda b: f"{b['displayId']:<40} {b['latestCommit'][:12]}{'  (默认)' if b.get('isDefault') else ''}")


def cmd_commits(a, c):
    params = {'until': a.branch} if a.branch else {}
    from datetime import datetime
    show(c.paged(repo_path(a.repo) + '/commits', params, limit=a.n), a.json,
         lambda m: f"{m['displayId']}  {datetime.fromtimestamp(m['authorTimestamp'] / 1000):%Y-%m-%d %H:%M}  "
                   f"{m['author'].get('name', '')}  {m['message'].splitlines()[0][:80]}")


def cmd_contains(a, c):
    if not all(ch in '0123456789abcdefABCDEF' for ch in a.commit) or len(a.commit) < 7:
        fail('--commit 需要至少 7 位十六进制提交号')
    rest = repo_path(a.repo).replace('/rest/api/1.0/', '/rest/branch-utils/1.0/', 1)
    rows = c.paged(f'{rest}/branches/info/{a.commit}')
    show(rows, a.json, lambda b: b['displayId'])


def cmd_prs(a, c):
    from datetime import datetime
    show(c.paged(repo_path(a.repo) + '/pull-requests', {'state': a.state, 'order': 'NEWEST'}, limit=a.n), a.json,
         lambda p: f"#{p['id']:<5} {p['state']:<8} {p['fromRef']['displayId']} → {p['toRef']['displayId']}  "
                   f"{p['author']['user']['name']}  {datetime.fromtimestamp(p['updatedDate'] / 1000):%Y-%m-%d}  "
                   f"{p['title'][:60]}")


def active_users(c, include_all=False):
    users = c.paged('/rest/api/1.0/admin/users')
    return users if include_all else [u for u in users if u.get('active', True)]


def cmd_users(a, c):
    show(active_users(c, a.all), a.json,
         lambda u: f"{u['name']:<28} {'启用' if u.get('active', True) else '停用'}  "
                   f"{u.get('displayName', '')}  {u.get('emailAddress', '')}")


def cmd_groups(a, c):
    show(c.paged('/rest/api/1.0/admin/groups'), a.json, lambda g: g['name'])


def cmd_perms(a, c):
    base = f'/rest/api/1.0/projects/{seg(a.project)}' + (f'/repos/{seg(a.repo)}' if a.repo else '')
    rows = [{'type': '组', 'name': x['group']['name'], 'permission': x['permission']}
            for x in c.paged(base + '/permissions/groups')]
    rows += [{'type': '用户', 'name': x['user']['name'], 'permission': x['permission']}
             for x in c.paged(base + '/permissions/users')]
    show(rows, a.json, lambda x: f"{x['type']}  {x['name']:<28} {x['permission']}")


def cmd_whitelist(a, c):
    allow = {x.strip().lower() for x in a.allow.split(',') if x.strip()}
    extra = sorted(u['name'] for u in active_users(c) if u['name'].lower() not in allow)
    print('白名单外的启用账号：' + (', '.join(extra) if extra else '无'))
    return 1 if extra else 0


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument('--json', action='store_true', help='输出 JSON')
    ap = argparse.ArgumentParser(description='Bitbucket 只读接口（code.cambodianexpress.com）')
    sub = ap.add_subparsers(dest='cmd', required=True)
    _add = sub.add_parser
    sub.add_parser = lambda *x, **k: _add(*x, parents=[common], **k)
    sub.add_parser('init', help='生成本地配置（不含密码）')
    sub.add_parser('check', help='连通性与认证')
    sub.add_parser('projects')
    s = sub.add_parser('repos'); s.add_argument('--project')
    s = sub.add_parser('branches'); s.add_argument('--repo', required=True); s.add_argument('--filter')
    s = sub.add_parser('commits'); s.add_argument('--repo', required=True); s.add_argument('--branch')
    s.add_argument('-n', type=int, default=10)
    s = sub.add_parser('contains', help='提交所在分支'); s.add_argument('--repo', required=True)
    s.add_argument('--commit', required=True)
    s = sub.add_parser('prs'); s.add_argument('--repo', required=True)
    s.add_argument('--state', default='OPEN', choices=['OPEN', 'MERGED', 'DECLINED', 'ALL'])
    s.add_argument('-n', type=int, default=20)
    s = sub.add_parser('users'); s.add_argument('--all', action='store_true', help='包含停用账号')
    sub.add_parser('groups')
    s = sub.add_parser('perms'); s.add_argument('--project', required=True); s.add_argument('--repo')
    s = sub.add_parser('whitelist'); s.add_argument('--allow', required=True, help='逗号分隔用户名')
    a = ap.parse_args()
    if a.cmd == 'init':
        return cmd_init(a, None)
    global SSL_CTX
    SSL_CTX = ssl_context()
    client = Client(*load_config())
    return globals()['cmd_' + a.cmd](a, client) or 0


if __name__ == '__main__':
    sys.exit(main())
