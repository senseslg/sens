#!/usr/bin/env bash
set -euo pipefail

readonly SSH_HOST="${DMALL_SSH_HOST:-47.83.1.157}"
readonly SSH_USER="${DMALL_SSH_USER:-sens}"
readonly SSH_KEY="${DMALL_SSH_KEY:-/Users/lingang/.ssh/id_ed25519_d_mall}"

if [[ ! -r "$SSH_KEY" ]]; then
  printf 'SSH key is missing or unreadable: %s\n' "$SSH_KEY" >&2
  printf 'Set DMALL_SSH_KEY to the correct private-key path.\n' >&2
  exit 1
fi

exec ssh \
  -i "$SSH_KEY" \
  -o IdentitiesOnly=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  "${SSH_USER}@${SSH_HOST}" \
  "$@"
