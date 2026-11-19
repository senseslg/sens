#!/usr/bin/env python3
"""只读查询 wms-db 上 Jenkins 的任务、构建结果和构建日志。

通过 gcloud IAP SSH 登录 wms-db，读取 Jenkins 数据卷中的文件；不调用 Jenkins API，
不触发、取消或修改任何构建。

用法（同一个脚本，macOS 与 Windows 都可直接调用，系统差异见 PLATFORM_PROFILES 与 README）：
  macOS：  python3 jenkins_builds.py list --job ccsl/uat/ccsl-backend-uat [-n 5]
  Windows：python  jenkins_builds.py list --job ccsl/uat/ccsl-backend-uat [-n 5]
  其它子命令：jobs [--folder ccsl]；log --job … --build 2345 [--all] [--tail 80]；platform（只显示本机配置）

退出码：0 成功；1 远端命令失败或缺 gcloud；2 参数错误。
"""
import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys

# ── 按系统分开的配置（新增系统时只加一项，不改其它系统）──────────────────────
# gcloud：按顺序查找的可执行文件名（Windows 的 subprocess 不会自动补 .cmd）。
# encoding：解码远端输出用的编码；None 表示沿用系统默认（macOS 原有行为，默认就是 UTF-8）。
PLATFORM_PROFILES = {
    'mac': {'gcloud': ['gcloud'], 'encoding': None},
    'windows': {'gcloud': ['gcloud.cmd', 'gcloud'], 'encoding': 'utf-8'},
}


def platform_name():
    return 'windows' if os.name == 'nt' else 'mac'


def gcloud_bin(profile):
    """可用环境变量 GCLOUD_BIN 指定 gcloud 路径（任意系统）。"""
    explicit = os.environ.get('GCLOUD_BIN')
    if explicit:
        return explicit
    for name in profile['gcloud']:
        found = shutil.which(name)
        if found:
            return found
    print('未找到 gcloud：请安装 Google Cloud SDK 并执行 gcloud auth login，或设置 GCLOUD_BIN', file=sys.stderr)
    sys.exit(1)


GCLOUD_ARGS = ['compute', 'ssh', 'wms-db',
               '--project=cambodian-express', '--zone=asia-southeast1-a', '--tunnel-through-iap']
JENKINS_JOBS = '/home/daniel/containers/jenkins/jenkins/jobs'
JOB_RE = re.compile(r'^[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$')
# 构建日志关键行：触发人、检出提交、Maven/npm 错误、构建结果
KEY_LINES = (r'Started by|Checking out Revision|Commit message|CONFLICT|\[ERROR\]|ERROR in|'
             r'error:|BUILD (SUCCESS|FAILURE)|npm ERR|Finished:')
NOISE = re.compile(r'numpy|tcp_upload|performance of the tunnel|^WARNING:?\s*$', re.I)
SENSITIVE = re.compile(r'password|passwd|token|secret|authorization|api[_-]?key', re.I)
ANNOTATION = re.compile(r'ha:////[A-Za-z0-9+/=]+')
ANSI = re.compile(r'\x1b\[[0-9;]*m')


def job_dir(job):
    if not JOB_RE.match(job) or '..' in job:
        sys.exit(2)
    return JENKINS_JOBS + '/' + '/jobs/'.join(job.split('/'))


def run_remote(cmd):
    profile = PLATFORM_PROFILES[platform_name()]
    kwargs = {'capture_output': True, 'text': True, 'timeout': 240}
    if profile['encoding']:
        # Windows 默认按系统代码页解码，日志为 UTF-8，显式指定避免乱码或解码异常
        kwargs.update(encoding=profile['encoding'], errors='replace')
    p = subprocess.run([gcloud_bin(profile)] + GCLOUD_ARGS + ['--command', cmd], **kwargs)
    lines = []
    for raw in (p.stdout + p.stderr).splitlines():
        line = ANSI.sub('', ANNOTATION.sub('', raw)).rstrip()
        if not line or NOISE.search(line):
            continue
        lines.append('[已隐藏疑似敏感行]' if SENSITIVE.search(line) else line)
    print('\n'.join(lines))
    return p.returncode


def main():
    ap = argparse.ArgumentParser(description='Jenkins 只读查询（wms-db）')
    sub = ap.add_subparsers(dest='cmd', required=True)
    j = sub.add_parser('jobs', help='列出任务（含 builds 目录的任务路径）')
    j.add_argument('--folder', default='ccsl')
    l = sub.add_parser('list', help='最近构建：编号、结果、完成时间')
    l.add_argument('--job', required=True, help='如 ccsl/uat/ccsl-backend-uat')
    l.add_argument('-n', type=int, default=5)
    g = sub.add_parser('log', help='构建日志；默认只看关键行')
    g.add_argument('--job', required=True)
    g.add_argument('--build', type=int, required=True)
    g.add_argument('--all', action='store_true', help='输出完整日志（仍做脱敏）')
    g.add_argument('--tail', type=int, default=0, help='只看最后 N 行')
    sub.add_parser('platform', help='只显示本机识别的系统、gcloud 路径和解码方式，不连远端')
    a = ap.parse_args()

    if a.cmd == 'platform':
        name = platform_name()
        profile = PLATFORM_PROFILES[name]
        explicit = os.environ.get('GCLOUD_BIN')
        found = explicit or next((shutil.which(n) for n in profile['gcloud'] if shutil.which(n)), None)
        print(f"platform={name} gcloud={found or '未找到'} encoding={profile['encoding'] or '系统默认'}")
        return 0 if found else 1
    if a.cmd == 'jobs':
        base = job_dir(a.folder)
        cmd = (f"sudo -n find {shlex.quote(base)} -maxdepth 6 -name builds -type d "
               f"| sed -e 's#^{JENKINS_JOBS}/##' -e 's#/builds$##' -e 's#/jobs/#/#g' | sort")
    elif a.cmd == 'list':
        b = shlex.quote(job_dir(a.job) + '/builds')
        cmd = (f"for n in $(sudo -n ls {b} | grep -E '^[0-9]+$' | sort -rn | head -{max(1, a.n)}); do "
               f"r=$(sudo -n grep -oE '<result>[A-Z]+</result>' {b}/$n/build.xml 2>/dev/null | sed -E 's#</?result>##g'); "
               f"t=$(sudo -n stat -c %y {b}/$n/build.xml 2>/dev/null | cut -c1-19); "
               f"echo \"#$n ${{r:-RUNNING}} $t\"; done")
    else:
        log = shlex.quote(f"{job_dir(a.job)}/builds/{a.build}/log")
        if a.all or a.tail:
            cmd = f"sudo -n cat {log}" + (f" | tail -n {a.tail}" if a.tail else '')
        else:
            cmd = f"sudo -n grep -aE {shlex.quote(KEY_LINES)} {log} | head -80"
    return 0 if run_remote(cmd) == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
