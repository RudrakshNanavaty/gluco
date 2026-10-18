#!/usr/bin/env bash
# Sync a local .env file with its Google Secret Manager secret.
#
#   scripts/secrets.sh <backend|frontend> <push|pull|diff>
#
# push  uploads the local .env as a new secret version (creates the secret if needed)
# pull  overwrites the local .env with the latest version (old file kept as .env.bak)
# diff  compares local and remote by variable name only; values are never printed
#
# GLUCO_GCP_PROJECT overrides the project (default: gcloud's active project).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
usage() { echo "usage: $0 <backend|frontend> <push|pull|diff>" >&2; exit 2; }
[[ $# -eq 2 ]] || usage

case "$1" in
  backend) secret=gluco-backend-env file="$root/back-end/.env" ;;
  frontend) secret=gluco-frontend-env file="$root/front-end/.env" ;;
  *) usage ;;
esac

project="${GLUCO_GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null)}"
[[ -n "$project" ]] || { echo "No GCP project: run 'gcloud config set project <id>' or set GLUCO_GCP_PROJECT" >&2; exit 1; }

latest() { gcloud secrets versions access latest --secret="$secret" --project="$project"; }

# Sorted "NAME<TAB>sha256" lines, so values can be compared without being shown.
fingerprint() {
  grep -E '^[A-Za-z_][A-Za-z0-9_]*=' | while IFS= read -r line; do
    printf '%s\t%s\n' "${line%%=*}" "$(printf '%s' "${line#*=}" | sha256sum | cut -c1-12)"
  done | sort
}

case "$2" in
  push)
    [[ -f "$file" ]] || { echo "$file not found" >&2; exit 1; }
    if gcloud secrets describe "$secret" --project="$project" >/dev/null 2>&1; then
      gcloud secrets versions add "$secret" --data-file="$file" --project="$project"
    else
      gcloud secrets create "$secret" --data-file="$file" --replication-policy=automatic --project="$project"
    fi
    ;;
  pull)
    remote="$(mktemp)"
    trap 'rm -f "$remote"' EXIT
    latest >"$remote"
    if [[ -f "$file" ]]; then
      cp "$file" "$file.bak"
      echo "Backed up existing file to ${file#"$root/"}.bak"
    fi
    install -m 600 "$remote" "$file"
    echo "Wrote ${file#"$root/"} from $secret"
    ;;
  diff)
    [[ -f "$file" ]] || { echo "$file not found" >&2; exit 1; }
    if diff <(fingerprint <"$file") <(latest | fingerprint) >/dev/null; then
      echo "In sync: ${file#"$root/"} matches $secret"
    else
      echo "Differs (variable name and short value hash only; '<' local, '>' remote):"
      diff <(fingerprint <"$file") <(latest | fingerprint) || true
      exit 1
    fi
    ;;
  *) usage ;;
esac
