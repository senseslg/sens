# sens-server

Shared, local-only connection and operations helpers for servers maintained by `sens`.

## Servers

- [`cs-online/`](cs-online/) - Toucha's self-hosted Chatwoot production server.
- [`mallgogo/`](mallgogo/) - Mallgogo production and UAT application server.
- [`new-ccsl/`](new-ccsl/) - New CCSL Java production and UAT server.
- [`d-mall-sever/`](d-mall-sever/) - D-Mall / `ce-ssr-app` production server.

The `d-mall-sever` directory name follows the requested local path spelling.

## Rules

- Keep passwords, private keys, tokens, `.env` files, database credentials, and
  certificate private keys out of this directory.
- Store only connection metadata, public-key fingerprints, redacted server facts,
  and reviewed helper scripts.
- Treat remote servers as production-like. Start read-only and obtain explicit
  authorization before any restart, deployment, configuration edit, log cleanup,
  package install, database write, firewall change, or deletion.
- Update each server's `SERVER_INFO.md` after a verified maintenance session.
