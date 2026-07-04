#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARIA_ROOT="${ARIA_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-$ARIA_ROOT/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ARIA_ROOT/.env}"

cd "$ARIA_ROOT"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
echo "ARIA stopped."
