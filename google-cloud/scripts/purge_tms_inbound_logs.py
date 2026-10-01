#!/usr/bin/env python3
"""Safely purge old tms_uat.sys_if_invoke_inbound rows in bounded batches.

Dry-run by default. The production config path is read, never written or printed.
Run with --execute only after checking the current Cloud SQL backup and free space.
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import pymysql
import yaml


DEFAULT_CONFIG = (
    Path(__file__).resolve().parents[2]
    / "otwms-server/otwms-backend/src/main/resources/application-prod.yml"
)


def connect(config_path):
    with open(config_path, encoding="utf-8") as config_file:
        source = yaml.safe_load(config_file)["spring"]["datasource"]
    url = urlparse(source["url"].removeprefix("jdbc:"))
    return pymysql.connect(
        host=url.hostname,
        port=url.port or 3306,
        user=source["username"],
        password=source["password"],
        database="tms_uat",
        charset="utf8mb4",
        connect_timeout=10,
        read_timeout=120,
        write_timeout=120,
        autocommit=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cutoff", help="Fixed database-local cutoff: YYYY-MM-DD HH:MM:SS")
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--max-rows", type=int, default=10000)
    parser.add_argument("--sleep", type=float, default=0.25)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 5000 or args.max_rows < 1 or args.sleep < 0:
        parser.error("batch-size must be 1..5000, max-rows positive, sleep nonnegative")
    if args.cutoff:
        try:
            time.strptime(args.cutoff, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            parser.error("cutoff must be YYYY-MM-DD HH:MM:SS")

    conn = connect(args.config)
    deleted = 0
    started = time.monotonic()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SET SESSION innodb_lock_wait_timeout = 3")
            cursor.execute("SELECT NOW(), NOW() - INTERVAL 2 YEAR, @@session.time_zone")
            db_now, default_cutoff, timezone = cursor.fetchone()
            cutoff = args.cutoff or str(default_cutoff)
            if cutoff > str(default_cutoff):
                raise ValueError("cutoff is newer than the two-year retention boundary")
            cursor.execute(
                "SELECT INBOUND_ID, REQUEST_TIME FROM sys_if_invoke_inbound "
                "WHERE REQUEST_TIME < %s ORDER BY REQUEST_TIME LIMIT 1",
                (cutoff,),
            )
            first = cursor.fetchone()
            print(json.dumps({
                "mode": "execute" if args.execute else "dry-run",
                "db_now": str(db_now), "timezone": timezone,
                "cutoff": cutoff, "oldest_target": str(first),
                "batch_size": args.batch_size, "max_rows": args.max_rows,
            }), flush=True)
            if not args.execute or first is None:
                return
            while deleted < args.max_rows:
                limit = min(args.batch_size, args.max_rows - deleted)
                batch_started = time.monotonic()
                cursor.execute(
                    "DELETE FROM sys_if_invoke_inbound "
                    "WHERE REQUEST_TIME < %s ORDER BY REQUEST_TIME LIMIT %s",
                    (cutoff, limit),
                )
                count = cursor.rowcount
                if count < 0 or count > limit:
                    raise RuntimeError("unexpected affected-row count")
                conn.commit()
                deleted += count
                if deleted % 50000 < args.batch_size or count < limit:
                    print(json.dumps({
                        "deleted_this_run": deleted,
                        "last_batch": count,
                        "last_batch_seconds": round(time.monotonic() - batch_started, 3),
                        "elapsed_seconds": round(time.monotonic() - started, 1),
                    }), flush=True)
                if count < limit:
                    break
                if args.sleep:
                    time.sleep(args.sleep)
            cursor.execute(
                "SELECT INBOUND_ID, REQUEST_TIME FROM sys_if_invoke_inbound "
                "WHERE REQUEST_TIME < %s ORDER BY REQUEST_TIME LIMIT 1",
                (cutoff,),
            )
            remaining = cursor.fetchone()
            print(json.dumps({
                "complete": remaining is None,
                "deleted_this_run": deleted,
                "oldest_remaining_target": str(remaining),
            }), flush=True)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error_type": type(exc).__name__}), file=sys.stderr)
        sys.exit(1)
