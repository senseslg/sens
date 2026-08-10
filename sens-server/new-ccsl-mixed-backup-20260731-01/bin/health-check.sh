#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
VERIFIER="${ROOT_DIR}/scripts/verify_deployment.py"
SSH_TARGET="sens@8.212.48.176"

usage() {
  echo "Usage: $0 {prod|uat|all} [--json]" >&2
  exit 2
}

run_prod() {
  python3 "${VERIFIER}" \
    --ssh-host "${SSH_TARGET}" \
    --jar-path /home/engineer/prod/backend/ccsl-prod.jar \
    --log-path /home/engineer/prod/backend/ccsl-prod.log \
    --port 8080 \
    --domain https://portal.ceccsl.com/ \
    --domain https://m.ceccsl.com/ \
    "$@"
}

run_uat() {
  python3 "${VERIFIER}" \
    --ssh-host "${SSH_TARGET}" \
    --jar-path /home/engineer/uat/backend/ccsl-uat.jar \
    --log-path /home/engineer/uat/backend/ccsl-uat.log \
    --port 8081 \
    --domain https://ccsl-uat.cambodianexpress.com/ \
    --domain https://m-uat.ceccsl.com/ \
    "$@"
}

[[ $# -ge 1 ]] || usage
environment="$1"
shift

case "${environment}" in
  prod)
    run_prod "$@"
    ;;
  uat)
    run_uat "$@"
    ;;
  all)
    result=0
    run_prod "$@" || result=$?
    run_uat "$@" || result=$?
    exit "${result}"
    ;;
  *)
    usage
    ;;
esac
