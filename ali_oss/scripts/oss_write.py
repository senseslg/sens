#!/usr/bin/env python3
"""OSS mutations, dry-run by default. --apply is an execution switch, not authorization."""
import argparse
import hashlib
import json
from pathlib import Path
from oss_api import OSSClient, OSSError, load_credentials, parse_xml, public_result

ROOTS = {"cors": "CORSConfiguration", "lifecycle": "LifecycleConfiguration",
         "referer": "RefererConfiguration", "versioning": "VersioningConfiguration",
         "encryption": "ServerSideEncryptionRule", "tagging": "Tagging",
         "website": "WebsiteConfiguration", "logging": "BucketLoggingStatus"}
MAX_UPLOAD = 32 * 1024 * 1024


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--region", required=True)
    p.add_argument("--bucket", required=True)
    p.add_argument("--credentials")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--confirm-bucket", help="must equal --bucket when applying")
    sub = p.add_subparsers(dest="operation", required=True)
    put = sub.add_parser("put-object")
    put.add_argument("key")
    put.add_argument("file", type=Path)
    put.add_argument("--content-type", default="application/octet-stream")
    delete = sub.add_parser("delete-object")
    delete.add_argument("key")
    delete.add_argument("--version-id", help="explicit version; omission may create a delete marker")
    config = sub.add_parser("put-config")
    config.add_argument("name", choices=tuple(ROOTS) + ("policy",))
    config.add_argument("file", type=Path)
    acl = sub.add_parser("set-acl")
    acl.add_argument("acl", choices=("private", "public-read", "public-read-write"))
    return p


def plan(args):
    headers, params, body, key = {}, {}, None, ""
    method = "PUT"
    if args.operation == "put-object":
        key = args.key
        if args.file.stat().st_size > MAX_UPLOAD:
            raise OSSError("upload_limit_32MiB_use_official_sdk_for_large_files")
        body = args.file.read_bytes()
        if len(body) > MAX_UPLOAD:
            raise OSSError("upload_limit_32MiB_use_official_sdk_for_large_files")
        headers = {"Content-Type": args.content_type, "x-oss-forbid-overwrite": "true"}
    elif args.operation == "delete-object":
        method, key = "DELETE", args.key
        if args.version_id:
            params["versionId"] = args.version_id
    elif args.operation == "set-acl":
        params, headers = {"acl": None}, {"x-oss-acl": args.acl}
    else:
        if args.file.stat().st_size > 1024 * 1024:
            raise OSSError("config_limit_1MiB")
        body = args.file.read_bytes()
        params = {args.name: None}
        if args.name == "policy":
            policy = json.loads(body)
            if not isinstance(policy, dict) or "Statement" not in policy:
                raise OSSError("expected_bucket_policy_json")
            headers["Content-Type"] = "application/json"
        else:
            if parse_xml(body).tag != ROOTS[args.name]:
                raise OSSError("unexpected_configuration_xml_root")
            headers["Content-Type"] = "application/xml"
    if args.operation.endswith("object") and not key:
        raise OSSError("empty_object_key")
    return method, key, params, headers, body


def run(args):
    method, key, params, headers, body = plan(args)
    # Validate endpoint/target even in preview; do not read credentials until apply.
    client = OSSClient(args.region, {}, args.bucket)
    preview = {"dry_run": not args.apply, "operation": args.operation, "method": method,
               "bucket": args.bucket, "region": args.region, "key": key, "params": params,
               "headers": headers, "bytes": len(body) if body is not None else 0,
               "sha256": hashlib.sha256(body).hexdigest() if body is not None else None}
    if not args.apply:
        return preview
    if args.confirm_bucket != args.bucket:
        raise OSSError("apply_requires_matching_confirm_bucket")
    client.credentials = load_credentials(args.credentials)
    return {"plan": preview, "result": public_result(client.request(method, key, params, body, headers)),
            "verification_required": True}


def main():
    args = parser().parse_args()
    try:
        print(json.dumps(run(args), ensure_ascii=False))
        return 0
    except OSSError as exc:
        print(json.dumps(exc.as_dict()))
        return 1 if exc.status in (403, 404, 409, 412) else 2
    except (OSError, ValueError, TypeError):
        print(json.dumps({"error": "local_input_or_file_error"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
