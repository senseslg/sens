#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DISK_WARN_PERCENT="${DISK_WARN_PERCENT:-85}"

if [[ ! "$DISK_WARN_PERCENT" =~ ^[0-9]+$ ]] || (( DISK_WARN_PERCENT < 1 || DISK_WARN_PERCENT > 100 )); then
  printf 'DISK_WARN_PERCENT must be an integer between 1 and 100.\n' >&2
  exit 1
fi

"$SCRIPT_DIR/connect.sh" "DISK_WARN_PERCENT=$DISK_WARN_PERCENT bash -s" <<'REMOTE'
set -u

status=0

printf '== identity ==\n'
printf 'date: '
date -Is
printf 'host: '
hostname
printf 'uptime: '
uptime -p

printf '\n== resources ==\n'
df -hT /
free -h

disk_percent="$(df -P / | awk 'NR == 2 {gsub(/%/, "", $5); print $5}')"
if (( disk_percent >= DISK_WARN_PERCENT )); then
  printf 'ALERT: root disk usage is %s%% (threshold %s%%)\n' "$disk_percent" "$DISK_WARN_PERCENT" >&2
  status=2
else
  printf 'OK: root disk usage is %s%% (threshold %s%%)\n' "$disk_percent" "$DISK_WARN_PERCENT"
fi

printf '\n== required services ==\n'
for unit in \
  chatwoot.target \
  chatwoot-web.1.service \
  chatwoot-worker.1.service \
  postgresql@16-main.service \
  redis-server.service \
  hbrclient.service
do
  state="$(systemctl is-active "$unit" 2>/dev/null || true)"
  printf '%-34s %s\n' "$unit" "$state"
  if [[ "$state" != "active" ]]; then
    status=2
  fi
done

nginx_unit="$(systemctl is-active nginx.service 2>/dev/null || true)"
if pgrep -x nginx >/dev/null 2>&1; then
  nginx_process="running"
else
  nginx_process="missing"
  status=2
fi
printf '%-34s %s (live process: %s)\n' "nginx.service" "$nginx_unit" "$nginx_process"
if [[ "$nginx_unit" != "active" ]]; then
  printf 'WARN: Nginx is serving outside the active systemd unit.\n' >&2
fi

printf '\n== HTTP checks ==\n'
check_url() {
  local url="$1"
  local curl_args=()
  if [[ "$url" == https://* ]]; then
    curl_args+=("-k")
  fi

  local output
  output="$(curl "${curl_args[@]}" -sS -m 8 -o /dev/null -w '%{http_code} %{time_total}s' "$url" 2>/dev/null || printf '000 failed')"
  printf '%-48s %s\n' "$url" "$output"
  if [[ "$output" != 200\ * ]]; then
    status=2
  fi
}

check_url "http://127.0.0.1:3000"
check_url "http://127.0.0.1:7433"
check_url "https://chat.cambodianexpress.com"
check_url "https://superset.cambodianexpress.com"

printf '\n== result ==\n'
if (( status == 0 )); then
  printf 'HEALTHY\n'
else
  printf 'ATTENTION REQUIRED\n'
fi

exit "$status"
REMOTE
