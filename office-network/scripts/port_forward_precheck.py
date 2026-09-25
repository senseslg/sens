#!/usr/bin/env python3
"""Read-only precheck and RouterOS rule proposal for one port forward.

This script never logs in to a router and never applies configuration. It
validates parameters, checks LAN TCP reachability, optionally inspects a
sanitized RouterOS export, and prints proposed commands for human review.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path
import re
import socket
import sys
from typing import Any


def port_number(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def private_ipv4(value: str) -> str:
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("target IP must be a valid IPv4 address") from exc
    if address.version != 4 or not address.is_private or address.is_loopback:
        raise argparse.ArgumentTypeError("target IP must be a private, non-loopback IPv4 address")
    return str(address)


def ipv4(value: str) -> str:
    try:
        address = ipaddress.ip_address(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("public IP must be a valid IPv4 address") from exc
    if address.version != 4:
        raise argparse.ArgumentTypeError("public IP must be IPv4")
    return str(address)


def cidr(value: str) -> str:
    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("source must be a valid IPv4 CIDR") from exc
    if network.version != 4:
        raise argparse.ArgumentTypeError("source must be IPv4")
    return str(network)


def safe_name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,48}", value):
        raise argparse.ArgumentTypeError(
            "service name may contain only letters, digits, dot, underscore, and hyphen"
        )
    return value


def tcp_check(host: str, port: int, timeout: float) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {"checked": True, "reachable": True, "detail": "TCP connection succeeded"}
    except OSError as exc:
        return {"checked": True, "reachable": False, "detail": str(exc)}


def inspect_export(path: Path, public_port: int, target_ip: str, target_port: int) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"read": False, "error": str(exc)}

    logical_lines: list[str] = []
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        current = f"{current} {line}".strip()
        if current.endswith("\\"):
            current = current[:-1].strip()
            continue
        logical_lines.append(current)
        current = ""
    if current:
        logical_lines.append(current)

    nat_rules = [line for line in logical_lines if "chain=dstnat" in line]
    filter_rules = [line for line in logical_lines if "chain=forward" in line]
    port_pattern = re.compile(rf"(?:^|\s)dst-port={public_port}(?:\s|$)")
    conflicts = [line for line in nat_rules if port_pattern.search(line)]
    same_target = [
        line
        for line in nat_rules
        if f"to-addresses={target_ip}" in line and f"to-ports={target_port}" in line
    ]
    dstnat_policy = [line for line in filter_rules if "connection-nat-state" in line]
    final_drops = [line for line in filter_rules if "action=drop" in line]
    return {
        "read": True,
        "dstnat_rule_count": len(nat_rules),
        "forward_rule_count": len(filter_rules),
        "public_port_conflicts": conflicts,
        "same_target_rules": same_target,
        "dstnat_policy_rules": dstnat_policy,
        "forward_drop_rule_count": len(final_drops),
        "note": "Rule order and full semantics still require human review.",
    }


def proposed_rules(args: argparse.Namespace) -> dict[str, str]:
    source = f" src-address={args.source_cidr}" if args.source_cidr else ""
    public = f" dst-address={args.public_ip}" if args.public_ip else ""
    nat = (
        "/ip firewall nat add chain=dstnat action=dst-nat"
        f" in-interface-list={args.wan_interface_list} protocol={args.protocol}"
        f" dst-port={args.public_port}{public}{source}"
        f" to-addresses={args.target_ip} to-ports={args.target_port}"
        f' comment="office-network:{args.service_name}"'
    )
    filter_rule = (
        "/ip firewall filter add chain=forward action=accept"
        f" in-interface-list={args.wan_interface_list} connection-nat-state=dstnat"
        f" protocol={args.protocol} dst-address={args.target_ip}"
        f" dst-port={args.target_port}{source}"
        f' comment="office-network:{args.service_name}:allow"'
    )
    return {"required_dstnat": nat, "conditional_forward_accept": filter_rule}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service-name", required=True, type=safe_name)
    parser.add_argument("--target-ip", required=True, type=private_ipv4)
    parser.add_argument("--target-port", required=True, type=port_number)
    parser.add_argument("--public-port", required=True, type=port_number)
    parser.add_argument("--protocol", choices=("tcp", "udp"), default="tcp")
    parser.add_argument("--public-ip", type=ipv4)
    parser.add_argument("--source-cidr", type=cidr)
    parser.add_argument("--wan-interface-list", default="WAN", type=safe_name)
    parser.add_argument("--router-export", type=Path, help="sanitized RouterOS text export")
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--skip-connect", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    local_check: dict[str, Any]
    if args.skip_connect:
        local_check = {"checked": False, "reachable": None, "detail": "skipped"}
    elif args.protocol == "tcp":
        local_check = tcp_check(args.target_ip, args.target_port, args.timeout)
    else:
        local_check = {
            "checked": False,
            "reachable": None,
            "detail": "UDP reachability cannot be proven with a generic connect check",
        }

    export_result = (
        inspect_export(args.router_export, args.public_port, args.target_ip, args.target_port)
        if args.router_export
        else {"read": False, "detail": "no sanitized export supplied"}
    )
    warnings: list[str] = []
    if not args.source_cidr:
        warnings.append("No source CIDR restriction: the proposed public port is globally reachable.")
    if not args.public_ip:
        warnings.append("No public IP matcher: proposal relies only on WAN interface list and port.")
    if local_check.get("reachable") is False:
        warnings.append("LAN TCP service is not reachable; do not add a public mapping yet.")
    if export_result.get("public_port_conflicts"):
        warnings.append("A dstnat rule already uses the requested public port; inspect before changes.")

    result = {
        "mode": "read-only; no router login or configuration writes",
        "parameters": {
            "service_name": args.service_name,
            "target_ip": args.target_ip,
            "target_port": args.target_port,
            "public_port": args.public_port,
            "protocol": args.protocol,
            "public_ip": args.public_ip,
            "source_cidr": args.source_cidr,
            "wan_interface_list": args.wan_interface_list,
        },
        "lan_service_check": local_check,
        "router_export_check": export_result,
        "proposed_rules": proposed_rules(args),
        "warnings": warnings,
        "decision": (
            "not_ready"
            if local_check.get("reachable") is False or export_result.get("public_port_conflicts")
            else "ready_for_human_router-review"
        ),
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("Port-forward precheck (READ ONLY)")
        print(f"Decision: {result['decision']}")
        print(f"LAN service: {local_check['detail']}")
        print("Required NAT proposal:")
        print(f"  {result['proposed_rules']['required_dstnat']}")
        print("Conditional filter proposal (only if current forward rules require it):")
        print(f"  {result['proposed_rules']['conditional_forward_accept']}")
        for warning in warnings:
            print(f"WARNING: {warning}")

    return 1 if result["decision"] == "not_ready" else 0


if __name__ == "__main__":
    sys.exit(main())
