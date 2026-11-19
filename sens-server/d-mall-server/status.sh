#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_DIR="${DMALL_PROJECT_DIR:-/home/sens/ce-ssr-app}"

"$SCRIPT_DIR/connect.sh" "PROJECT_DIR='$PROJECT_DIR' bash -s" <<'REMOTE'
set -u

printf '== identity ==\n'
printf 'date:       '; date -Is
printf 'host:       '; hostname
printf 'user:       '; whoami
printf 'uptime:     '; uptime -p
printf 'os:         '; . /etc/os-release && printf '%s %s\n' "$NAME" "$VERSION_ID"
printf 'kernel:     '; uname -r
printf 'timezone:   '; timedatectl show -p Timezone --value 2>/dev/null || true

printf '\n== resources ==\n'
df -hT /
free -h

printf '\n== project ==\n'
if [[ -d "$PROJECT_DIR/.git" ]]; then
  printf 'path:       %s\n' "$PROJECT_DIR"
  printf 'branch:     '; git -C "$PROJECT_DIR" branch --show-current
  printf 'commit:     '; git -C "$PROJECT_DIR" rev-parse HEAD
  printf 'version:    '
  sed -n 's/^[[:space:]]*"version":[[:space:]]*"\([^"]*\)".*/\1/p' \
    "$PROJECT_DIR/package.json" | head -n 1
  printf 'rollback:   '
  if [[ -r "$PROJECT_DIR/.deploy_rollback_ref" ]]; then
    cat "$PROJECT_DIR/.deploy_rollback_ref"
  else
    printf 'not recorded\n'
  fi
  tracked_changes="$(git -C "$PROJECT_DIR" status --short --untracked-files=no)"
  if [[ -n "$tracked_changes" ]]; then
    printf 'tracked changes:\n%s\n' "$tracked_changes"
  else
    printf 'tracked changes: none\n'
  fi
else
  printf 'ERROR: project directory is missing: %s\n' "$PROJECT_DIR" >&2
fi

printf '\n== listeners ==\n'
ss -ltnp 2>/dev/null | grep -E ':(22|80|443|3001|8001)\b' || true

printf '\n== application processes ==\n'
for port in 3001 8001; do
  pids="$(fuser -n tcp "$port" 2>/dev/null || true)"
  if [[ -n "$pids" ]]; then
    printf -- '-- port %s --\n' "$port"
    ps -o pid,etime,%cpu,%mem,comm -p $pids
  else
    printf -- '-- port %s: no owning process found --\n' "$port"
  fi
done

printf '\n== nginx ==\n'
if pgrep -x nginx >/dev/null 2>&1; then
  printf 'process: running\n'
else
  printf 'process: missing\n'
fi
if sudo -n nginx -t >/dev/null 2>&1; then
  printf 'config:  valid\n'
else
  printf 'config:  unavailable or invalid\n'
fi
REMOTE
