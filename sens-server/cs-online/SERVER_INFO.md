# cs-online server information

Last read-only verification: **2026-07-31**.

## Identity

| Item | Verified value |
|---|---|
| Role | Toucha self-hosted Chatwoot production host |
| SSH | `sens@47.239.215.30` |
| Hostname | `cs-online` |
| Provider | Alibaba Cloud ECS |
| OS | Ubuntu 22.04.5 LTS |
| Kernel | `5.15.0-173-generic` |
| Architecture | `x86_64` |
| Server timezone | `Asia/Shanghai` (`UTC+08:00`) |
| CPU | 2 logical CPUs |
| Memory | 7.6 GiB |
| Swap | None |

This host contains the Chatwoot deployment. No Toucha Java backend or Vue frontend checkout was found under `/home`, `/opt`, `/srv`, or `/var/www` during the 2026-07-23 baseline survey.

## Current health

Verified on 2026-07-31:

- Chatwoot target, Web, and Worker: active.
- PostgreSQL 16 and Redis: active.
- Alibaba Cloud backup client: active.
- Local Chatwoot Web (`127.0.0.1:3000`): HTTP 200.
- SidekiqAlive (`127.0.0.1:7433`): HTTP 200.
- `https://chat.cambodianexpress.com`: HTTP 200.
- `https://superset.cambodianexpress.com`: HTTP 200.
- Nginx process serves 80/443, but `nginx.service` remains inactive.
- Root filesystem: 118 GiB total, 106 GiB used, 7.2 GiB available (**94% used**).
- Memory: about 3.8 GiB available during verification; no swap.

Disk usage increased from 90% on 2026-07-23 to 94% on 2026-07-31. Treat disk/log remediation as urgent.

## Runtime topology

### Chatwoot

| Item | Value |
|---|---|
| Path | `/home/chatwoot/chatwoot` |
| Version | `4.12.1` / tag `v4.12.1` |
| Branch | `master` |
| Startup target | `chatwoot.target` |
| Web unit | `chatwoot-web.1.service` |
| Worker unit | `chatwoot-worker.1.service` |
| Web port | `3000` |
| SidekiqAlive port | `7433` |

### Supporting services

| Port | Binding | Service |
|---|---|---|
| `22` | all interfaces | SSH |
| `80`, `443` | all interfaces | Nginx |
| `3000` | all interfaces | Chatwoot Rails |
| `7433` | all interfaces | SidekiqAlive |
| `5432` | loopback only | PostgreSQL |
| `6379` | loopback only | Redis |
| `44089` | loopback only | Alibaba Cloud backup client |

Direct workstation checks to ports 3000 and 7433 timed out during the baseline survey. UFW was inactive, so an Alibaba Cloud security group or another upstream network control was inferred to block those ports. Re-check cloud rules before relying on that protection.

## Nginx

Both domains proxy to `127.0.0.1:3000`:

- `chat.cambodianexpress.com`
- `superset.cambodianexpress.com`

Operational warning:

- `nginx.service` is enabled but inactive.
- The live Nginx master was launched from a root login-session cgroup rather than the systemd service.
- Do not assume `systemctl reload/restart nginx` controls the live process.

Reconcile Nginx with systemd only in an approved maintenance window with configuration validation, rollback preparation, and external HTTP checks.

## Highest-priority risks

### P0 — Disk/log growth

Baseline findings on 2026-07-23:

- `/var/log` was about 17 GiB.
- Current and previous syslog files were about 4.4 GiB and 6.6 GiB.
- Persistent journal data was about 4.0 GiB.
- Chatwoot generated about 2,198 journal entries in a sampled minute.
- Nearly all of the latest 200,000 syslog lines came from Chatwoot Web and Worker.
- Weekly rsyslog rotation was insufficient for the observed rate.

By 2026-07-31, root disk usage reached 94% with only 7.2 GiB free.

Do not truncate/delete logs ad hoc. An approved remediation must first preserve a small diagnostic sample, identify the noisy Chatwoot statements/log level, define size/daily retention limits, confirm retention requirements, and verify health plus disk/log growth afterward.

### P1 — Secret-file permissions

`/home/chatwoot/chatwoot/.env` was mode `664` in the baseline survey. Its contents were not inspected. Tighten permissions only during an approved change and verify Chatwoot afterward.

### P1 — SSH policy

Public-key login for `sens` works. The server still allowed password authentication and direct root login during the baseline survey. Do not disable them until another recovery/operator key has been tested in a separate session.

### P2 — No swap

There is no swap. Evaluate a small swap file or stronger memory monitoring during an approved maintenance window.

### P2 — Backup restore unverified

The Alibaba Cloud backup client is active, but backup scope, retention, PostgreSQL consistency, last success, and restore procedure have not been verified.

## Read-only checks

Use:

```bash
./health-check.sh
```

Or after connecting:

```bash
systemctl status chatwoot.target chatwoot-web.1.service chatwoot-worker.1.service --no-pager
systemctl status postgresql@16-main.service redis-server.service --no-pager
ss -ltn
df -hT /
free -h
curl -sS -m 5 -o /dev/null -w '%{http_code} %{time_total}s\n' http://127.0.0.1:3000
curl -sS -m 5 -o /dev/null -w '%{http_code} %{time_total}s\n' http://127.0.0.1:7433
```

## Change boundary

No restart/deployment/rollback procedure has been exercised safely on this production host. Before the first state-changing maintenance:

1. Confirm a current backup and tested restore path.
2. Record Chatwoot tag/commit and worktree state.
3. Confirm `.env` preservation and database migration requirements.
4. Resolve how the live Nginx process will be controlled.
5. Prepare rollback steps.
6. Capture before-state.
7. Make the smallest scoped change.
8. Verify services, listeners, all four HTTP checks, disk, and recent narrow logs.

Never invent and execute a generic Chatwoot deployment workflow directly against this host.

## Maintenance history

- **2026-07-23** — Completed the initial read-only server survey; installed and verified the workstation Ed25519 public key for `sens`.
- **2026-07-31** — Re-verified key login, required services, four HTTP health checks, memory, and disk. Services remained healthy; root disk usage had increased to 94%.
