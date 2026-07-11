#!/bin/sh
set -e

# Volume mount replaces /app/data; seed F1.10 baseline from image if missing.
SEED_BASELINE=/app/seed/config/dimension_baseline.v1.json
DST_BASELINE=/app/data/config/dimension_baseline.v1.json
if [ -f "$SEED_BASELINE" ]; then
  mkdir -p /app/data/config
  if [ ! -f "$DST_BASELINE" ]; then
    echo "==> Seeding dimension_baseline.v1.json into data volume"
    cp "$SEED_BASELINE" "$DST_BASELINE"
  fi
fi

if [ "${SKIP_MIGRATE:-false}" != "true" ]; then
  echo "==> bootstrap_db (init_db + alembic)"
  python bootstrap_db.py
fi

exec "$@"
