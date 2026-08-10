#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly DISK_WARN_PERCENT="${DISK_WARN_PERCENT:-85}"
readonly LOG_SAMPLE_SECONDS="${LOG_SAMPLE_SECONDS:-5}"

if [[ ! "$DISK_WARN_PERCENT" =~ ^[0-9]+$ ]] || (( DISK_WARN_PERCENT < 1 || DISK_WARN_PERCENT > 100 )); then
  printf 'DISK_WARN_PERCENT must be an integer between 1 and 100.\n' >&2
  exit 1
fi

if [[ ! "$LOG_SAMPLE_SECONDS" =~ ^[0-9]+$ ]] || (( LOG_SAMPLE_SECONDS < 1 || LOG_SAMPLE_SECONDS > 60 )); then
  printf 'LOG_SAMPLE_SECONDS must be an integer between 1 and 60.\n' >&2
  exit 1
fi

"$SCRIPT_DIR/connect.sh" \
  "DISK_WARN_PERCENT=$DISK_WARN_PERCENT LOG_SAMPLE_SECONDS=$LOG_SAMPLE_SECONDS bash -s" <<'REMOTE'
set -u

status=0

printf '== filesystem ==\n'
df -hT /
df -i /

disk_percent="$(df -P / | awk 'NR == 2 {gsub(/%/, "", $5); print $5}')"
if (( disk_percent >= DISK_WARN_PERCENT )); then
  printf 'ALERT: root disk usage is %s%% (threshold %s%%)\n' "$disk_percent" "$DISK_WARN_PERCENT" >&2
  status=2
else
  printf 'OK: root disk usage is %s%% (threshold %s%%)\n' "$disk_percent" "$DISK_WARN_PERCENT"
fi

printf '\n== largest log files (metadata only) ==\n'
find /var/log -maxdepth 3 -type f -printf '%s %TY-%Tm-%Td %p\n' 2>/dev/null \
  | sort -nr \
  | head -n 15 \
  | while read -r bytes modified path
    do
      if command -v numfmt >/dev/null 2>&1; then
        size="$(numfmt --to=iec-i --suffix=B "$bytes")"
      else
        size="$bytes bytes"
      fi
      printf '%10s  %s  %s\n' "$size" "$modified" "$path"
    done

printf '\n== known log footprints ==\n'
for path in /var/log/syslog /var/log/syslog.1 /var/log/journal /var/log/nginx
do
  if [[ -e "$path" ]]; then
    du -sh "$path" 2>/dev/null || true
  fi
done

printf '\n== syslog growth sample ==\n'
if [[ -e /var/log/syslog ]]; then
  before="$(stat -c %s /var/log/syslog 2>/dev/null || printf 0)"
  sleep "$LOG_SAMPLE_SECONDS"
  after="$(stat -c %s /var/log/syslog 2>/dev/null || printf 0)"
  delta=$((after - before))
  bytes_per_second=$((delta / LOG_SAMPLE_SECONDS))
  mib_per_day="$(awk -v rate="$bytes_per_second" 'BEGIN {printf "%.1f", rate * 86400 / 1048576}')"
  printf 'sample_seconds=%s before_bytes=%s after_bytes=%s delta_bytes=%s\n' \
    "$LOG_SAMPLE_SECONDS" "$before" "$after" "$delta"
  printf 'estimated_rate=%s bytes/s (~%s MiB/day if sustained)\n' \
    "$bytes_per_second" "$mib_per_day"
else
  printf '/var/log/syslog not found\n'
fi

printf '\n== result ==\n'
if (( status == 0 )); then
  printf 'DISK WITHIN THRESHOLD\n'
else
  printf 'DISK ATTENTION REQUIRED\n'
fi

exit "$status"
REMOTE
