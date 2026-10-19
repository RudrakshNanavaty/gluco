#!/usr/bin/env bash
# Copy the database settings CI needs from back-end/.env to GitHub Actions secrets.
#
#   scripts/github-secrets.sh [--dry-run]
#
# Sets PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD, PGSSLMODE and
# DASHBOARD_SESSION_ID (read from DASHBOARD_SESSION_ID or DEMO_SESSION_ID) on the
# repository `gh` resolves for this checkout. Values go to `gh` on stdin, never
# on a command line or to the terminal. --dry-run prints names only.
#
# Needs `gh auth login` with permission to manage the repo's secrets. Use a
# SELECT-only database role: CI runs pull request code with these credentials.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
file="${ENV_FILE:-$root/back-end/.env}"
dry_run=false
case "${1:-}" in
  "") ;;
  --dry-run) dry_run=true ;;
  *) echo "usage: $0 [--dry-run]" >&2; exit 2 ;;
esac
[[ -f "$file" ]] || { echo "$file not found" >&2; exit 1; }

# Last assignment of NAME in the file, without the quotes around its value.
# The file is parsed, not sourced, so nothing in it is executed.
value_of() {
  local line value
  line="$(grep -E "^[[:space:]]*(export[[:space:]]+)?$1=" "$file" | tail -n1 || true)"
  value="${line#*=}"
  value="${value%$'\r'}"
  if [[ "$value" =~ ^\"(.*)\"$ || "$value" =~ ^\'(.*)\'$ ]]; then value="${BASH_REMATCH[1]}"; fi
  printf '%s' "$value"
}

# secret name : env names to try, first non-empty wins
mapping=(
  "PGHOST:PGHOST"
  "PGPORT:PGPORT"
  "PGDATABASE:PGDATABASE"
  "PGUSER:PGUSER"
  "PGPASSWORD:PGPASSWORD"
  "PGSSLMODE:PGSSLMODE"
  "DASHBOARD_SESSION_ID:DASHBOARD_SESSION_ID DEMO_SESSION_ID"
)

repo_args=()
[[ -z "${GITHUB_REPOSITORY:-}" ]] || repo_args=(--repo "$GITHUB_REPOSITORY")

missing=0
for entry in "${mapping[@]}"; do
  name="${entry%%:*}"
  value=""
  for source in ${entry#*:}; do
    value="$(value_of "$source")"
    [[ -z "$value" ]] || break
  done
  if [[ -z "$value" ]]; then
    echo "skip   $name (empty or missing in ${file#"$root/"})"
    # The live job cannot connect without the connection details and credentials.
    case "$name" in PGHOST|PGUSER|PGPASSWORD) missing=1 ;; esac
    continue
  fi
  if $dry_run; then
    echo "would set $name"
  else
    printf '%s' "$value" | gh secret set "$name" "${repo_args[@]}"
  fi
done

if [[ $missing -ne 0 ]]; then
  echo "PGHOST, PGUSER and PGPASSWORD are required for the live database job." >&2
  exit 1
fi
