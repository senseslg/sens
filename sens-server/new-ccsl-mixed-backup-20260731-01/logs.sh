#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_DIR="${NEW_CCSL_PROJECT_DIR:-/home/sens/ce-ssr-app}"
readonly TARGET="${1:-both}"
readonly LINES="${2:-80}"

if [[ "$TARGET" != "frontend" && "$TARGET" != "backend" && "$TARGET" != "both" ]]; then
  printf 'Usage: %s [frontend|backend|both] [lines]\n' "$0" >&2
  exit 1
fi
if [[ ! "$LINES" =~ ^[0-9]+$ ]] || (( LINES < 1 || LINES > 1000 )); then
  printf 'lines must be an integer between 1 and 1000.\n' >&2
  exit 1
fi

"$SCRIPT_DIR/connect.sh" \
  "PROJECT_DIR='$PROJECT_DIR' TARGET='$TARGET' LINES=$LINES bash -s" <<'REMOTE'
set -u

show_log() {
  local label="$1"
  local path="$2"
  printf '== %s: %s ==\n' "$label" "$path"
  if [[ -r "$path" ]]; then
    tail -n "$LINES" "$path"
  else
    printf 'Log is missing or unreadable.\n' >&2
  fi
}

case "$TARGET" in
  frontend)
    show_log frontend "$PROJECT_DIR/frontend.log"
    ;;
  backend)
    show_log backend "$PROJECT_DIR/backend.log"
    ;;
  both)
    show_log backend "$PROJECT_DIR/backend.log"
    printf '\n'
    show_log frontend "$PROJECT_DIR/frontend.log"
    ;;
esac
REMOTE
