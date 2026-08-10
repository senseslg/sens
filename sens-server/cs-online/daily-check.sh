#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SAVE_REPORTS="${SAVE_REPORTS:-1}"
readonly REPORT_DIR="${REPORT_DIR:-$SCRIPT_DIR/reports}"

if [[ "$SAVE_REPORTS" != "0" && "$SAVE_REPORTS" != "1" ]]; then
  printf 'SAVE_REPORTS must be 0 or 1.\n' >&2
  exit 1
fi

run_checks() {
  local health_status
  local disk_status

  printf 'cs-online daily check\n'
  printf 'local_time=%s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')"

  printf '\n######## HEALTH ########\n'
  set +e
  "$SCRIPT_DIR/health-check.sh"
  health_status=$?

  printf '\n######## DISK AND LOGS ########\n'
  "$SCRIPT_DIR/disk-log-check.sh"
  disk_status=$?
  set -e

  printf '\n######## SUMMARY ########\n'
  printf 'health_exit=%s disk_log_exit=%s\n' "$health_status" "$disk_status"

  if (( health_status == 0 && disk_status == 0 )); then
    printf 'DAILY CHECK PASSED\n'
    return 0
  fi

  printf 'DAILY CHECK REQUIRES ATTENTION\n'
  return 2
}

if [[ "$SAVE_REPORTS" == "1" ]]; then
  mkdir -p "$REPORT_DIR"
  readonly REPORT_FILE="$REPORT_DIR/$(date '+%Y%m%d-%H%M%S').txt"

  set +e
  run_checks 2>&1 | tee "$REPORT_FILE"
  status="${PIPESTATUS[0]}"
  set -e

  printf '\nSaved report: %s\n' "$REPORT_FILE"
  exit "$status"
fi

run_checks
