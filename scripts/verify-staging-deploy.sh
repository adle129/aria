#!/usr/bin/env bash
# Verify Aliyun staging deploy matches package stamp and key files are in running images.
# Usage: cd /opt/aria && bash scripts/verify-staging-deploy.sh
# Env: ARIA_ROOT, HEALTH_URL (default http://127.0.0.1/api/v1/health)

set -euo pipefail

ARIA_ROOT="${ARIA_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ARIA_ROOT"

HEALTH_URL="${HEALTH_URL:-http://127.0.0.1/api/v1/health}"
STAMP_FILE="${STAMP_FILE:-$ARIA_ROOT/deploy-stamp.txt}"
FAIL=0

echo "==> verify-staging-deploy"
echo "    Root:   $ARIA_ROOT"
echo "    Health: $HEALTH_URL"

if [[ ! -f "$STAMP_FILE" ]]; then
  echo "ERROR: missing $STAMP_FILE (re-package with package-aliyun-staging.ps1)" >&2
  exit 1
fi

# shellcheck disable=SC1090
# Load KEY=VALUE lines (ignore comments / blanks)
while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%$'\r'}"
  [[ -z "$line" || "$line" =~ ^# ]] && continue
  if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
    export "${BASH_REMATCH[1]}=${BASH_REMATCH[2]}"
  fi
done < "$STAMP_FILE"

EXPECTED_SHA="${deploy_sha:-}"
if [[ -z "$EXPECTED_SHA" || "$EXPECTED_SHA" == "unknown" ]]; then
  echo "ERROR: deploy_sha missing in stamp file" >&2
  exit 1
fi
echo "    Expected deploy_sha: $EXPECTED_SHA"

# --- containers running ---
for c in aria-backend aria-worker aria-frontend aria-postgres aria-nginx; do
  if ! docker ps --format '{{.Names}}' | grep -qx "$c"; then
    echo "ERROR: container not running: $c" >&2
    FAIL=1
  else
    echo "    ok container: $c"
  fi
done

# --- baked stamp inside images ---
check_file_in() {
  local container="$1" path="$2"
  if ! docker exec "$container" test -f "$path"; then
    echo "ERROR: $container missing $path (stale image / incomplete build)" >&2
    FAIL=1
  else
    echo "    ok $container:$path"
  fi
}

if docker ps --format '{{.Names}}' | grep -qx aria-backend; then
  check_file_in aria-backend /app/DEPLOY_SHA
  check_file_in aria-backend /app/app/utils/knowledge_paths.py
  BAKED="$(docker exec aria-backend cat /app/DEPLOY_SHA 2>/dev/null | tr -d '\r\n' || true)"
  if [[ -n "$BAKED" && "$BAKED" != "$EXPECTED_SHA" ]]; then
    echo "ERROR: backend /app/DEPLOY_SHA='$BAKED' != stamp '$EXPECTED_SHA'" >&2
    echo "  Fix: export DEPLOY_SHA from stamp and rebuild (do NOT docker cp hotfixes as the lasting fix)" >&2
    FAIL=1
  elif [[ -n "$BAKED" ]]; then
    echo "    ok backend DEPLOY_SHA matches stamp"
  fi
fi

if docker ps --format '{{.Names}}' | grep -qx aria-worker; then
  check_file_in aria-worker /app/DEPLOY_SHA
  check_file_in aria-worker /app/app/utils/knowledge_paths.py
  WBAKED="$(docker exec aria-worker cat /app/DEPLOY_SHA 2>/dev/null | tr -d '\r\n' || true)"
  if [[ -n "$WBAKED" && "$WBAKED" != "$EXPECTED_SHA" ]]; then
    echo "ERROR: worker /app/DEPLOY_SHA='$WBAKED' != stamp '$EXPECTED_SHA'" >&2
    FAIL=1
  fi
fi

if docker ps --format '{{.Names}}' | grep -qx aria-frontend; then
  check_file_in aria-frontend /app/DEPLOY_SHA
  FBAKED="$(docker exec aria-frontend cat /app/DEPLOY_SHA 2>/dev/null | tr -d '\r\n' || true)"
  if [[ -n "$FBAKED" && "$FBAKED" != "$EXPECTED_SHA" ]]; then
    echo "ERROR: frontend /app/DEPLOY_SHA='$FBAKED' != stamp '$EXPECTED_SHA'" >&2
    FAIL=1
  fi
fi

# --- health API ---
BODY=""
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if BODY="$(curl -sf --max-time 5 "$HEALTH_URL" 2>/dev/null)"; then
    break
  fi
  sleep 2
done

if [[ -z "$BODY" ]]; then
  echo "ERROR: health unreachable: $HEALTH_URL" >&2
  FAIL=1
else
  HEALTH_SHA="$(printf '%s' "$BODY" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("deploy_sha",""))' 2>/dev/null || true)"
  MOCK_LLM="$(printf '%s' "$BODY" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("mock_llm", True))' 2>/dev/null || true)"
  MOCK_RAG="$(printf '%s' "$BODY" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("mock_rag", True))' 2>/dev/null || true)"
  echo "    health deploy_sha=$HEALTH_SHA mock_llm=$MOCK_LLM mock_rag=$MOCK_RAG"
  if [[ "$HEALTH_SHA" != "$EXPECTED_SHA" ]]; then
    echo "ERROR: /health deploy_sha='$HEALTH_SHA' != stamp '$EXPECTED_SHA'" >&2
    echo "  Images were not rebuilt with this package. Re-run deploy (incremental build, not --no-cache)." >&2
    FAIL=1
  fi
  if [[ "$MOCK_LLM" != "False" && "$MOCK_LLM" != "false" ]]; then
    echo "ERROR: staging requires MOCK_LLM=false (got $MOCK_LLM)" >&2
    FAIL=1
  fi
  if [[ "$MOCK_RAG" != "False" && "$MOCK_RAG" != "false" ]]; then
    echo "ERROR: staging requires MOCK_RAG=false (got $MOCK_RAG)" >&2
    FAIL=1
  fi
fi

if [[ "$FAIL" -ne 0 ]]; then
  echo "==> VERIFY FAILED" >&2
  exit 1
fi
echo "==> VERIFY OK (deploy_sha=$EXPECTED_SHA)"
