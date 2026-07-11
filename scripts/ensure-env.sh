#!/usr/bin/env bash
# Ensure project .env exists (bootstrap from example). Safe to run repeatedly.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/.env}"
PROFILE="${1:-dev}"

if [[ -f "$ENV_FILE" ]]; then
  echo "OK: $ENV_FILE exists"
  exit 0
fi

case "$PROFILE" in
  prod|production|r1)
    SRC="$ROOT/.env.production.example"
    ;;
  aliyun-staging|staging)
    SRC="$ROOT/.env.aliyun-staging.example"
    ;;
  *)
    if [[ -f "$ROOT/.env.docker.example" ]]; then
      SRC="$ROOT/.env.docker.example"
    else
      SRC="$ROOT/.env.example"
    fi
    ;;
esac

if [[ ! -f "$SRC" ]]; then
  echo "ERROR: template not found: $SRC" >&2
  exit 1
fi

cp "$SRC" "$ENV_FILE"
echo "Created $ENV_FILE from $(basename "$SRC")"
if [[ "$PROFILE" == "prod" || "$PROFILE" == "production" || "$PROFILE" == "r1" ]]; then
  echo "WARN: Edit POSTGRES_PASSWORD and OLLAMA_* in .env before customer go-live."
fi
if [[ "$PROFILE" == "aliyun-staging" || "$PROFILE" == "staging" ]]; then
  echo "WARN: Replace change_me_* placeholders (or run scripts/deploy-aliyun-staging.sh)."
fi
