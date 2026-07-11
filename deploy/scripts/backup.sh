#!/usr/bin/env bash
# Daily backup: PostgreSQL dump + app data directories (R1-KH09)
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
MIN_FREE_GB="${BACKUP_MIN_FREE_GB:-5}"

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1" >&2
    exit 1
  }
}

estimate_backup_bytes() {
  local total=0
  local path size
  for path in \
    "$APP_DIR/uploads" \
    "$APP_DIR/outputs" \
    "$APP_DIR/knowledge_base" \
    "$APP_DIR/templates" \
    "$APP_DIR/config" \
    "$APP_DIR/feedback" \
    "$APP_DIR/manpower_baselines.json" \
    "$APP_DIR/pgvector_index_state.json"; do
    if [[ -e "$path" ]]; then
      size="$(du -sb "$path" 2>/dev/null | awk '{print $1}')"
      total=$((total + size))
    fi
  done
  echo "$((total * 2))"
}

assert_backup_capacity() {
  mkdir -p "$BACKUP_ROOT"
  local required available_kb
  required="$(estimate_backup_bytes)"
  available_kb="$(df -Pk "$BACKUP_ROOT" | awk 'NR==2 {print $4}')"
  local available_bytes=$((available_kb * 1024))
  local min_free_bytes=$((MIN_FREE_GB * 1024 * 1024 * 1024))
  if (( available_bytes < required || available_bytes < min_free_bytes )); then
    echo "[$(date -Iseconds)] Backup aborted: insufficient space (need ${required} bytes, free ${available_bytes} bytes)" >&2
    exit 50
  fi
}

require_command docker
require_command rsync
require_command df

assert_backup_capacity
mkdir -p "$BACKUP_DIR"

echo "[$(date -Iseconds)] Backup start -> $BACKUP_DIR"

docker exec "$PG_CONTAINER" pg_dump -U aria_admin aria_db > "${BACKUP_DIR}/aria_db.sql"

for sub in uploads outputs knowledge_base templates config feedback; do
  if [[ -d "${APP_DIR}/${sub}" ]]; then
    rsync -a "${APP_DIR}/${sub}/" "${BACKUP_DIR}/${sub}/"
  fi
done

for file in manpower_baselines.json pgvector_index_state.json; do
  if [[ -f "${APP_DIR}/${file}" ]]; then
    cp -a "${APP_DIR}/${file}" "${BACKUP_DIR}/${file}"
  fi
done

cat > "${BACKUP_DIR}/manifest.json" <<EOF
{
  "backup_date": "${DATE}",
  "aria_data_root": "${ARIA_DATA_ROOT}",
  "includes": [
    "aria_db.sql",
    "uploads",
    "outputs",
    "knowledge_base",
    "templates",
    "config",
    "feedback",
    "manpower_baselines.json",
    "pgvector_index_state.json"
  ],
  "notes": "PostgreSQL logical dump + app files; chroma_db intentionally excluded"
}
EOF

find "$BACKUP_ROOT" -maxdepth 1 -type d -name '20*' -mtime +"${RETENTION_DAYS}" -exec rm -rf {} + 2>/dev/null || true

echo "[$(date -Iseconds)] ARIA backup completed" | tee -a /var/log/aria_backup.log
