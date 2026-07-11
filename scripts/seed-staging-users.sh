#!/usr/bin/env bash
# Seed default admin + engineer after ARIA containers are healthy.
# Usage: bash scripts/seed-staging-users.sh
# Env: SEED_ADMIN_PASSWORD, SEED_ENGINEER_PASSWORD (optional)

set -euo pipefail

ARIA_ROOT="${ARIA_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
CONTAINER="${ARIA_BACKEND_CONTAINER:-aria-backend}"
ENV_FILE="${ENV_FILE:-$ARIA_ROOT/.env}"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a
  # only export SEED_* lines to avoid clobbering shell
  while IFS= read -r line || [[ -n "$line" ]]; do
    case "$line" in
      SEED_*=*) export "$line" ;;
    esac
  done < <(grep -E '^SEED_[A-Z0-9_]+=' "$ENV_FILE" | tr -d '\r' || true)
  set +a
fi

ADMIN_USER="${SEED_ADMIN_USERNAME:-admin}"
ADMIN_PASS="${SEED_ADMIN_PASSWORD:-admin123}"
ENG_USER="${SEED_ENGINEER_USERNAME:-engineer}"
ENG_PASS="${SEED_ENGINEER_PASSWORD:-engineer123}"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "ERROR: container not running: $CONTAINER" >&2
  exit 1
fi

# Prefer in-image script; fall back to host copy (older images without COPY scripts)
run_seed() {
  docker exec \
    -e PYTHONPATH=/app \
    -e SEED_ADMIN_USERNAME="$ADMIN_USER" \
    -e SEED_ADMIN_PASSWORD="$ADMIN_PASS" \
    -e SEED_ENGINEER_USERNAME="$ENG_USER" \
    -e SEED_ENGINEER_PASSWORD="$ENG_PASS" \
    -w /app \
    "$CONTAINER" \
    "$@"
}

if docker exec -w /app "$CONTAINER" test -f /app/scripts/seed_default_users.py 2>/dev/null; then
  echo "==> Seeding default users (in-image script)"
  run_seed python scripts/seed_default_users.py
elif [[ -f "$ARIA_ROOT/backend/scripts/seed_default_users.py" ]]; then
  echo "==> Seeding default users (docker cp from host — rebuild backend to bake scripts in)"
  docker cp "$ARIA_ROOT/backend/scripts/seed_default_users.py" "$CONTAINER:/tmp/seed_default_users.py"
  run_seed python /tmp/seed_default_users.py
elif [[ -f "$ARIA_ROOT/backend/scripts/create_admin.py" ]]; then
  echo "==> Fallback: create_admin.py twice"
  docker cp "$ARIA_ROOT/backend/scripts/create_admin.py" "$CONTAINER:/tmp/create_admin.py"
  docker exec -e PYTHONPATH=/app -w /app "$CONTAINER" \
    python /tmp/create_admin.py --username "$ADMIN_USER" --password "$ADMIN_PASS" \
    --display-name "系统管理员" --role kb_admin || true
  docker exec -e PYTHONPATH=/app -w /app "$CONTAINER" \
    python /tmp/create_admin.py --username "$ENG_USER" --password "$ENG_PASS" \
    --display-name "报价工程师" --role quote_engineer || true
else
  echo "ERROR: seed_default_users.py / create_admin.py not found" >&2
  exit 1
fi

echo ""
echo "Login (change passwords after first login on shared staging):"
echo "  admin     / ${ADMIN_PASS}     (kb_admin)"
echo "  engineer  / ${ENG_PASS}  (quote_engineer)"
echo "  URL: http://<host>/"
