#!/usr/bin/env bash
# Production one-click start: preflight + compose up (migrate via backend entrypoint)
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

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker is not running." >&2
  exit 1
fi

MOCK_LLM="$(grep -E '^MOCK_LLM=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '\r" ' || echo false)"
MOCK_RAG="$(grep -E '^MOCK_RAG=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '\r" ' || echo false)"
ARIA_UI_PROFILE_VAL="$(grep -E '^ARIA_UI_PROFILE=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '\r" ' || echo r1)"
OLLAMA_URL="$(grep -E '^OLLAMA_BASE_URL=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- | tr -d '\r" ' || echo http://localhost:11434)"
OLLAMA_URL="${OLLAMA_URL/host.docker.internal/localhost}"

if [[ "${ARIA_UI_PROFILE_VAL,,}" == "r1" ]]; then
  if [[ "${MOCK_LLM,,}" == "true" || "${MOCK_RAG,,}" == "true" ]]; then
    echo "ERROR: ARIA_UI_PROFILE=r1 requires MOCK_LLM=false and MOCK_RAG=false in $ENV_FILE" >&2
    exit 1
  fi
fi

if [[ "${MOCK_LLM,,}" != "true" ]]; then
  if ! curl -sf "${OLLAMA_URL}/api/tags" >/dev/null; then
    echo "WARN: Ollama not reachable at ${OLLAMA_URL} (MOCK_LLM=false). Install/start Ollama first." >&2
  fi
fi

cd "$ARIA_ROOT"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build "$@"

deadline=$((SECONDS + 180))
while (( SECONDS < deadline )); do
  if curl -sf http://localhost/api/v1/health >/dev/null; then
    break
  fi
  sleep 3
done

if ! curl -sf http://localhost/api/v1/health >/dev/null; then
  echo "ERROR: health check failed. docker compose -f $COMPOSE_FILE logs backend worker" >&2
  exit 1
fi

for c in aria-postgres aria-backend aria-worker aria-frontend aria-nginx; do
  if ! docker ps --format '{{.Names}}' | grep -qx "$c"; then
    echo "ERROR: container not running: $c" >&2
    exit 1
  fi
done

echo "ARIA started (profile=${ARIA_UI_PROFILE_VAL:-r1})."
echo "  App:    http://localhost"
echo "  Health: http://localhost/api/v1/health"
echo "  Admin:  docker exec aria-backend python scripts/create_admin.py --username admin --password '***' --display-name Admin --role kb_admin"
echo "  Smoke:  python scripts/r1_e2e_smoke.py --base-url http://localhost/api/v1 --username USER --password PASS"
