#!/usr/bin/env bash
set -u

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

printf '######## D-Mall server status ########\n'
"$SCRIPT_DIR/status.sh"
status_rc=$?

printf '\n######## D-Mall health check ########\n'
"$SCRIPT_DIR/health-check.sh"
health_rc=$?

if (( status_rc == 0 && health_rc == 0 )); then
  printf '\nDAILY CHECK PASSED\n'
  exit 0
fi

printf '\nDAILY CHECK REQUIRES ATTENTION (status=%s, health=%s)\n' \
  "$status_rc" "$health_rc" >&2
exit 2
