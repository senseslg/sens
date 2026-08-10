#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DISK_WARN_PERCENT="${DISK_WARN_PERCENT:-85}"
readonly MEMORY_WARN_PERCENT="${MEMORY_WARN_PERCENT:-10}"
readonly CERT_WARN_DAYS="${CERT_WARN_DAYS:-21}"

for value_name in DISK_WARN_PERCENT MEMORY_WARN_PERCENT CERT_WARN_DAYS; do
  value="${!value_name}"
  if [[ ! "$value" =~ ^[0-9]+$ ]]; then
    printf '%s must be a non-negative integer.\n' "$value_name" >&2
    exit 1
  fi
done

if (( DISK_WARN_PERCENT < 1 || DISK_WARN_PERCENT > 100 )); then
  printf 'DISK_WARN_PERCENT must be between 1 and 100.\n' >&2
  exit 1
fi
if (( MEMORY_WARN_PERCENT > 100 )); then
  printf 'MEMORY_WARN_PERCENT must be between 0 and 100.\n' >&2
  exit 1
fi

"$SCRIPT_DIR/connect.sh" \
  "DISK_WARN_PERCENT=$DISK_WARN_PERCENT MEMORY_WARN_PERCENT=$MEMORY_WARN_PERCENT CERT_WARN_DAYS=$CERT_WARN_DAYS bash -s" <<'REMOTE'
set -u

status=0

mark_failed() {
  status=2
}

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
  mark_failed
else
  printf 'OK: root disk usage is %s%% (threshold %s%%)\n' "$disk_percent" "$DISK_WARN_PERCENT"
fi

memory_total="$(awk '/MemTotal:/ {print $2}' /proc/meminfo)"
memory_available="$(awk '/MemAvailable:/ {print $2}' /proc/meminfo)"
memory_available_percent=$((memory_available * 100 / memory_total))
if (( memory_available_percent <= MEMORY_WARN_PERCENT )); then
  printf 'ALERT: available memory is %s%% (threshold %s%%)\n' "$memory_available_percent" "$MEMORY_WARN_PERCENT" >&2
  mark_failed
else
  printf 'OK: available memory is %s%% (threshold %s%%)\n' "$memory_available_percent" "$MEMORY_WARN_PERCENT"
fi

printf '\n== required processes ==\n'
check_process() {
  local label="$1"
  local pattern="$2"
  local pid
  pid="$(pgrep -f "$pattern" | head -n 1 || true)"
  if [[ -z "$pid" ]]; then
    printf '%-24s missing\n' "$label"
    mark_failed
    return
  fi
  printf '%-24s running (pid %s)\n' "$label" "$pid"
}

check_process "Mall production" '[m]all-prod\.jar'
check_process "Mall UAT" '[m]all-uat\.jar'

if pgrep -x nginx >/dev/null 2>&1; then
  printf '%-24s running\n' "Nginx"
else
  printf '%-24s missing\n' "Nginx"
  mark_failed
fi

docker_state="$(systemctl is-active docker.service 2>/dev/null || true)"
printf '%-24s %s\n' "Docker service" "$docker_state"
if [[ "$docker_state" != "active" ]]; then
  mark_failed
fi

printf '\n== HTTP checks ==\n'
check_url() {
  local url="$1"
  local output
  output="$(curl -sS -m 10 -o /dev/null -w '%{http_code} %{time_total}s' "$url" 2>/dev/null || printf '000 failed')"
  printf '%-48s %s\n' "$url" "$output"
  if [[ "$output" != 200\ * ]]; then
    mark_failed
  fi
}

check_url "http://127.0.0.1:8081/version"
check_url "http://127.0.0.1:8082/version"
check_url "https://admin.cel-mall.com"
check_url "https://admin-uat.cel-mall.com"

printf '\n== TLS certificates ==\n'
check_certificate() {
  local host="$1"
  local end_date
  local end_epoch
  local now_epoch
  local days_left

  end_date="$(
    timeout 12 openssl s_client -servername "$host" -connect "$host:443" </dev/null 2>/dev/null |
      openssl x509 -noout -enddate 2>/dev/null |
      sed 's/^notAfter=//'
  )"
  if [[ -z "$end_date" ]]; then
    printf '%-32s unable to read certificate\n' "$host"
    mark_failed
    return
  fi

  end_epoch="$(date -d "$end_date" +%s 2>/dev/null || printf '0')"
  now_epoch="$(date +%s)"
  days_left=$(((end_epoch - now_epoch) / 86400))
  printf '%-32s %s days remaining (%s)\n' "$host" "$days_left" "$end_date"
  if (( days_left <= CERT_WARN_DAYS )); then
    printf 'ALERT: %s certificate expires within %s days.\n' "$host" "$CERT_WARN_DAYS" >&2
    mark_failed
  fi
}

check_certificate "admin.cel-mall.com"
check_certificate "admin-uat.cel-mall.com"

printf '\n== result ==\n'
if (( status == 0 )); then
  printf 'HEALTHY\n'
else
  printf 'ATTENTION REQUIRED\n'
fi

exit "$status"
REMOTE
