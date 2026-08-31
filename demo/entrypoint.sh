#!/usr/bin/env bash
set -euo pipefail

root_password="${FIREBIRD_ROOT_PASSWORD:-}"
case "${root_password,,}" in
  ""|secret|masterkey|change_me|replace_with_random_root_password)
    echo "FIREBIRD_ROOT_PASSWORD must be set to a non-placeholder value" >&2
    exit 78
    ;;
esac

exec /usr/local/bin/entrypoint.sh "$@"
