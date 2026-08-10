#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_DIR="${DMALL_PROJECT_DIR:-/home/sens/ce-ssr-app}"
readonly DISK_WARN_PERCENT="${DISK_WARN_PERCENT:-85}"
readonly MEMORY_WARN_PERCENT="${MEMORY_WARN_PERCENT:-10}"

for value_name in DISK_WARN_PERCENT MEMORY_WARN_PERCENT; do
  value="${!value_name}"
  if [[ ! "$value" =~ ^[0-9]+$ ]] || (( value < 1 || value > 100 )); then
    printf '%s must be an integer between 1 and 100.\n' "$value_name" >&2
    exit 1
  fi
done

"$SCRIPT_DIR/connect.sh" \
  "PROJECT_DIR='$PROJECT_DIR' DISK_WARN_PERCENT=$DISK_WARN_PERCENT MEMORY_WARN_PERCENT=$MEMORY_WARN_PERCENT bash -s" <<'REMOTE'
set -u

status=0

printf '== identity ==\n'
printf 'date:   '; date -Is
printf 'host:   '; hostname
printf 'uptime: '; uptime -p

printf '\n== resources ==\n'
df -hT /
free -h

disk_percent="$(df -P / | awk 'NR == 2 {gsub(/%/, "", $5); print $5}')"
if (( disk_percent >= DISK_WARN_PERCENT )); then
  printf 'ALERT: root disk usage is %s%% (threshold %s%%)\n' \
    "$disk_percent" "$DISK_WARN_PERCENT" >&2
  status=2
else
  printf 'OK: root disk usage is %s%% (threshold %s%%)\n' \
    "$disk_percent" "$DISK_WARN_PERCENT"
fi

memory_available_percent="$(
  awk '
    /^MemTotal:/ { total=$2 }
    /^MemAvailable:/ { available=$2 }
    END { if (total > 0) printf "%d", available * 100 / total; else print 0 }
  ' /proc/meminfo
)"
if (( memory_available_percent < MEMORY_WARN_PERCENT )); then
  printf 'ALERT: available memory is %s%% (minimum %s%%)\n' \
    "$memory_available_percent" "$MEMORY_WARN_PERCENT" >&2
  status=2
else
  printf 'OK: available memory is %s%% (minimum %s%%)\n' \
    "$memory_available_percent" "$MEMORY_WARN_PERCENT"
fi

printf '\n== project ==\n'
if [[ -d "$PROJECT_DIR/.git" ]]; then
  printf 'commit:   '; git -C "$PROJECT_DIR" rev-parse HEAD
  printf 'branch:   '; git -C "$PROJECT_DIR" branch --show-current
  printf 'rollback: '
  if [[ -r "$PROJECT_DIR/.deploy_rollback_ref" ]]; then
    cat "$PROJECT_DIR/.deploy_rollback_ref"
  else
    printf 'not recorded\n'
  fi
else
  printf 'ALERT: project directory is missing: %s\n' "$PROJECT_DIR" >&2
  status=2
fi

printf '\n== required listeners ==\n'
for port in 3001 8001; do
  if ss -ltn 2>/dev/null | grep -qE ":${port}\\b"; then
    printf 'OK: port %s is listening\n' "$port"
  else
    printf 'ALERT: port %s is not listening\n' "$port" >&2
    status=2
  fi
done

printf '\n== nginx ==\n'
if pgrep -x nginx >/dev/null 2>&1; then
  printf 'OK: Nginx process is running\n'
else
  printf 'ALERT: Nginx process is missing\n' >&2
  status=2
fi
if sudo -n nginx -t >/dev/null 2>&1; then
  printf 'OK: Nginx configuration is valid\n'
else
  printf 'ALERT: Nginx configuration check failed or sudo is unavailable\n' >&2
  status=2
fi

printf '\n== HTTP checks ==\n'
check_url() {
  local url="$1"
  local output
  output="$(curl -sS -m 8 -o /dev/null -w '%{http_code} %{time_total}s' \
    "$url" 2>/dev/null || printf '000 failed')"
  printf '%-52s %s\n' "$url" "$output"
  if [[ "$output" != 200\ * ]]; then
    status=2
  fi
}

check_url 'http://127.0.0.1:3001/'
check_url 'http://127.0.0.1:8001/docs'
check_url 'https://ce-ssr-app.ceccsl.com/'

printf '\n== result ==\n'
if (( status == 0 )); then
  printf 'HEALTHY\n'
else
  printf 'ATTENTION REQUIRED\n'
fi

exit "$status"
REMOTE
