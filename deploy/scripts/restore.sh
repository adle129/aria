#!/usr/bin/env bash
# Restore ARIA backup (R1-KH09): PostgreSQL -> app files -> active pointer
# Usage: bash deploy/scripts/restore.sh /data/aria/backups/20260710
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup_dir>" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARIA_ROOT="${ARIA_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
ENV_FILE="${ENV_FILE:-$ARIA_ROOT/.env}"
BACKUP_DIR="$(cd "$1" && pwd)"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

ARIA_DATA_ROOT="${ARIA_DATA_ROOT:-/data/aria}"
APP_DIR="${ARIA_DATA_ROOT}/app"
PG_CONTAINER="${PG_CONTAINER:-aria-postgres}"
COMPOSE_FILE="${COMPOSE_FILE:-$ARIA_ROOT/docker-compose.prod.yml}"
LOCK_FILE="${ARIA_DATA_ROOT}/.restore.lock"
ROLLBACK_DIR=""

cleanup() {
  rm -f "$LOCK_FILE"
}
trap cleanup EXIT

require_file() {
  if [[ ! -e "$1" ]]; then
    echo "Missing backup artifact: $1" >&2
    exit 3
  fi
}

echo "[$(date -Iseconds)] Restore start from $BACKUP_DIR"
require_file "${BACKUP_DIR}/aria_db.sql"

if [[ -e "$LOCK_FILE" ]]; then
  echo "Another restore is in progress: $LOCK_FILE" >&2
  exit 4
fi
touch "$LOCK_FILE"

ROLLBACK_DIR="${ARIA_DATA_ROOT}/backups/.rollback-$(date +%Y%m%d%H%M%S)"
mkdir -p "$ROLLBACK_DIR"

bash "$SCRIPT_DIR/stop.sh" || true

for sub in uploads outputs knowledge_base templates config feedback; do
  if [[ -d "${APP_DIR}/${sub}" ]]; then
    rsync -a "${APP_DIR}/${sub}/" "${ROLLBACK_DIR}/${sub}/"
  fi
done
for file in manpower_baselines.json pgvector_index_state.json; do
  if [[ -f "${APP_DIR}/${file}" ]]; then
    cp -a "${APP_DIR}/${file}" "${ROLLBACK_DIR}/${file}"
  fi
done

docker compose -f "$COMPOSE_FILE" up -d postgres
sleep 5

if ! docker exec -i "$PG_CONTAINER" psql -U aria_admin -d aria_db < "${BACKUP_DIR}/aria_db.sql"; then
  echo "[$(date -Iseconds)] PostgreSQL restore failed; rolling back app files from $ROLLBACK_DIR" >&2
  for sub in uploads outputs knowledge_base templates config feedback; do
    if [[ -d "${ROLLBACK_DIR}/${sub}" ]]; then
      rsync -a "${ROLLBACK_DIR}/${sub}/" "${APP_DIR}/${sub}/"
    fi
  done
  for file in manpower_baselines.json pgvector_index_state.json; do
    if [[ -f "${ROLLBACK_DIR}/${file}" ]]; then
      cp -a "${ROLLBACK_DIR}/${file}" "${APP_DIR}/${file}"
    fi
  done
  exit 5
fi

for sub in uploads outputs knowledge_base templates config feedback; do
  if [[ -d "${BACKUP_DIR}/${sub}" ]]; then
    mkdir -p "${APP_DIR}/${sub}"
    rsync -a --delete "${BACKUP_DIR}/${sub}/" "${APP_DIR}/${sub}/"
  fi
done

for file in manpower_baselines.json pgvector_index_state.json; do
  if [[ -f "${BACKUP_DIR}/${file}" ]]; then
    cp -a "${BACKUP_DIR}/${file}" "${APP_DIR}/${file}"
  fi
done

bash "$SCRIPT_DIR/start.sh"

echo "[$(date -Iseconds)] Restore completed. Rollback snapshot: $ROLLBACK_DIR"
echo "[$(date -Iseconds)] Post-restore checks: Top-3 search, baselines API, import batch audit"
