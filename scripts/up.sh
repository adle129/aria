#!/usr/bin/env bash
# One-click dev: bootstrap .env (if missing) + docker compose up --build
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

bash "$ROOT/scripts/ensure-env.sh" dev

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
EXTRA_ARGS=("$@")

if [[ "${1:-}" == "--cn" ]]; then
  COMPOSE_FILE="docker-compose.cn.yml"
  shift
  EXTRA_ARGS=("$@")
fi

if [[ "${1:-}" == "--dev-fast" ]]; then
  COMPOSE_FILE="docker-compose.dev.yml"
  shift
  EXTRA_ARGS=("$@")
fi

echo "==> docker compose -f $COMPOSE_FILE up --build ${EXTRA_ARGS[*]:-}"
docker compose -f "$COMPOSE_FILE" up --build "${EXTRA_ARGS[@]}"
