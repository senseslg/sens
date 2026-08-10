#!/usr/bin/env bash
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_DIR="${DMALL_PROJECT_DIR:-/home/sens/ce-ssr-app}"

assume_yes=0
if [[ "${1:-}" == "--yes" ]]; then
  assume_yes=1
  shift
fi

if (( $# != 1 )); then
  printf 'Usage: %s [--yes] <git-ref-or-commit>\n' "$0" >&2
  printf 'Use an exact commit SHA whenever possible.\n' >&2
  exit 1
fi

readonly TARGET_REF="$1"
if [[ "$TARGET_REF" == -* || ! "$TARGET_REF" =~ ^[A-Za-z0-9._/-]+$ ]]; then
  printf 'Unsafe or unsupported Git ref: %s\n' "$TARGET_REF" >&2
  exit 1
fi

printf 'Target server:  sens@%s\n' "${DMALL_SSH_HOST:-47.83.1.157}"
printf 'Project:        %s\n' "$PROJECT_DIR"
printf 'Deploy target:  %s\n' "$TARGET_REF"
printf '\nCurrent server state:\n'
"$SCRIPT_DIR/connect.sh" \
  "PROJECT_DIR='$PROJECT_DIR' bash -s" <<'REMOTE'
set -u
printf '  commit:   '; git -C "$PROJECT_DIR" rev-parse HEAD
printf '  version:  '
sed -n 's/^[[:space:]]*"version":[[:space:]]*"\([^"]*\)".*/\1/p' \
  "$PROJECT_DIR/package.json" | head -n 1
printf '  rollback: '
if [[ -r "$PROJECT_DIR/.deploy_rollback_ref" ]]; then
  cat "$PROJECT_DIR/.deploy_rollback_ref"
else
  printf 'not recorded\n'
fi
REMOTE

if (( assume_yes == 0 )); then
  printf '\nThis updates code, installs dependencies, rebuilds and restarts the app.\n'
  read -r -p 'Type DEPLOY to continue: ' confirmation
  if [[ "$confirmation" != "DEPLOY" ]]; then
    printf 'Deployment cancelled.\n'
    exit 1
  fi
fi

"$SCRIPT_DIR/connect.sh" bash -s -- "$PROJECT_DIR" "$TARGET_REF" <<'REMOTE'
set -euo pipefail
project_dir="$1"
target_ref="$2"
cd "$project_dir"
exec bash ./deploy.sh "$target_ref"
REMOTE

printf '\nDeployment completed. Running independent health check...\n'
"$SCRIPT_DIR/health-check.sh"
