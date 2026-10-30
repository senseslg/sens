#!/usr/bin/env python3
"""Read-only GCP cost inventory and hourly monitoring summaries; never mutates resources.

Requires an existing gcloud login. Writes only the explicitly requested local JSON.
No credentials, connection strings, request bodies, or customer data are exported.
Exit 0: all queries succeeded; 2: partial results; 1: collection failed.
"""
import argparse
import concurrent.futures
import datetime as dt
import json
import math
import ssl
from pathlib import Path
import subprocess
import urllib.error
import urllib.parse
import urllib.request


def gcloud(args):
    result = subprocess.run(["gcloud", *args, "--format=json", "--quiet"],
                            capture_output=True, text=True, timeout=120)
    if result.returncode:
        return {"error": "gcloud_failed", "command": args[:4]}
    try:
        return json.loads(result.stdout)
    except ValueError:
        return {"error": "invalid_json"}


def get_json(url, token):
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        import certifi
        context = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=90, context=context) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        return {"error": "http_error", "status": exc.code}
    except (OSError, ValueError):
        return {"error": "request_failed"}


def tail(value):
    return value.rsplit("/", 1)[-1] if isinstance(value, str) else value


def inventory(project):
    commands = {
        "instances": ["compute", "instances", "list"],
        "disks": ["compute", "disks", "list"],
        "snapshots": ["compute", "snapshots", "list"],
        "images": ["compute", "images", "list", "--no-standard-images"],
        "managed_groups": ["compute", "instance-groups", "managed", "list"],
        "addresses": ["compute", "addresses", "list"],
        "forwarding_rules": ["compute", "forwarding-rules", "list"],
        "backends": ["compute", "backend-services", "list"],
        "url_maps": ["compute", "url-maps", "list"],
        "routers": ["compute", "routers", "list"],
        "commitments": ["compute", "commitments", "list"],
        "sql": ["sql", "instances", "list"],
        "redis": ["redis", "instances", "list", "--region=asia-southeast1"],
        "clusters": ["container", "clusters", "list"],
        "buckets": ["storage", "buckets", "list"],
    }
    output = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        pending = {pool.submit(gcloud, [*args, f"--project={project}"]): name
                   for name, args in commands.items()}
        for future in concurrent.futures.as_completed(pending):
            name = pending[future]
            try:
                output[name] = sanitize(name, future.result())
            except Exception:
                output[name] = {"error": "collection_failed"}
    return output


def sanitize(name, rows):
    if isinstance(rows, dict) and "error" in rows:
        return rows
    if isinstance(rows, dict):
        rows = rows.get("items", [])
    keys = {
        "instances": ["name", "id", "status", "zone", "machineType", "creationTimestamp"],
        "disks": ["name", "zone", "sizeGb", "type", "users", "creationTimestamp"],
        "snapshots": ["name", "sourceDisk", "diskSizeGb", "storageBytes", "storageLocations", "creationTimestamp"],
        "images": ["name", "diskSizeGb", "storageLocations", "creationTimestamp"],
        "managed_groups": ["name", "zone", "targetSize", "instanceTemplate", "autoHealingPolicies", "autoscaler"],
        "addresses": ["name", "status", "region", "addressType", "users"],
        "forwarding_rules": ["name", "region", "target", "loadBalancingScheme", "portRange"],
        "backends": ["name", "region", "protocol", "enableCDN", "securityPolicy", "backends"],
        "url_maps": ["name", "defaultService", "hostRules", "pathMatchers"],
        "routers": ["name", "region", "nats"],
        "commitments": ["name", "status", "plan", "region", "resources"],
        "sql": ["name", "region", "state", "databaseVersion", "settings"],
        "redis": ["name", "tier", "memorySizeGb", "redisVersion", "state", "locationId"],
        "clusters": ["name", "location", "status", "currentNodeCount", "nodePools", "autopilot"],
        "buckets": ["name", "location", "storage_class", "default_storage_class", "lifecycle_config", "retention_policy", "soft_delete_policy", "versioning_enabled", "creation_time"],
    }[name]
    selected = []
    for row in rows:
        item = {key: row[key] for key in keys if key in row}
        if name == "instances":
            item["disks"] = [{key: disk.get(key) for key in ("source", "diskSizeGb", "boot")}
                             for disk in row.get("disks", [])]
        if name == "sql":
            settings = row.get("settings", {})
            item["settings"] = {key: settings[key] for key in (
                "tier", "dataDiskSizeGb", "dataDiskType", "availabilityType", "edition",
                "storageAutoResize", "storageAutoResizeLimit", "activationPolicy", "backupConfiguration")
                if key in settings}
        if name == "clusters":
            item["nodePools"] = [{"name": p.get("name"), "initialNodeCount": p.get("initialNodeCount"),
                                  "autoscaling": p.get("autoscaling"),
                                  "machineType": p.get("config", {}).get("machineType")}
                                 for p in row.get("nodePools", [])]
        selected.append(item)
    return selected


METRICS = {
    "vm_cpu": ("compute.googleapis.com/instance/cpu/utilization", "ALIGN_MEAN"),
    "vm_cpu_peak": ("compute.googleapis.com/instance/cpu/utilization", "ALIGN_MAX"),
    "vm_memory_percent": ("agent.googleapis.com/memory/percent_used", "ALIGN_MEAN"),
    "vm_disk_percent": ("agent.googleapis.com/disk/percent_used", "ALIGN_MEAN"),
    "sql_cpu": ("cloudsql.googleapis.com/database/cpu/utilization", "ALIGN_MEAN"),
    "sql_cpu_peak": ("cloudsql.googleapis.com/database/cpu/utilization", "ALIGN_MAX"),
    "sql_memory": ("cloudsql.googleapis.com/database/memory/utilization", "ALIGN_MEAN"),
    "sql_memory_used": ("cloudsql.googleapis.com/database/memory/usage", "ALIGN_MEAN"),
    "sql_memory_components": ("cloudsql.googleapis.com/database/memory/components", "ALIGN_MEAN"),
    "sql_disk_used": ("cloudsql.googleapis.com/database/disk/bytes_used", "ALIGN_MEAN"),
    "sql_disk_quota": ("cloudsql.googleapis.com/database/disk/quota", "ALIGN_MEAN"),
    "sql_disk_types": ("cloudsql.googleapis.com/database/disk/bytes_used_by_data_type", "ALIGN_MEAN"),
    "sql_connections": ("cloudsql.googleapis.com/database/network/connections", "ALIGN_MEAN"),
    "redis_used": ("redis.googleapis.com/stats/memory/usage", "ALIGN_MEAN"),
    "redis_connections": ("redis.googleapis.com/clients/connected", "ALIGN_MEAN"),
    "redis_commands": ("redis.googleapis.com/commands/calls", "ALIGN_SUM"),
    "storage_bytes": ("storage.googleapis.com/storage/total_bytes", "ALIGN_MEAN"),
    "storage_objects": ("storage.googleapis.com/storage/object_count", "ALIGN_MEAN"),
    "api_calls": ("serviceruntime.googleapis.com/api/request_count", "ALIGN_SUM"),
    "lb_requests": ("loadbalancing.googleapis.com/https/request_count", "ALIGN_SUM"),
}


def metric_summary(project, name, metric, aligner, start, end, token):
    params = {"filter": f'metric.type="{metric}"', "interval.startTime": start,
              "interval.endTime": end, "aggregation.alignmentPeriod": "3600s",
              "aggregation.perSeriesAligner": aligner, "pageSize": "100000"}
    # API counts can have many method/status series; aggregate at service level.
    if name == "api_calls":
        params.update({"aggregation.crossSeriesReducer": "REDUCE_SUM",
                       "aggregation.groupByFields": "resource.labels.service"})
    if name == "lb_requests":
        params.update({"aggregation.crossSeriesReducer": "REDUCE_SUM",
                       "aggregation.groupByFields": ["resource.labels.url_map_name", "metric.labels.response_code_class"]})
    base = f"https://monitoring.googleapis.com/v3/projects/{project}/timeSeries?"
    output, pages = [], 0
    while True:
        data = get_json(base + urllib.parse.urlencode(params, doseq=True), token)
        if "error" in data:
            return data
        for series in data.get("timeSeries", []):
            points = series.get("points", [])
            values = [float(p["value"].get("doubleValue", p["value"].get("int64Value", 0))) for p in points]
            values = [v for v in values if math.isfinite(v)]
            if not values:
                continue
            ordered = sorted(values)
            output.append({"resource": series.get("resource"), "metric_labels": series.get("metric", {}).get("labels", {}),
                           "points": len(values), "mean_hourly": sum(values)/len(values),
                           "p95_hourly": ordered[max(0, math.ceil(len(values)*.95)-1)],
                           "max_hourly": max(values), "min_hourly": min(values),
                           "latest": values[0], "oldest": values[-1], "sum_hourly": sum(values) if aligner == "ALIGN_SUM" else None,
                           "latest_time": points[0]["interval"]["endTime"],
                           "oldest_time": points[-1]["interval"]["endTime"]})
        pages += 1
        if not data.get("nextPageToken"):
            return {"series": output, "pages": pages}
        if pages >= 20:
            return {"series": output, "error": "page_limit", "pages": pages}
        params["pageToken"] = data["nextPageToken"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not 1 <= args.days <= 90:
        parser.error("days must be 1..90")
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(days=args.days)
    stamp = lambda value: value.isoformat().replace("+00:00", "Z")
    result = {"project": args.project, "collected_at": stamp(end), "start": stamp(start),
              "aggregation": "Hourly means except *_peak (hourly maxima); totals use ALIGN_SUM. p95/max of mean series are not instantaneous peaks.",
              "inventory": inventory(args.project), "metrics": {}}
    token_result = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True, timeout=30)
    if token_result.returncode:
        result["metrics"] = {"error": "authentication_failed"}
    else:
        token = token_result.stdout.strip()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            tasks = {pool.submit(metric_summary, args.project, name, metric, aligner,
                                 stamp(start), stamp(end), token): name
                     for name, (metric, aligner) in METRICS.items()}
            for task in concurrent.futures.as_completed(tasks):
                name = tasks[task]
                try:
                    result["metrics"][name] = task.result()
                except Exception:
                    result["metrics"][name] = {"error": "collection_failed"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    errors = [k for section in ("inventory", "metrics") for k, v in result[section].items()
              if isinstance(v, dict) and "error" in v]
    if "error" in result["metrics"]:
        errors.append("metrics_authentication")
    print(json.dumps({"output": str(args.output), "partial_failures": errors}))
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
