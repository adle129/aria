#!/bin/sh
set -e

if [ "${SKIP_MIGRATE:-false}" != "true" ]; then
  echo "==> bootstrap_db (init_db + alembic)"
  python bootstrap_db.py
fi

exec "$@"
