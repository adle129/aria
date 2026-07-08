#!/usr/bin/env bash
# One-click Docker: preflight + compose up --build (+ health verify when -d)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PROFILE="dev"
COMPOSE_FILE="docker-compose.yml"
DETACHED=""
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cn) COMPOSE_FILE="docker-compose.cn.yml"; shift ;;
    --dev-fast) COMPOSE_FILE="docker-compose.dev.yml"; shift ;;
    --prod) PROFILE="prod"; COMPOSE_FILE="docker-compose.prod.yml"; shift ;;
    -d|--detach) DETACHED="-d"; shift ;;
    *) EXTRA_ARGS+=("$1"); shift ;;
  esac
done

bash "$ROOT/scripts/ensure-env.sh" "$PROFILE"

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker is not running." >&2
  exit 1
fi

if [[ "$COMPOSE_FILE" != "docker-compose.dev.yml" ]]; then
  MOCK_LLM="$(grep -E '^MOCK_LLM=' "$ROOT/.env" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '\r" ' || echo true)"
  OLLAMA_URL="$(grep -E '^OLLAMA_BASE_URL=' "$ROOT/.env" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '\r" ' || echo http://localhost:11434)"
  OLLAMA_URL="${OLLAMA_URL/host.docker.internal/localhost}"
  if [[ "${MOCK_LLM,,}" != "true" ]]; then
    if ! curl -sf "${OLLAMA_URL}/api/tags" >/dev/null; then
      echo "WARN: Ollama not reachable at ${OLLAMA_URL} (MOCK_LLM=false)" >&2
    fi
  fi
fi

if [[ "$COMPOSE_FILE" == "docker-compose.dev.yml" ]]; then
  echo "WARN: dev-fast lacks pgvector/worker — not for R1 testing." >&2
fi

echo "==> docker compose -f $COMPOSE_FILE up --build $DETACHED ${EXTRA_ARGS[*]:-}"
docker compose -f "$COMPOSE_FILE" up --build $DETACHED "${EXTRA_ARGS[@]}"

if [[ -n "$DETACHED" && "$COMPOSE_FILE" != "docker-compose.dev.yml" ]]; then
  deadline=$((SECONDS + 180))
  until curl -sf http://localhost/api/v1/health >/dev/null; do
    if (( SECONDS >= deadline )); then
      echo "ERROR: health check timed out" >&2
      exit 1
    fi
    sleep 3
  done
  for c in aria-postgres aria-backend aria-worker aria-frontend aria-nginx; do
    docker ps --format '{{.Names}}' | grep -qx "$c" || { echo "ERROR: $c not running" >&2; exit 1; }
  done
  echo "ARIA started: http://localhost  health: http://localhost/api/v1/health"
fi
