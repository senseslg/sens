#!/usr/bin/env python3
"""Read-only OSS CLI. Emits one JSON result; never reads object contents."""
import argparse
import json
from oss_api import OSSClient, OSSError, load_credentials, public_result

CONFIGS = ("acl", "cors", "lifecycle", "referer", "versioning", "policy", "encryption", "tagging", "website", "logging")


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--region", required=True)
    p.add_argument("--credentials", help="private JSON path; otherwise OSS_* environment")
    p.add_argument("--bucket", default="")
    sub = p.add_subparsers(dest="operation", required=True)
    ls = sub.add_parser("buckets")
    ls.add_argument("--prefix", default="")
    ls.add_argument("--marker", default="")
    ls.add_argument("--limit", type=int, default=100)
    sub.add_parser("info")
    sub.add_parser("stat")
    config = sub.add_parser("config")
    config.add_argument("name", choices=CONFIGS)
    objects = sub.add_parser("objects")
    objects.add_argument("--prefix", required=True, help="explicit scope; use / delimiter for directories")
    objects.add_argument("--delimiter", default="/")
    objects.add_argument("--token", default="")
    objects.add_argument("--limit", type=int, default=100)
    head = sub.add_parser("head")
    head.add_argument("key")
    return p


def run(args):
    if hasattr(args, "limit") and not 1 <= args.limit <= 1000:
        raise OSSError("limit_must_be_1_to_1000")
    if (args.operation == "buckets") == bool(args.bucket):
        raise OSSError("buckets_requires_no_bucket_other_operations_require_bucket")
    params, method, key = {}, "GET", ""
    if args.operation == "buckets":
        params = {"prefix": args.prefix, "marker": args.marker, "max-keys": args.limit}
    elif args.operation in ("info", "stat"):
        params = {"bucketInfo" if args.operation == "info" else "stat": None}
    elif args.operation == "config":
        params = {args.name: None}
    elif args.operation == "objects":
        params = {"list-type": "2", "prefix": args.prefix, "delimiter": args.delimiter,
                  "max-keys": args.limit, "encoding-type": "url"}
        if args.token:
            params["continuation-token"] = args.token
    elif args.operation == "head":
        if not args.key:
            raise OSSError("empty_object_key")
        method, key = "HEAD", args.key
    client = OSSClient(args.region, load_credentials(args.credentials), args.bucket)
    return public_result(client.request(method, key, params))


def main():
    args = parser().parse_args()
    try:
        print(json.dumps(run(args), ensure_ascii=False))
        return 0
    except OSSError as exc:
        print(json.dumps(exc.as_dict()))
        return 1 if exc.status in (403, 404) else 2
    except (OSError, ValueError, TypeError):
        print(json.dumps({"error": "local_input_or_file_error"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
