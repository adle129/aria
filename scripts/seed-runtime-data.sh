#!/usr/bin/env bash
# Seed runtime files onto the ARIA data volume (idempotent).
# - Excel/QA templates (only when templates dir is empty)
# - F1.10 dimension_baseline.v1.json (required for RFQ parse)
#
# Usage:
#   ARIA_ROOT=/opt/aria ARIA_DATA_ROOT=/data/aria bash scripts/seed-runtime-data.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARIA_ROOT="${ARIA_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
DATA_ROOT="${ARIA_DATA_ROOT:-/data/aria}"
APP_DIR="${DATA_ROOT}/app"

mkdir -p "$APP_DIR"/{uploads,outputs,knowledge_base,templates,config,feedback}

if [[ -d "$ARIA_ROOT/backend/data/templates" ]] && [[ -z "$(ls -A "$APP_DIR/templates" 2>/dev/null || true)" ]]; then
  echo "==> Seeding Excel/QA templates → ${APP_DIR}/templates"
  cp -a "$ARIA_ROOT"/backend/data/templates/. "$APP_DIR/templates/"
fi

BASELINE_NAME="dimension_baseline.v1.json"
BASELINE_DST="${APP_DIR}/config/${BASELINE_NAME}"
BASELINE_SRC=""
for cand in \
  "${ARIA_ROOT}/backend/data/config/${BASELINE_NAME}" \
  "${ARIA_ROOT}/app/config/${BASELINE_NAME}" \
  "${ARIA_ROOT}/config/${BASELINE_NAME}"
do
  if [[ -f "$cand" ]]; then
    BASELINE_SRC="$cand"
    break
  fi
done

if [[ -z "$BASELINE_SRC" ]]; then
  echo "ERROR: ${BASELINE_NAME} seed not found under ${ARIA_ROOT}" >&2
  echo "  Expected: backend/data/config/${BASELINE_NAME}" >&2
  exit 1
fi

if [[ ! -f "$BASELINE_DST" ]]; then
  echo "==> Seeding dimension baseline → ${BASELINE_DST}"
  cp -a "$BASELINE_SRC" "$BASELINE_DST"
else
  echo "==> dimension baseline present: ${BASELINE_DST}"
fi
