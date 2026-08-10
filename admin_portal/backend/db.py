from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pymysql

from .config import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    MYSQL_DATABASE,
    MYSQL_ROOT_PASSWORD,
    LOCAL_MYSQL_SOCKET,
)
from .security import hash_password


@dataclass(frozen=True)
class DatabaseStatus:
    online: bool
    version: str | None = None
    user_count: int | None = None
    database_count: int | None = None
    error: str | None = None


def _public_admin_user(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "is_active": bool(row["is_active"]),
        "last_login_at": row["last_login_at"].isoformat() if row["last_login_at"] else None,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def _connect(database: str | None = None):
    return pymysql.connect(
        host="localhost",
        user="root",
        password=MYSQL_ROOT_PASSWORD,
        unix_socket=str(LOCAL_MYSQL_SOCKET),
        database=database,
        charset="utf8mb4",
        autocommit=True,
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
        read_timeout=10,
        write_timeout=10,
    )


@contextmanager
def connect(database: str | None = None):
    conn = _connect(database)
    try:
        yield conn
    finally:
        conn.close()


def bootstrap_database() -> None:
    with connect() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE DATABASE IF NOT EXISTS `sens`
                DEFAULT CHARACTER SET utf8mb4
                COLLATE utf8mb4_unicode_ci
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS `sens`.`admin_users` (
                    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(64) NOT NULL UNIQUE,
                    display_name VARCHAR(128) NOT NULL,
                    password_salt CHAR(32) NOT NULL,
                    password_hash CHAR(64) NOT NULL,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    last_login_at TIMESTAMP NULL DEFAULT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """
            )
            salt_hex, password_hash = hash_password(ADMIN_PASSWORD)
            cursor.execute(
                """
                INSERT INTO `sens`.`admin_users`
                    (username, display_name, password_salt, password_hash, is_active)
                SELECT %s, %s, %s, %s, 1
                FROM DUAL
                WHERE NOT EXISTS (
                    SELECT 1 FROM `sens`.`admin_users` WHERE username = %s
                )
                """,
                (
                    ADMIN_USERNAME,
                    "SENS 管理员",
                    salt_hex,
                    password_hash,
                    ADMIN_USERNAME,
                ),
            )


def fetch_admin_user(username: str) -> dict[str, Any] | None:
    with connect(MYSQL_DATABASE) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, display_name, password_salt, password_hash,
                       is_active, last_login_at
                FROM admin_users
                WHERE username = %s
                LIMIT 1
                """,
                (username,),
            )
            return cursor.fetchone()


def fetch_admin_user_by_id(user_id: int) -> dict[str, Any] | None:
    with connect(MYSQL_DATABASE) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, display_name, is_active, last_login_at,
                       created_at, updated_at
                FROM admin_users
                WHERE id = %s
                LIMIT 1
                """,
                (user_id,),
            )
            row = cursor.fetchone()
            return _public_admin_user(row) if row else None


def mark_login(username: str) -> None:
    with connect(MYSQL_DATABASE) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE admin_users
                SET last_login_at = %s
                WHERE username = %s
                """,
                (datetime.now(), username),
            )


def list_admin_users() -> list[dict[str, Any]]:
    with connect(MYSQL_DATABASE) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, username, display_name, is_active, last_login_at,
                       created_at, updated_at
                FROM admin_users
                ORDER BY id ASC
                """
            )
            return [_public_admin_user(row) for row in cursor.fetchall()]


def count_active_admin_users() -> int:
    with connect(MYSQL_DATABASE) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS count FROM admin_users WHERE is_active = 1")
            return int(cursor.fetchone()["count"])


def create_admin_user(
    username: str,
    display_name: str,
    password: str,
    is_active: bool = True,
) -> dict[str, Any]:
    salt_hex, password_hash = hash_password(password)
    with connect(MYSQL_DATABASE) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO admin_users
                    (username, display_name, password_salt, password_hash, is_active)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (username, display_name, salt_hex, password_hash, 1 if is_active else 0),
            )
            user = fetch_admin_user_by_id(int(cursor.lastrowid))
            if not user:
                raise RuntimeError("failed_to_fetch_created_user")
            return user


def update_admin_user(user_id: int, display_name: str, is_active: bool) -> dict[str, Any] | None:
    with connect(MYSQL_DATABASE) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE admin_users
                SET display_name = %s,
                    is_active = %s
                WHERE id = %s
                """,
                (display_name, 1 if is_active else 0, user_id),
            )
    return fetch_admin_user_by_id(user_id)


def reset_admin_password(user_id: int, password: str) -> dict[str, Any] | None:
    salt_hex, password_hash = hash_password(password)
    with connect(MYSQL_DATABASE) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE admin_users
                SET password_salt = %s,
                    password_hash = %s
                WHERE id = %s
                """,
                (salt_hex, password_hash, user_id),
            )
    return fetch_admin_user_by_id(user_id)


def delete_admin_user(user_id: int) -> bool:
    with connect(MYSQL_DATABASE) as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM admin_users WHERE id = %s", (user_id,))
            return cursor.rowcount > 0


def inspect_database() -> DatabaseStatus:
    try:
        with connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT VERSION() AS version")
                version = cursor.fetchone()["version"]
                cursor.execute("SELECT COUNT(*) AS count FROM mysql.user")
                user_count = int(cursor.fetchone()["count"])
                cursor.execute("SHOW DATABASES")
                database_count = len(cursor.fetchall())
        return DatabaseStatus(
            online=True,
            version=version,
            user_count=user_count,
            database_count=database_count,
        )
    except Exception as exc:  # noqa: BLE001
        return DatabaseStatus(online=False, error=str(exc))
