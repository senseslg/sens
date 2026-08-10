#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${SENS_PORTAL_ENV_FILE:-$ROOT_DIR/.local-portal/env}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi
RUN_DIR="$ROOT_DIR/.local-portal/run"
LOG_DIR="$ROOT_DIR/.local-portal/log"
PID_FILE="$RUN_DIR/uvicorn.pid"
PLIST_FILE="$RUN_DIR/com.sens.admin-portal.plist"
LOG_FILE="$LOG_DIR/uvicorn.log"
PORT="${SENS_PORTAL_PORT:-8008}"
HOST="${SENS_PORTAL_HOST:-127.0.0.1}"
SCRIPT_PATH="$ROOT_DIR/admin_portal/scripts/portal-local.sh"
LAUNCHD_LABEL="com.sens.admin-portal"
UVICORN_FALLBACK="/Library/Frameworks/Python.framework/Versions/3.11/bin/uvicorn"

mkdir -p "$RUN_DIR" "$LOG_DIR"

health_url() {
  printf 'http://%s:%s/api/health' "$HOST" "$PORT"
}

running_pid() {
  if [[ -f "$PID_FILE" ]]; then
    cat "$PID_FILE"
  fi
}

is_running() {
  curl -fsS --max-time 3 "$(health_url)" >/dev/null 2>&1
}

launchctl_available() {
  [[ "$(uname -s)" == "Darwin" ]] && command -v launchctl >/dev/null 2>&1
}

launchd_loaded() {
  launchctl print "gui/$(id -u)/$LAUNCHD_LABEL" >/dev/null 2>&1
}

write_launchd_plist() {
  local uvicorn_bin="$1"
  cat >"$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LAUNCHD_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$SCRIPT_PATH</string>
    <string>_serve</string>
    <string>$uvicorn_bin</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$LOG_FILE</string>
  <key>StandardErrorPath</key>
  <string>$LOG_FILE</string>
  <key>WorkingDirectory</key>
  <string>$ROOT_DIR</string>
</dict>
</plist>
EOF
}

export_portal_environment() {
  : "${SENS_PORTAL_MYSQL_ROOT_PASSWORD:?Set SENS_PORTAL_MYSQL_ROOT_PASSWORD in the environment or $ENV_FILE}"
  : "${SENS_PORTAL_ADMIN_PASSWORD:?Set SENS_PORTAL_ADMIN_PASSWORD in the environment or $ENV_FILE}"
  : "${SENS_PORTAL_SESSION_SECRET:?Set SENS_PORTAL_SESSION_SECRET in the environment or $ENV_FILE}"
  export SENS_PORTAL_ENABLE_REMOTE_CHECKS="${SENS_PORTAL_ENABLE_REMOTE_CHECKS:-0}"
  export SENS_PORTAL_MYSQL_DIR="${SENS_PORTAL_MYSQL_DIR:-$ROOT_DIR/.local-mysql84}"
  export SENS_PORTAL_MYSQL_SOCKET="${SENS_PORTAL_MYSQL_SOCKET:-$SENS_PORTAL_MYSQL_DIR/run/mysql.sock}"
  export SENS_PORTAL_ADMIN_USERNAME="${SENS_PORTAL_ADMIN_USERNAME:-sens}"
}

start_portal() {
  local uvicorn_bin
  uvicorn_bin="$(command -v uvicorn || true)"
  if [[ -z "$uvicorn_bin" || ! -x "$uvicorn_bin" ]]; then
    uvicorn_bin="$UVICORN_FALLBACK"
  fi

  if [[ ! -x "$uvicorn_bin" ]]; then
    echo "uvicorn not found. Checked: $(command -v uvicorn || true) and $UVICORN_FALLBACK" >&2
    exit 1
  fi

  if is_running; then
    echo "Portal: already running at $(health_url)"
    return 0
  fi

  stop_portal

  export_portal_environment
  if launchctl_available; then
    write_launchd_plist "$uvicorn_bin"
    launchctl bootout "gui/$(id -u)" "$PLIST_FILE" >/dev/null 2>&1 || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST_FILE" >/dev/null 2>&1
    launchctl kickstart -k "gui/$(id -u)/$LAUNCHD_LABEL"
  else
    nohup "$uvicorn_bin" admin_portal.backend.main:app --host "$HOST" --port "$PORT" >"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"
  fi

  local i
  for i in $(seq 1 40); do
    if is_running; then
      echo "Portal: started at $(health_url)"
      return 0
    fi
    sleep 1
  done

  echo "Portal did not become ready. Inspect $LOG_FILE." >&2
  exit 1
}

stop_portal() {
  if launchctl_available && launchd_loaded; then
    launchctl bootout "gui/$(id -u)" "$PLIST_FILE" >/dev/null 2>&1 || launchctl remove "$LAUNCHD_LABEL"
  fi
  if [[ -f "$PID_FILE" ]]; then
    kill "$(cat "$PID_FILE")" >/dev/null 2>&1 || true
    rm -f "$PID_FILE"
  fi
  pkill -f "uvicorn admin_portal.backend.main:app --host $HOST --port $PORT" >/dev/null 2>&1 || true

  local i
  for i in $(seq 1 40); do
    if ! is_running; then
      break
    fi
    sleep 0.25
  done
}

status_portal() {
  if is_running; then
    curl -fsS "$(health_url)"
    echo
  else
    echo "Portal: stopped"
    return 1
  fi
}

case "${1:-}" in
  start)
    start_portal
    ;;
  stop)
    stop_portal
    ;;
  status)
    status_portal
    ;;
  restart)
    stop_portal
    start_portal
    ;;
  _serve)
    export_portal_environment
    cd "$ROOT_DIR"
    if [[ -n "${2:-}" && -x "$2" ]]; then
      exec "$2" admin_portal.backend.main:app --host "$HOST" --port "$PORT"
    fi
    exec "$UVICORN_FALLBACK" admin_portal.backend.main:app --host "$HOST" --port "$PORT"
    ;;
  *)
    cat <<EOF
Usage: $(basename "$0") {start|stop|status|restart}

start    Start the FastAPI backend on 127.0.0.1:8008.
stop     Stop the background backend process.
status   Call the unauthenticated /api/health endpoint.
restart  Stop and start again.
EOF
    exit 1
    ;;
esac
