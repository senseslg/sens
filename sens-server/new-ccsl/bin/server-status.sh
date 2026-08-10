#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

exec python3 "${ROOT_DIR}/scripts/server_baseline.py" \
  --ssh-host sens@8.212.48.176 "$@"
