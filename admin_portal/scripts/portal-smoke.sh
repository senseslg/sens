#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${SENS_PORTAL_ENV_FILE:-$ROOT_DIR/.local-portal/env}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi
: "${SENS_PORTAL_ADMIN_PASSWORD:?Set SENS_PORTAL_ADMIN_PASSWORD in the environment or $ENV_FILE}"
ADMIN_USERNAME="${SENS_PORTAL_ADMIN_USERNAME:-sens}"
ADMIN_PASSWORD="$SENS_PORTAL_ADMIN_PASSWORD"
MYSQL_SCRIPT="$ROOT_DIR/admin_portal/scripts/mysql-local.sh"
PORTAL_SCRIPT="$ROOT_DIR/admin_portal/scripts/portal-local.sh"
COOKIE_JAR="$ROOT_DIR/.local-portal/run/cookies.txt"
TEMP_COOKIE_JAR="$ROOT_DIR/.local-portal/run/temp-cookies.txt"
TEMP_USER_ID=""
TEMP_USERNAME=""
TEMP_PASSWORD_1="TmpPass123"
TEMP_PASSWORD_2="TmpPass456"

cleanup() {
  if [[ -n "$TEMP_USER_ID" && -f "$COOKIE_JAR" ]]; then
    curl -fsS -b "$COOKIE_JAR" -X DELETE "http://127.0.0.1:8008/api/users/$TEMP_USER_ID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

"$MYSQL_SCRIPT" init >/dev/null
"$PORTAL_SCRIPT" start >/dev/null

mkdir -p "$(dirname "$COOKIE_JAR")"
rm -f "$COOKIE_JAR"
rm -f "$TEMP_COOKIE_JAR"

TEMP_USERNAME="qa_$(date +%s)"
LOGIN_PAYLOAD="$(python3 - "$ADMIN_USERNAME" "$ADMIN_PASSWORD" <<'PY'
import json
import sys

print(json.dumps({"username": sys.argv[1], "password": sys.argv[2]}))
PY
)"

curl -fsS "http://127.0.0.1:8008/api/health" >/tmp/admin_portal_health.json
curl -fsS -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -d "$LOGIN_PAYLOAD" \
  http://127.0.0.1:8008/api/login >/tmp/admin_portal_login.json
curl -fsS -b "$COOKIE_JAR" -c "$COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$TEMP_USERNAME\",\"display_name\":\"QA User\",\"password\":\"$TEMP_PASSWORD_1\",\"is_active\":true}" \
  http://127.0.0.1:8008/api/users >/tmp/admin_portal_create_user.json

TEMP_USER_ID="$(python3 - <<'PY'
import json
from pathlib import Path
print(json.loads(Path("/tmp/admin_portal_create_user.json").read_text())["user"]["id"])
PY
)"

curl -fsS -c "$TEMP_COOKIE_JAR" -b "$TEMP_COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$TEMP_USERNAME\",\"password\":\"$TEMP_PASSWORD_1\"}" \
  http://127.0.0.1:8008/api/login >/dev/null
curl -fsS -b "$COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -d "{\"password\":\"$TEMP_PASSWORD_2\"}" \
  http://127.0.0.1:8008/api/users/$TEMP_USER_ID/password >/dev/null
curl -fsS -c "$TEMP_COOKIE_JAR" -b "$TEMP_COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$TEMP_USERNAME\",\"password\":\"$TEMP_PASSWORD_2\"}" \
  http://127.0.0.1:8008/api/login >/dev/null
curl -fsS -b "$COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -X PUT \
  -d '{"display_name":"QA User Updated","is_active":false}' \
  http://127.0.0.1:8008/api/users/$TEMP_USER_ID >/dev/null

if curl -fsS -c "$TEMP_COOKIE_JAR" -b "$TEMP_COOKIE_JAR" \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"$TEMP_USERNAME\",\"password\":\"$TEMP_PASSWORD_2\"}" \
  http://127.0.0.1:8008/api/login >/dev/null 2>&1; then
  echo "deactivated login unexpectedly succeeded" >&2
  exit 1
fi

curl -fsS -b "$COOKIE_JAR" -X DELETE "http://127.0.0.1:8008/api/users/$TEMP_USER_ID" >/dev/null
curl -fsS -b "$COOKIE_JAR" http://127.0.0.1:8008/api/dashboard >/tmp/admin_portal_dashboard.json

python3 - <<'PY'
import json
from pathlib import Path

health = json.loads(Path("/tmp/admin_portal_health.json").read_text())
login = json.loads(Path("/tmp/admin_portal_login.json").read_text())
dashboard = json.loads(Path("/tmp/admin_portal_dashboard.json").read_text())

print(f"health={health['local']['health']}")
print(f"login={login['username']}")
print("user_management=ok")
print(
    "services="
    f"{dashboard['summary']['service_count']} "
    f"warning={dashboard['summary']['warning_count']} "
    f"archive={dashboard['summary']['archive_count']}"
)
PY
