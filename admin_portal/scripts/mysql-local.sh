#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${SENS_PORTAL_ENV_FILE:-$ROOT_DIR/.local-portal/env}"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi
MYSQL_PREFIX="${SENS_PORTAL_MYSQL_PREFIX:-/opt/homebrew/opt/mysql@8.4}"
MYSQL_DIR="${SENS_PORTAL_MYSQL_DIR:-$ROOT_DIR/.local-mysql84}"
DATA_DIR="$MYSQL_DIR/data"
RUN_DIR="$MYSQL_DIR/run"
LOG_DIR="$MYSQL_DIR/log"
CONF_FILE="$MYSQL_DIR/my.cnf"
SOCKET="$RUN_DIR/mysql.sock"
SOCKET="${SENS_PORTAL_MYSQL_SOCKET:-$SOCKET}"
MYSQL_BIN="$MYSQL_PREFIX/bin/mysql"
MYSQLADMIN_BIN="$MYSQL_PREFIX/bin/mysqladmin"
MYSQLD_BIN="$MYSQL_PREFIX/bin/mysqld"
MYSQLDUMP_BIN="$MYSQL_PREFIX/bin/mysqldump"
LEGACY_MYSQL_DIR="${SENS_PORTAL_MYSQL56_DIR:-$ROOT_DIR/.local-mysql}"
LEGACY_SOCKET="${SENS_PORTAL_MYSQL56_SOCKET:-$LEGACY_MYSQL_DIR/run/mysql.sock}"
LEGACY_MYSQL_BIN="/usr/local/mysql/bin/mysql"
LEGACY_MYSQLDUMP_BIN="/usr/local/mysql/bin/mysqldump"
LAUNCHD_LABEL="com.sens.local-mysql84"

: "${SENS_PORTAL_MYSQL_ROOT_PASSWORD:?Set SENS_PORTAL_MYSQL_ROOT_PASSWORD in the environment or $ENV_FILE}"
: "${SENS_PORTAL_ADMIN_PASSWORD:?Set SENS_PORTAL_ADMIN_PASSWORD in the environment or $ENV_FILE}"
MYSQL_ROOT_PASSWORD="$SENS_PORTAL_MYSQL_ROOT_PASSWORD"
ADMIN_USERNAME="${SENS_PORTAL_ADMIN_USERNAME:-sens}"
ADMIN_PASSWORD="$SENS_PORTAL_ADMIN_PASSWORD"

mkdir -p "$DATA_DIR" "$RUN_DIR" "$LOG_DIR"

ensure_config() {
  if [[ ! -f "$CONF_FILE" ]]; then
    cat >"$CONF_FILE" <<EOF
[mysqld]
basedir=$MYSQL_PREFIX
datadir=$DATA_DIR
socket=$SOCKET
port=0
pid-file=$RUN_DIR/mysqld.pid
bind-address=127.0.0.1
skip-name-resolve
sql_mode=NO_ENGINE_SUBSTITUTION,STRICT_TRANS_TABLES
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
[client]
socket=$SOCKET
port=0
default-character-set=utf8mb4
EOF
  fi
}

ensure_datadir() {
  if [[ ! -d "$DATA_DIR/mysql" ]]; then
    "$MYSQLD_BIN" --initialize-insecure --basedir="$MYSQL_PREFIX" --datadir="$DATA_DIR" >/dev/null 2>&1
  fi
}

mysql_auth_args() {
  if "$MYSQL_BIN" -uroot -p"$MYSQL_ROOT_PASSWORD" --protocol=SOCKET --socket="$SOCKET" -e "SELECT 1" >/dev/null 2>&1; then
    printf '%s\n' "-uroot -p${MYSQL_ROOT_PASSWORD} --protocol=SOCKET --socket=${SOCKET}"
  else
    printf '%s\n' "-uroot --protocol=SOCKET --socket=${SOCKET}"
  fi
}

mysql_ping() {
  if "$MYSQL_BIN" -uroot -p"$MYSQL_ROOT_PASSWORD" --protocol=SOCKET --socket="$SOCKET" -e "SELECT 1" >/dev/null 2>&1; then
    return 0
  fi
  "$MYSQL_BIN" -uroot --protocol=SOCKET --socket="$SOCKET" -e "SELECT 1" >/dev/null 2>&1
}

wait_for_mysql() {
  local i
  for i in $(seq 1 60); do
    if mysql_ping; then
      return 0
    fi
    sleep 1
  done
  return 1
}

launchctl_available() {
  [[ "$(uname -s)" == "Darwin" ]] && command -v launchctl >/dev/null 2>&1
}

launchd_loaded() {
  launchctl print "gui/$(id -u)/$LAUNCHD_LABEL" >/dev/null 2>&1
}

start_daemon() {
  ensure_config
  ensure_datadir
  if launchctl_available; then
    if launchd_loaded; then
      launchctl remove "$LAUNCHD_LABEL"
    fi
    launchctl submit \
      -l "$LAUNCHD_LABEL" \
      -o "$LOG_DIR/mysqld.log" \
      -e "$LOG_DIR/mysqld.log" \
      -- "$MYSQLD_BIN" --defaults-file="$CONF_FILE" --skip-networking
  else
    nohup "$MYSQLD_BIN" --defaults-file="$CONF_FILE" --skip-networking >"$LOG_DIR/mysqld.log" 2>&1 &
    echo $! >"$RUN_DIR/mysqld-start.pid"
  fi
}

stop_mysql() {
  if launchctl_available && launchd_loaded; then
    launchctl remove "$LAUNCHD_LABEL"
  elif mysql_ping; then
    if "$MYSQLADMIN_BIN" -uroot -p"$MYSQL_ROOT_PASSWORD" --protocol=SOCKET --socket="$SOCKET" shutdown >/dev/null 2>&1; then
      true
    else
      "$MYSQLADMIN_BIN" -uroot --protocol=SOCKET --socket="$SOCKET" shutdown >/dev/null 2>&1 || true
    fi
  fi

  local i
  for i in $(seq 1 60); do
    if ! mysql_ping && [[ ! -S "$SOCKET" ]]; then
      break
    fi
    sleep 0.25
  done

  rm -f "$RUN_DIR/mysqld-start.pid"
}

ensure_started() {
  if mysql_ping; then
    return 0
  fi

  start_daemon
  if ! wait_for_mysql; then
    echo "MySQL 8.4 did not become ready. Inspect $LOG_DIR/mysqld.log." >&2
    exit 1
  fi
}

mysql_run() {
  # Use a real query to decide auth mode, not mysqladmin ping.
  if "$MYSQL_BIN" -uroot -p"$MYSQL_ROOT_PASSWORD" --protocol=SOCKET --socket="$SOCKET" -e "SELECT 1" >/dev/null 2>&1; then
    "$MYSQL_BIN" -uroot -p"$MYSQL_ROOT_PASSWORD" --protocol=SOCKET --socket="$SOCKET" "$@"
  else
    "$MYSQL_BIN" -uroot --protocol=SOCKET --socket="$SOCKET" "$@"
  fi
}

set_root_password() {
  mysql_run -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';"
}

bootstrap_schema() {
  mysql_run <<SQL
CREATE DATABASE IF NOT EXISTS sens DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS sens.admin_users (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(64) NOT NULL UNIQUE,
  display_name VARCHAR(128) NOT NULL,
  password_salt CHAR(32) NOT NULL,
  password_hash CHAR(64) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  last_login_at TIMESTAMP NULL DEFAULT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
SQL
}

import_legacy_ce() {
  if mysql_run -e "SELECT 1 FROM information_schema.tables WHERE table_schema = 'sens' AND table_name = 'admin_users' LIMIT 1" >/dev/null 2>&1; then
    return 1
  fi
  if [[ -S "$LEGACY_SOCKET" ]] && "$LEGACY_MYSQL_BIN" -uroot -p"$MYSQL_ROOT_PASSWORD" --protocol=SOCKET --socket="$LEGACY_SOCKET" ping >/dev/null 2>&1; then
    local dump_file
    dump_file="$(mktemp)"
    "$LEGACY_MYSQLDUMP_BIN" \
      -uroot \
      -p"$MYSQL_ROOT_PASSWORD" \
      --protocol=SOCKET \
      --socket="$LEGACY_SOCKET" \
      --single-transaction \
      --routines \
      --triggers \
      --databases ce >"$dump_file"
    perl -0pe 's/`ce`/`sens`/g' "$dump_file" | mysql_run
    rm -f "$dump_file"
    return 0
  fi
  return 1
}

ensure_admin_user() {
  mysql_run <<SQL
CREATE DATABASE IF NOT EXISTS sens DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS sens.admin_users (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(64) NOT NULL UNIQUE,
  display_name VARCHAR(128) NOT NULL,
  password_salt CHAR(32) NOT NULL,
  password_hash CHAR(64) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  last_login_at TIMESTAMP NULL DEFAULT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
SQL

  python3 - "$ADMIN_USERNAME" "$ADMIN_PASSWORD" "$SOCKET" "$MYSQL_ROOT_PASSWORD" <<'PY'
import hashlib
import secrets
import sys

import pymysql

username, password, socket_path, root_password = sys.argv[1:5]
salt = secrets.token_bytes(16)
digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200000)

conn = pymysql.connect(
    host="localhost",
    user="root",
    password=root_password,
    unix_socket=socket_path,
    database="sens",
    charset="utf8mb4",
    autocommit=True,
)
try:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO admin_users
                (username, display_name, password_salt, password_hash, is_active)
            VALUES (%s, %s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE
                display_name = VALUES(display_name),
                password_salt = VALUES(password_salt),
                password_hash = VALUES(password_hash),
                is_active = VALUES(is_active)
            """,
            (username, "SENS 管理员", salt.hex(), digest.hex()),
        )
finally:
    conn.close()
PY
}

bootstrap_database() {
  ensure_started
  if ! import_legacy_ce; then
    bootstrap_schema
  fi
  set_root_password
  ensure_admin_user
}

restart_mysql() {
  if launchctl_available && launchd_loaded; then
    launchctl kickstart -k "gui/$(id -u)/$LAUNCHD_LABEL"
    if ! wait_for_mysql; then
      echo "MySQL 8.4 did not become ready. Inspect $LOG_DIR/mysqld.log." >&2
      exit 1
    fi
  else
    stop_mysql
    start_daemon
    if ! wait_for_mysql; then
      echo "MySQL 8.4 did not become ready. Inspect $LOG_DIR/mysqld.log." >&2
      exit 1
    fi
  fi
}

status_mysql() {
  if ! mysql_ping; then
    echo "MySQL: stopped"
    return 1
  fi
  mysql_run -e "
    SELECT VERSION() AS version,
           @@socket AS socket,
           @@skip_networking AS skip_networking,
           (SELECT COUNT(*) FROM mysql.user) AS mysql_users,
           (SELECT COUNT(*) FROM information_schema.schemata) AS database_count;
  "
}

case "${1:-}" in
  start)
    ensure_started
    ;;
  bootstrap)
    bootstrap_database
    ;;
  init)
    bootstrap_database
    ;;
  status)
    status_mysql
    ;;
  ping)
    mysql_ping
    ;;
  stop)
    stop_mysql
    ;;
  restart)
    restart_mysql
    ;;
  *)
    cat <<EOF
Usage: $(basename "$0") {start|bootstrap|init|status|ping|stop|restart}

start      Start the local MySQL 8.4 daemon if needed.
bootstrap  Migrate ce from the legacy 5.6 instance if present, then seed root and sens.
init       Run start + bootstrap in one pass.
status     Print current MySQL/socket status.
ping       Exit 0 only when the socket accepts root login.
stop       Stop the project-local MySQL 8.4 daemon.
restart    Restart the project-local MySQL 8.4 daemon.
EOF
    exit 1
    ;;
esac
