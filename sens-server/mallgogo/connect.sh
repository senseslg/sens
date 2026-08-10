#!/usr/bin/env bash
set -euo pipefail

readonly SSH_HOST="${MALLGOGO_SSH_HOST:-47.83.14.210}"
readonly SSH_PORT="${MALLGOGO_SSH_PORT:-22}"
readonly SSH_USER="${MALLGOGO_SSH_USER:-sens}"
readonly SSH_KEY="${MALLGOGO_SSH_KEY:-$HOME/.ssh/id_ed25519_cel_mall_server}"

if [[ ! -r "$SSH_KEY" ]]; then
  printf 'SSH key is missing or unreadable: %s\n' "$SSH_KEY" >&2
  printf 'Set MALLGOGO_SSH_KEY to the correct private-key path.\n' >&2
  exit 1
fi

exec ssh \
  -i "$SSH_KEY" \
  -p "$SSH_PORT" \
  -o IdentitiesOnly=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  "${SSH_USER}@${SSH_HOST}" \
  "$@"
