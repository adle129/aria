#!/usr/bin/env bash
# Package an offline ARIA delivery bundle (run on staging ECS after models + images exist).
#
# Usage:
#   cd /opt/aria
#   bash scripts/package-offline-delivery.sh
#   bash scripts/package-offline-delivery.sh /data/aria-delivery
#
# Output: ${OUT_DIR}/aria-offline-YYYYMMDD/ (+ .tar and optional .tar.part*)

set -euo pipefail

ARIA_ROOT="${ARIA_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ARIA_ROOT"
export PATH="/usr/local/bin:${PATH}"

OUT_BASE="${1:-${OFFLINE_OUT:-/data/aria-delivery}}"
STAMP="$(date +%Y%m%d)"
OUT_DIR="${OUT_BASE}/aria-offline-${STAMP}"
OLLAMA_MODELS_DIR="${OLLAMA_MODELS_DIR:-/data/ollama/models}"
SPLIT_GB="${SPLIT_GB:-4}"

echo "==> ARIA offline delivery package"
echo "    Root: $ARIA_ROOT"
echo "    Out:  $OUT_DIR"

mkdir -p "$OUT_DIR"/{images,models,bin,app,scripts,docs}

# --- Ollama binary / tarball ---
if [[ -x /usr/local/bin/ollama ]]; then
  cp -a /usr/local/bin/ollama "$OUT_DIR/bin/ollama"
elif command -v ollama >/dev/null 2>&1; then
  cp -a "$(command -v ollama)" "$OUT_DIR/bin/ollama"
else
  echo "WARN: ollama binary not found" >&2
fi
for t in /tmp/ollama-linux-amd64.tar.zst /tmp/ollama-linux-amd64.tgz; do
  if [[ -f "$t" ]]; then
    echo "==> Bundling $(basename "$t")"
    cp -a "$t" "$OUT_DIR/bin/"
    break
  fi
done

# --- Models ---
if [[ ! -d "$OLLAMA_MODELS_DIR" ]]; then
  echo "ERROR: models dir missing: $OLLAMA_MODELS_DIR" >&2
  exit 1
fi
echo "==> Archiving models from $OLLAMA_MODELS_DIR..."
sudo tar -C "$(dirname "$OLLAMA_MODELS_DIR")" -czf "$OUT_DIR/models/ollama-models.tar.gz" "$(basename "$OLLAMA_MODELS_DIR")"
sudo chown "$(id -u):$(id -g)" "$OUT_DIR/models/ollama-models.tar.gz" 2>/dev/null || true
ls -lh "$OUT_DIR/models/ollama-models.tar.gz"

# --- Retag app images to stable offline tags ---
echo "==> Retagging images to *:offline"
retag_from_container() {
  local cname="$1"
  local tag="$2"
  local img
  img="$(docker inspect -f '{{.Image}}' "$cname" 2>/dev/null || true)"
  if [[ -z "$img" ]]; then
    img="$(docker inspect -f '{{.Config.Image}}' "$cname" 2>/dev/null || true)"
  fi
  if [[ -n "$img" ]]; then
    docker tag "$img" "$tag" 2>/dev/null || docker tag "$(docker inspect -f '{{.Image}}' "$cname")" "$tag"
    echo "    $cname -> $tag"
  else
    echo "WARN: container $cname not found — start ARIA first" >&2
  fi
}
retag_from_container aria-backend aria-backend:offline
retag_from_container aria-worker aria-worker:offline
retag_from_container aria-frontend aria-frontend:offline

# --- docker save ---
SAVE_LIST=(
  "pgvector/pgvector:pg16"
  "nginx:alpine"
  "aria-backend:offline"
  "aria-worker:offline"
  "aria-frontend:offline"
)
EXISTING=()
for img in "${SAVE_LIST[@]}"; do
  if docker image inspect "$img" >/dev/null 2>&1; then
    EXISTING+=("$img")
  else
    echo "WARN: missing image $img" >&2
  fi
done
if [[ ${#EXISTING[@]} -lt 5 ]]; then
  echo "ERROR: need postgres+nginx+backend+worker+frontend images. Finish staging deploy first." >&2
  printf '  have: %s\n' "${EXISTING[@]:-none}"
  exit 1
fi

echo "==> docker save..."
docker save -o "$OUT_DIR/images/aria-stack.tar" "${EXISTING[@]}"
ls -lh "$OUT_DIR/images/aria-stack.tar"

# --- App files (offline compose: no build) ---
echo "==> Copying offline compose + deploy scripts"
cp -a docker-compose.offline.yml "$OUT_DIR/app/"
cp -a docker-compose.prod.yml "$OUT_DIR/app/" 2>/dev/null || true
cp -a .env.production.example "$OUT_DIR/app/"
cp -a nginx "$OUT_DIR/app/"
cp -a samples "$OUT_DIR/app/" 2>/dev/null || true
mkdir -p "$OUT_DIR/app/deploy/scripts" "$OUT_DIR/app/scripts" "$OUT_DIR/app/backend-scripts"
cp -a deploy/scripts/*.sh "$OUT_DIR/app/deploy/scripts/"
cp -a scripts/ensure-env.sh "$OUT_DIR/app/scripts/"
cp -a scripts/seed-staging-users.sh "$OUT_DIR/app/scripts/"
cp -a scripts/seed-runtime-data.sh "$OUT_DIR/app/scripts/"
cp -a scripts/seed-staging-users.sh "$OUT_DIR/scripts/"
cp -a scripts/seed-runtime-data.sh "$OUT_DIR/scripts/"
cp -a scripts/install-offline-delivery.sh "$OUT_DIR/scripts/"
cp -a backend/scripts/seed_default_users.py backend/scripts/create_admin.py \
  "$OUT_DIR/app/backend-scripts/" 2>/dev/null || true
# Host layout expected by seed-staging-users.sh fallback
mkdir -p "$OUT_DIR/app/backend/scripts"
cp -a backend/scripts/seed_default_users.py backend/scripts/create_admin.py \
  "$OUT_DIR/app/backend/scripts/" 2>/dev/null || true
if [[ -d backend/data/templates ]]; then
  mkdir -p "$OUT_DIR/app/templates"
  cp -a backend/data/templates/* "$OUT_DIR/app/templates/" 2>/dev/null || true
fi
if [[ -f backend/data/config/dimension_baseline.v1.json ]]; then
  mkdir -p "$OUT_DIR/app/config" "$OUT_DIR/app/backend/data/config"
  cp -a backend/data/config/dimension_baseline.v1.json "$OUT_DIR/app/config/"
  cp -a backend/data/config/dimension_baseline.v1.json "$OUT_DIR/app/backend/data/config/"
fi

cat > "$OUT_DIR/MANIFEST.txt" << EOF
ARIA offline delivery
packaged_at=$(date -Iseconds)
host=$(hostname)
compose=docker-compose.offline.yml
ollama_models=$OLLAMA_MODELS_DIR
images:
$(printf '  - %s\n' "${EXISTING[@]}")
EOF

cat > "$OUT_DIR/README.txt" << 'EOF'
ARIA 离线交付包

客户内网（已挂载 /data，已装 Docker + NVIDIA 驱动）：

  cd /path/to/aria-offline-YYYYMMDD
  sudo bash scripts/install-offline-delivery.sh

详见 docs/INSTALL.md
EOF

if [[ -f docs/offline-customer-deploy.md ]]; then
  cp -a docs/offline-customer-deploy.md "$OUT_DIR/docs/INSTALL.md"
else
  cp -a "$OUT_DIR/README.txt" "$OUT_DIR/docs/INSTALL.md"
fi

echo "==> Creating archive..."
PARENT="$(dirname "$OUT_DIR")"
BASE="$(basename "$OUT_DIR")"
tar -C "$PARENT" -cf "${OUT_DIR}.tar" "$BASE"
ls -lh "${OUT_DIR}.tar"

if command -v split >/dev/null 2>&1; then
  echo "==> Splitting into ${SPLIT_GB}G parts..."
  split -b "${SPLIT_GB}G" -d "${OUT_DIR}.tar" "${OUT_DIR}.tar.part"
  ls -lh "${OUT_DIR}.tar.part"* 2>/dev/null || true
  echo "    Reassemble: cat ${BASE}.tar.part* > ${BASE}.tar && tar -xf ${BASE}.tar"
fi

echo ""
echo "================================================"
echo " Offline package ready: $OUT_DIR"
echo " Tarball: ${OUT_DIR}.tar"
echo "================================================"
