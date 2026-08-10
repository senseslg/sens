#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/connect.sh" 'bash -s' <<'REMOTE'
set -u

printf '== identity and operating system ==\n'
date -Is
hostname
if [[ -r /etc/os-release ]]; then
  grep -E '^(PRETTY_NAME|VERSION_ID)=' /etc/os-release
fi
uname -srmo
printf 'timezone: '
timedatectl show -p Timezone --value 2>/dev/null || true
printf 'uptime: '
uptime -p

printf '\n== load and CPU ==\n'
uptime
printf 'logical CPUs: '
nproc

printf '\n== memory ==\n'
free -h
printf 'available memory percent: '
awk '
  /MemTotal:/ {total=$2}
  /MemAvailable:/ {available=$2}
  END {if (total > 0) printf "%.1f%%\n", available * 100 / total}
' /proc/meminfo

printf '\n== filesystems ==\n'
df -hT -x tmpfs -x devtmpfs

printf '\n== selected application processes ==\n'
show_process() {
  local label="$1"
  local pattern="$2"
  local pids
  pids="$(pgrep -f "$pattern" | paste -sd, - || true)"
  if [[ -z "$pids" ]]; then
    printf '%s: not found\n' "$label"
    return
  fi
  printf '%s:\n' "$label"
  ps -p "$pids" -o pid=,ppid=,etimes=,%cpu=,%mem=,rss=,comm=
}

show_process "Mall production" '[m]all-prod\.jar'
show_process "Mall UAT" '[m]all-uat\.jar'
show_process "Nginx" '[n]ginx'
show_process "MinIO" '[m]inio'

printf '\n== selected service units ==\n'
for unit in docker.service nginx.service certbot.timer certbot.service redis-server.service mysql.service; do
  load_state="$(systemctl show "$unit" -p LoadState --value 2>/dev/null || true)"
  active_state="$(systemctl is-active "$unit" 2>/dev/null || true)"
  enabled_state="$(systemctl is-enabled "$unit" 2>/dev/null || true)"
  printf '%-24s load=%-10s active=%-10s enabled=%s\n' \
    "$unit" "${load_state:-unknown}" "${active_state:-unknown}" "${enabled_state:-unknown}"
done

printf '\n== failed systemd units ==\n'
systemctl --failed --no-legend --no-pager 2>/dev/null || true

printf '\n== selected TCP listeners ==\n'
ss -ltn 2>/dev/null |
  awk '
    NR == 1 {print; next}
    $4 ~ /:(22|80|443|3306|6379|8000|8081|8082|9000|9001)$/ {print}
  '

printf '\n== HTTP checks ==\n'
for url in \
  http://127.0.0.1:8081/version \
  http://127.0.0.1:8081/api/version \
  http://127.0.0.1:8082/version \
  http://127.0.0.1:8082/api/version \
  https://admin.cel-mall.com \
  https://admin-uat.cel-mall.com
do
  result="$(curl -sS -m 10 -o /dev/null -w '%{http_code} %{time_total}s' "$url" 2>/dev/null || printf '000 failed')"
  printf '%-48s %s\n' "$url" "$result"
done

printf '\n== TLS certificate dates ==\n'
for host in admin.cel-mall.com admin-uat.cel-mall.com; do
  printf '%s\n' "$host"
  timeout 12 openssl s_client -servername "$host" -connect "$host:443" </dev/null 2>/dev/null |
    openssl x509 -noout -subject -issuer -dates 2>/dev/null ||
    printf 'unable to read certificate\n'
done

printf '\n== notes ==\n'
printf '%s\n' \
  'This report is read-only.' \
  'Complete process arguments, environment variables, logs, and secret files are intentionally excluded.'
REMOTE
