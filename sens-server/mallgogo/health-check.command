#!/usr/bin/env bash
set -u

cd "$(dirname "$0")" || exit 1
./health-check.sh
status=$?

printf '\nPress Enter to close...'
read -r _
exit "$status"
