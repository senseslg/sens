# cs-online server access

Reusable local entry point for Toucha's self-hosted Chatwoot production server.

## Common commands

| Task | Command | Behavior |
|---|---|---|
| Interactive login | `./connect.sh` | Opens an SSH session |
| One remote command | `./connect.sh 'hostname && uptime'` | Runs the command and exits |
| Quick server status | `./server-status.sh` | Prints resources, services, listeners, version and HTTP status |
| Health check | `./health-check.sh` | Returns automation-friendly status code |
| Disk/log inspection | `./disk-log-check.sh` | Reports disk, largest log files and short growth rate without printing log content |
| Full daily check | `./daily-check.sh` | Runs health plus disk/log checks and saves a local report |

All operational scripts are read-only. They do not restart services, edit configuration, delete/rotate logs, deploy code, or write to databases.

## Daily operation

Recommended daily check:

```bash
cd /Users/lingang/sens/sens-server/cs-online
./daily-check.sh
```

Reports are saved under `reports/` with a timestamp. They contain service/resource metadata, not raw application logs.

Because the root filesystem is currently above the default warning threshold, a daily check is expected to print `ATTENTION REQUIRED` and return exit code `2` until disk usage is remediated.

Run without saving a report:

```bash
SAVE_REPORTS=0 ./daily-check.sh
```

Override thresholds or the log-growth sample duration:

```bash
DISK_WARN_PERCENT=90 LOG_SAMPLE_SECONDS=10 ./daily-check.sh
```

Exit-code convention:

- `0` — checks passed.
- `1` — local usage/configuration error.
- `2` — server attention is required.

## Connection

Interactive SSH login:

```bash
./connect.sh
```

On macOS, `connect.command` can be double-clicked in Finder to open an interactive SSH session.

| Item | Value |
|---|---|
| Host | `47.239.215.30` |
| User | `sens` |
| Default key | `~/.ssh/id_ed25519` |
| Public-key fingerprint | `SHA256:VUaAQ7Y2X3NB8+vksh5h3QfZbD65HMThsQRCxkhZJiY` |
| Authentication | Ed25519 public-key login, verified 2026-07-31 |

The private key remains in `~/.ssh/` and must never be copied into this directory or onto the server.

Environment overrides supported by the scripts:

```bash
CS_ONLINE_SSH_HOST=47.239.215.30
CS_ONLINE_SSH_USER=sens
CS_ONLINE_SSH_KEY="$HOME/.ssh/id_ed25519"
```

## Optional SSH alias

Review [`ssh_config.example`](ssh_config.example), then copy its block into `~/.ssh/config` if the alias is useful:

```bash
ssh sens-cs-online
```

The helper scripts do not modify `~/.ssh/config`.

## Server information

See [`SERVER_INFO.md`](SERVER_INFO.md) for the verified runtime topology, health endpoints, current risks, and maintenance boundaries.

## Safety

- Read-only inspection is the default.
- Do not run service restarts, deployments, config changes, log deletion/rotation, database writes, firewall changes, or package installation without explicit authorization.
- Never print or copy `/home/chatwoot/chatwoot/.env` or `/etc/nginx/ssl/origin.key`.
- Application logs can contain customer or message data. The supplied scripts inspect counts, sizes and service metadata only; they do not print log messages.
