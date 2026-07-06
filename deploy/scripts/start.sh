#!/usr/bin/env bash
# Production one-click start (bootstrap .env + data dirs + compose up)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARIA_ROOT="${ARIA_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-$ARIA_ROOT/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ARIA_ROOT/.env}"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "ERROR: compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

bash "$ARIA_ROOT/scripts/ensure-env.sh" prod

DATA_ROOT="/data/aria"
if [[ -f "$ENV_FILE" ]]; then
  line="$(grep -E '^ARIA_DATA_ROOT=' "$ENV_FILE" | tail -1 | cut -d= -f2- | tr -d '\r" ' || true)"
  [[ -n "$line" ]] && DATA_ROOT="$line"
fi
mkdir -p "$DATA_ROOT/postgres" "$DATA_ROOT/app"/{uploads,outputs,knowledge_base,chroma_db,templates,app/feedback}

cd "$ARIA_ROOT"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build "$@"
echo "ARIA started (profile=${ARIA_UI_PROFILE:-r1}). Check: curl -s http://localhost/api/v1/health"
