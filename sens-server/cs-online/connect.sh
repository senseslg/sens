#!/usr/bin/env bash
set -euo pipefail

readonly SSH_HOST="${CS_ONLINE_SSH_HOST:-47.239.215.30}"
readonly SSH_USER="${CS_ONLINE_SSH_USER:-sens}"
readonly SSH_KEY="${CS_ONLINE_SSH_KEY:-$HOME/.ssh/id_ed25519}"

if [[ ! -r "$SSH_KEY" ]]; then
  printf 'SSH key is missing or unreadable: %s\n' "$SSH_KEY" >&2
  printf 'Set CS_ONLINE_SSH_KEY to the correct private-key path.\n' >&2
  exit 1
fi

exec ssh \
  -i "$SSH_KEY" \
  -o IdentitiesOnly=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  "${SSH_USER}@${SSH_HOST}" \
  "$@"
