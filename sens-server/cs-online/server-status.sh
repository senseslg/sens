#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/connect.sh" 'bash -s' <<'REMOTE'
set -u

printf '== server ==\n'
printf 'date: '
date -Is
printf 'host: '
hostname
printf 'os: '
. /etc/os-release
printf '%s\n' "$PRETTY_NAME"
printf 'uptime: '
uptime -p

printf '\n== resources ==\n'
df -hT /
df -i /
free -h

printf '\n== services ==\n'
for unit in \
  chatwoot.target \
  chatwoot-web.1.service \
  chatwoot-worker.1.service \
  postgresql@16-main.service \
  redis-server.service \
  nginx.service \
  hbrclient.service
do
  printf '%-34s %s\n' "$unit" "$(systemctl is-active "$unit" 2>/dev/null || true)"
done
printf '%-34s %s\n' "nginx live process" "$(pgrep -x nginx >/dev/null 2>&1 && printf running || printf missing)"

printf '\n== expected listeners ==\n'
ss -ltn | awk '
  NR == 1 { print; next }
  $4 ~ /:(22|80|443|3000|7433|5432|6379|44089)$/ { print }
'

printf '\n== Chatwoot deployment ==\n'
printf 'path: /home/chatwoot/chatwoot\n'
printf 'version: '
grep -m1 '"version"' /home/chatwoot/chatwoot/package.json 2>/dev/null \
  | sed -E 's/.*"version": "([^"]+)".*/\1/' || printf 'unknown\n'
printf 'branch: '
git -c safe.directory=/home/chatwoot/chatwoot \
  -C /home/chatwoot/chatwoot branch --show-current 2>/dev/null || printf 'unknown\n'
printf 'revision: '
git -c safe.directory=/home/chatwoot/chatwoot \
  -C /home/chatwoot/chatwoot describe --tags --always --dirty 2>/dev/null || printf 'unknown\n'
printf 'worktree changes: '
git -c safe.directory=/home/chatwoot/chatwoot \
  -C /home/chatwoot/chatwoot status --short 2>/dev/null | wc -l | tr -d ' '
printf '\n'

printf '\n== HTTP status ==\n'
for url in \
  http://127.0.0.1:3000 \
  http://127.0.0.1:7433 \
  https://chat.cambodianexpress.com \
  https://superset.cambodianexpress.com
do
  curl_args=()
  if [[ "$url" == https://* ]]; then
    curl_args+=("-k")
  fi
  result="$(curl "${curl_args[@]}" -sS -m 8 -o /dev/null -w '%{http_code} %{time_total}s' "$url" 2>/dev/null || printf '000 failed')"
  printf '%-48s %s\n' "$url" "$result"
done
REMOTE
