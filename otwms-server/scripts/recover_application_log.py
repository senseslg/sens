#!/usr/bin/env python3
"""Bounded emergency log truncation over SSH; dry-run unless --execute.

Only targets /root/otwms-backend.log. Preserves and verifies its last 50 MiB
in /run before truncation. Does not restart Java, delete temp files, or install
automatic cleanup. Earlier log content is irreversibly discarded on execution.
"""
import argparse
import subprocess
import sys

REMOTE = r'''
import datetime, gzip, hashlib, json, os, shutil, socket, stat
expected_host = EXPECTED_HOST
execute = EXECUTE
if socket.gethostname() != expected_host:
    raise RuntimeError("hostname mismatch")
path = "/root/otwms-backend.log"
fd = os.open(path, (os.O_RDWR if execute else os.O_RDONLY) | os.O_NOFOLLOW)
try:
    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise RuntimeError("not an unaliased regular log")
    holders = []
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            with open('/proc/' + pid + '/comm') as f:
                if f.read().strip() != 'java':
                    continue
            value = os.stat('/proc/' + pid + '/fd/1')
            if (value.st_dev, value.st_ino) == (before.st_dev, before.st_ino):
                holders.append(int(pid))
        except OSError:
            continue
    if not holders:
        raise RuntimeError("no Java stdout owns target inode")
    def disk():
        d = os.statvfs('/')
        return {'free_bytes': d.f_bavail*d.f_frsize,
                'used_percent': round(100*(d.f_blocks-d.f_bavail)/d.f_blocks, 2)}
    print(json.dumps({'execute':execute, 'host':expected_host, 'physical_before':before.st_blocks*512,
                      'logical_before':before.st_size, 'java_pids':holders, 'disk_before':disk()}), flush=True)
    if execute:
        if before.st_blocks*512 < 10*1024**3:
            raise RuntimeError('log below 10 GiB emergency threshold')
        if os.stat('/run').st_dev == before.st_dev:
            raise RuntimeError('/run must be a separate filesystem')
        size = min(before.st_size, 50*1024**2)
        if shutil.disk_usage('/run').free < size + 16*1024**2:
            raise RuntimeError('insufficient /run space for evidence')
        data = os.pread(fd, size, before.st_size-size)
        if len(data) != size:
            raise RuntimeError('short evidence read')
        digest = hashlib.sha256(data).hexdigest()
        stamp = datetime.datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%z')
        filename = 'otwms-backend-tail-' + stamp + '.log.gz'
        staging = '/run/' + filename
        output = os.open(staging, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with os.fdopen(output, 'wb') as raw:
            with gzip.GzipFile(fileobj=raw, mode='wb') as zipped:
                zipped.write(data)
            raw.flush()
            os.fsync(raw.fileno())
        with gzip.open(staging, 'rb') as saved:
            if saved.read() != data:
                raise RuntimeError('compressed evidence mismatch; no truncation')
        current = os.stat(path, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (before.st_dev, before.st_ino):
            raise RuntimeError('log rotated; no truncation')
        os.ftruncate(fd, 0)
        os.fsync(fd)
        print(json.dumps({'truncated':True, 'evidence_staging':staging, 'tail_bytes':size,
                          'tail_sha256':digest, 'disk_after':disk()}), flush=True)
        destination = '/root/' + filename
        destination_fd = os.open(destination, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
        with open(staging, 'rb') as source, os.fdopen(destination_fd, 'wb') as target:
            shutil.copyfileobj(source, target)
            target.flush()
            os.fsync(target.fileno())
        with gzip.open(destination, 'rb') as saved:
            if hashlib.sha256(saved.read()).hexdigest() != digest:
                raise RuntimeError('permanent evidence verification failed; /run copy retained')
        os.unlink(staging)
        print(json.dumps({'evidence':destination, 'compressed_bytes':os.stat(destination).st_size,
                          'permissions':oct(stat.S_IMODE(os.stat(destination).st_mode)),
                          'disk_final':disk()}), flush=True)
finally:
    os.close(fd)
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', required=True)
    p.add_argument('--zone', required=True)
    p.add_argument('--instance', required=True)
    p.add_argument('--execute', action='store_true')
    args = p.parse_args()
    source = REMOTE.replace('EXPECTED_HOST', repr(args.instance)).replace('EXECUTE', repr(args.execute))
    result = subprocess.run(
        ['gcloud', 'compute', 'ssh', args.instance, '--project', args.project,
         '--zone', args.zone, '--command', 'sudo python3 -'],
        input=source, text=True, timeout=90, check=False)
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
