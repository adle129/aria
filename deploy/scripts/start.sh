#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARIA_ROOT="${ARIA_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-$ARIA_ROOT/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ARIA_ROOT/.env}"

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "ERROR: compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: .env not found: $ENV_FILE (copy from .env.production.example)" >&2
  exit 1
fi

cd "$ARIA_ROOT"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
echo "ARIA started. Check: curl -s http://localhost/api/v1/health"
