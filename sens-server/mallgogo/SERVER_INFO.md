# Mallgogo server information

Last connection verification: **2026-07-31**.

## Identity

| Item | Verified value |
|---|---|
| Role | Mallgogo production and UAT application host |
| SSH | `sens@47.83.14.210:22` |
| Hostname | `iZj6ce4xclipwf6qqnf9fkZ` |
| OS | Ubuntu 20.04.6 LTS |
| Architecture | `x86_64` |
| Server timezone | UTC+8 at the 2026-07-28 inspection |
| CPU | 4 logical CPUs |
| Memory | About 15 GiB |
| Swap | None |

## Current verified health

Read-only check at **2026-07-31 12:59 UTC+8**:

- Mall production and UAT Java processes: running.
- Nginx process: running.
- Docker service: active.
- Production and UAT local `/version`: HTTP 200.
- Production and UAT public admin sites: HTTP 200.
- Root filesystem: 40% used.
- Available memory: 38%.
- TLS certificate: valid through 2026-10-11, 72 days remaining.
- Overall scripted result: `HEALTHY`.

## Known runtime topology

| Component | Binding/endpoint | Notes |
|---|---|---|
| Mall production backend | `127.0.0.1:8081` and public port exposure observed | Java process using `mall-prod.jar` |
| Mall UAT backend | `127.0.0.1:8082` | Java process using `mall-uat.jar` |
| Nginx | `80`, `443` | Live process was not controlled by an active systemd unit |
| Onebound/product parser | `8000` | Public connection was blocked during baseline inspection |
| MinIO API/console | `9000`, `9001` | Public exposure was observed during baseline inspection |
| MySQL | loopback `3306` | Health scripts do not connect to it |
| Redis | loopback `6379` | Health scripts do not authenticate or query it |

HTTP checks used by the scripts:

- `http://127.0.0.1:8081/version`
- `http://127.0.0.1:8082/version`
- `https://admin.cel-mall.com`
- `https://admin-uat.cel-mall.com`

## Known operational risks

1. Java process arguments have exposed database, Redis, payment, object storage,
   and application credentials to local process listings. The bundled scripts
   show PID/resource data only and never print complete command lines.
2. Production backend port `8081` and MinIO ports `9000`/`9001` were reachable
   publicly during the 2026-07-28 baseline. Confirm and restrict cloud security
   group and host firewall rules.
3. The Let's Encrypt certificate was valid through 2026-10-11 at the baseline,
   but a Certbot renewal run had failed. The health script checks current expiry.
4. Mall Java processes and the live Nginx process did not have a clearly verified
   unified systemd lifecycle. Do not assume `systemctl restart nginx` or a generic
   Java restart command controls the live workload.
5. The host has no swap. Monitor memory headroom because production and UAT each
   historically used a 4 GiB Java heap.

## Read-only routine

Daily or before a deployment:

```bash
./health-check.sh
```

When investigating a warning:

```bash
./server-status.sh
```

The detailed status report covers identity, uptime, load, memory, filesystems,
selected process resource usage, selected listeners, service-unit state, local
and public HTTP responses, and TLS certificate dates. It does not read application
logs or secrets.

## Change boundary

Before a restart, deployment, configuration edit, firewall change, certificate
operation, log cleanup, or database write:

1. Confirm the exact target environment: production or UAT.
2. Capture a read-only before-state.
3. Identify the actual process supervisor/deployment mechanism.
4. Confirm backup and rollback paths.
5. Make the smallest scoped change.
6. Re-run both local and public health checks.
7. Record the change and result.
