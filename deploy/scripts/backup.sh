#!/usr/bin/env bash
# Daily backup: PostgreSQL dump + app data directories
# crontab: 0 2 * * * /opt/aria/deploy/scripts/backup.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARIA_ROOT="${ARIA_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
ENV_FILE="${ENV_FILE:-$ARIA_ROOT/.env}"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

ARIA_DATA_ROOT="${ARIA_DATA_ROOT:-/data/aria}"
APP_DIR="${ARIA_DATA_ROOT}/app"
BACKUP_ROOT="${ARIA_DATA_ROOT}/backups"
DATE="$(date +%Y%m%d)"
BACKUP_DIR="${BACKUP_ROOT}/${DATE}"
PG_CONTAINER="${PG_CONTAINER:-aria-postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

mkdir -p "$BACKUP_DIR"

echo "[$(date -Iseconds)] Backup start -> $BACKUP_DIR"

docker exec "$PG_CONTAINER" pg_dump -U aria_admin aria_db > "${BACKUP_DIR}/aria_db.sql"

for sub in uploads outputs knowledge_base chroma_db templates; do
  if [[ -d "${APP_DIR}/${sub}" ]]; then
    rsync -a "${APP_DIR}/${sub}/" "${BACKUP_DIR}/${sub}/"
  fi
done

find "$BACKUP_ROOT" -maxdepth 1 -type d -name '20*' -mtime +"${RETENTION_DAYS}" -exec rm -rf {} + 2>/dev/null || true

echo "[$(date -Iseconds)] ARIA backup completed" | tee -a /var/log/aria_backup.log
