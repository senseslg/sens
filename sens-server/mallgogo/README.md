# Mallgogo server access

Reusable local-only access and read-only operations helpers for the Mallgogo
application server.

## Quick start

Interactive SSH login:

```bash
./connect.sh
```

Run one remote command:

```bash
./connect.sh 'hostname && uptime'
```

Run the concise health check:

```bash
./health-check.sh
```

Run the more detailed read-only status inspection:

```bash
./server-status.sh
```

On macOS, `connect.command` and `health-check.command` can be double-clicked in
Finder.

## Connection

| Item | Value |
|---|---|
| Host | `47.83.14.210` |
| SSH port | `22` |
| User | `sens` |
| Default key | `~/.ssh/id_ed25519_cel_mall_server` |
| Authentication | Ed25519 public-key login |
| Verified remote hostname | `iZj6ce4xclipwf6qqnf9fkZ` |

The private key stays in `~/.ssh/`. It must never be copied into this folder,
a project repository, a ticket, or a chat message.

Environment overrides supported by the scripts:

```bash
MALLGOGO_SSH_HOST=47.83.14.210
MALLGOGO_SSH_PORT=22
MALLGOGO_SSH_USER=sens
MALLGOGO_SSH_KEY="$HOME/.ssh/id_ed25519_cel_mall_server"
```

## Health check thresholds

Defaults:

- Root filesystem warning: `85%`
- Available memory warning: `10%`
- TLS certificate expiry warning: `21` days

Override them for one run:

```bash
DISK_WARN_PERCENT=90 MEMORY_WARN_PERCENT=8 CERT_WARN_DAYS=30 ./health-check.sh
```

Exit codes:

- `0`: required process and HTTP checks passed; thresholds are acceptable.
- `2`: at least one required check failed or crossed a warning threshold.
- Other non-zero values: local script, SSH, or argument error.

## Optional SSH alias

Review `ssh_config.example`, then place its block in `~/.ssh/config` if useful:

```bash
ssh sens-mallgogo
```

The scripts do not modify SSH configuration automatically.

## Safety boundary

- All bundled checks are read-only.
- No script restarts services, deploys code, modifies configuration, queries a
  database, clears logs, changes firewall rules, or uses `sudo`.
- Do not inspect complete Java command lines. This server historically exposed
  credentials in process arguments.
- Obtain explicit authorization and prepare verification and rollback steps
  before any production change.

See `SERVER_INFO.md` for the known runtime topology and operational risks.
