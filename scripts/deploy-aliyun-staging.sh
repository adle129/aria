#!/usr/bin/env bash
# ARIA Aliyun R1 staging — one-shot deploy (run on GPU ECS)
# Usage: cd /opt/aria && bash scripts/deploy-aliyun-staging.sh
#
# Prereq: data disk mounted at /data; NVIDIA driver (nvidia-smi OK)
# Profile: production-equivalent (MOCK_*=false, pgvector, worker, AUTH)
#
# Lessons from Guangzhou ECS rollout:
# - Do NOT chown /data/ollama to ecs-user (ollama service writes as user ollama)
# - GitHub install.sh is often unreachable; prefer pre-installed binary
# - Raise public bandwidth peak before model pull; lower after

set -euo pipefail

ARIA_ROOT="${ARIA_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ARIA_ROOT"

COMPOSE_FILE="${COMPOSE_FILE:-$ARIA_ROOT/docker-compose.aliyun-staging.yml}"
ENV_FILE="${ENV_FILE:-$ARIA_ROOT/.env}"
DATA_ROOT="${ARIA_DATA_ROOT:-/data/aria}"
OLLAMA_MODELS_DIR="${OLLAMA_MODELS_DIR:-/data/ollama/models}"
SKIP_MODEL_PULL="${SKIP_MODEL_PULL:-false}"
SKIP_OLLAMA_INSTALL="${SKIP_OLLAMA_INSTALL:-false}"

export PATH="/usr/local/bin:${PATH}"

echo "==> ARIA Aliyun R1 staging deploy"
echo "    Root:    $ARIA_ROOT"
echo "    Compose: $COMPOSE_FILE"
echo "    Data:    $DATA_ROOT"

# --- GPU ---
if ! command -v nvidia-smi >/dev/null 2>&1; then
  echo "ERROR: nvidia-smi not found. Install NVIDIA driver (or use GPU image) before staging deploy." >&2
  exit 1
fi
echo "==> GPU:"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

# --- /data mount ---
if [ ! -d /data ]; then
  echo "ERROR: /data does not exist. Mount the data disk to /data first." >&2
  echo "  Example: sudo mkfs.ext4 /dev/vdb && sudo mkdir -p /data && sudo mount /dev/vdb /data" >&2
  exit 1
fi
if ! mountpoint -q /data 2>/dev/null; then
  echo "WARN: /data exists but is not a mountpoint — ensure the data disk is mounted." >&2
fi

# --- directories ---
echo "==> Creating data directories..."
sudo mkdir -p "$DATA_ROOT"/app/{uploads,outputs,knowledge_base,templates,config,feedback}
sudo mkdir -p "$DATA_ROOT"/postgres "$DATA_ROOT"/backups
sudo mkdir -p "$OLLAMA_MODELS_DIR" /opt/aria
# App data + code: deploy user. Never chown postgres/ — image runs as uid 999.
# Models dir: ollama service user ONLY.
sudo chown -R "$(id -u):$(id -g)" "$DATA_ROOT"/app "$DATA_ROOT"/backups /opt/aria 2>/dev/null || \
  sudo chown -R "$USER:$USER" "$DATA_ROOT"/app "$DATA_ROOT"/backups /opt/aria
if [[ -d "$DATA_ROOT/postgres" ]]; then
  # Official postgres/pgvector image uses uid/gid 999
  sudo chown -R 999:999 "$DATA_ROOT/postgres" || true
fi

# --- Docker ---
if ! command -v docker >/dev/null 2>&1; then
  echo "==> Installing Docker..."
  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y docker docker-compose-plugin 2>/dev/null || curl -fsSL https://get.docker.com | sudo sh
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y docker 2>/dev/null || curl -fsSL https://get.docker.com | sudo sh
  else
    curl -fsSL https://get.docker.com | sudo sh
  fi
  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER" 2>/dev/null || true
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: docker compose plugin required." >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: cannot access Docker as user '$USER'." >&2
  echo "  Fix: sudo usermod -aG docker $USER && newgrp docker" >&2
  echo "  Then re-run: cd /opt/aria && bash scripts/deploy-aliyun-staging.sh" >&2
  exit 1
fi

if [ ! -f /etc/docker/daemon.json ] && command -v systemctl >/dev/null 2>&1; then
  echo "==> Configuring Docker registry mirrors (first-time)..."
  sudo mkdir -p /etc/docker
  printf '%s\n' '{
  "registry-mirrors": [
    "https://docker.m.daocloud.io"
  ],
  "ipv6": false
}' | sudo tee /etc/docker/daemon.json >/dev/null
  sudo systemctl restart docker || true
  sleep 2
fi

# --- .env ---
if [ ! -f "$ENV_FILE" ]; then
  if [ -f .env.aliyun-staging.example ]; then
    cp .env.aliyun-staging.example "$ENV_FILE"
    echo "==> Created .env from .env.aliyun-staging.example"
  else
    echo "ERROR: missing .env — copy .env.aliyun-staging.example to .env" >&2
    exit 1
  fi
fi

if grep -q "change_me_before_deploy" "$ENV_FILE" 2>/dev/null; then
  if command -v openssl >/dev/null 2>&1; then
    PW=$(openssl rand -hex 16)
    sed -i "s/change_me_before_deploy/${PW}/g" "$ENV_FILE"
    echo "==> Generated POSTGRES_PASSWORD in .env"
  else
    echo "ERROR: set POSTGRES_PASSWORD in .env (replace change_me_before_deploy)" >&2
    exit 1
  fi
fi

if grep -q "change_me_jwt_before_deploy" "$ENV_FILE" 2>/dev/null; then
  if command -v openssl >/dev/null 2>&1; then
    JWT=$(openssl rand -hex 32)
    sed -i "s/change_me_jwt_before_deploy/${JWT}/g" "$ENV_FILE"
    echo "==> Generated JWT_SECRET in .env"
  else
    echo "ERROR: set JWT_SECRET in .env (replace change_me_jwt_before_deploy)" >&2
    exit 1
  fi
fi

# Staging must never run as local "dev" (KB Debug UI). Force regardless of leftover .env.
upsert_env() {
  local key="$1" val="$2"
  if grep -qE "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    printf '\n%s=%s\n' "$key" "$val" >> "$ENV_FILE"
  fi
}
upsert_env ARIA_UI_PROFILE r1
upsert_env KB_DEBUG_ENABLED false
# NEXT_PUBLIC_* is build-time; strip accidental local overrides from runtime .env
sed -i '/^NEXT_PUBLIC_ARIA_UI_PROFILE=/d' "$ENV_FILE" 2>/dev/null || true
echo "==> Staging UI gate: ARIA_UI_PROFILE=r1 KB_DEBUG_ENABLED=false"

line="$(grep -E '^ARIA_DATA_ROOT=' "$ENV_FILE" | tail -1 | cut -d= -f2- | tr -d '\r" ' || true)"
[[ -n "$line" ]] && DATA_ROOT="$line"

# --- templates + F1.10 dimension baseline ---
export ARIA_ROOT
export ARIA_DATA_ROOT="$DATA_ROOT"
bash "$ARIA_ROOT/scripts/seed-runtime-data.sh"

# --- Ollama ---
ensure_ollama_user() {
  if ! id ollama >/dev/null 2>&1; then
    sudo useradd -r -s /bin/false -m -d /usr/share/ollama ollama 2>/dev/null || true
  fi
}

install_ollama_from_tarball() {
  local tarball=""
  for c in /tmp/ollama-linux-amd64.tar.zst /tmp/ollama-linux-amd64.tgz /opt/aria/offline/ollama-linux-amd64.tar.zst; do
    if [[ -f "$c" ]]; then
      tarball="$c"
      break
    fi
  done
  if [[ -z "$tarball" ]]; then
    return 1
  fi
  echo "==> Installing Ollama from $tarball"
  if [[ "$tarball" == *.tar.zst ]]; then
    if ! command -v zstd >/dev/null 2>&1; then
      sudo yum install -y zstd 2>/dev/null || sudo dnf install -y zstd 2>/dev/null || true
    fi
    sudo tar -C /usr/local -I zstd -xvf "$tarball"
  else
    sudo tar -C /usr/local -xzf "$tarball"
  fi
  sudo chmod 755 /usr/local/bin/ollama
  return 0
}

write_ollama_unit() {
  ensure_ollama_user
  sudo mkdir -p /data/ollama/models
  sudo chown -R ollama:ollama /data/ollama
  if [[ ! -f /etc/systemd/system/ollama.service ]]; then
    sudo tee /etc/systemd/system/ollama.service >/dev/null << 'EOF'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_MODELS=/data/ollama/models"

[Install]
WantedBy=default.target
EOF
  fi
  sudo mkdir -p /etc/systemd/system/ollama.service.d/
  sudo tee /etc/systemd/system/ollama.service.d/override.conf >/dev/null << EOF
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_MODELS=${OLLAMA_MODELS_DIR}"
EOF
  sudo systemctl daemon-reload
  sudo systemctl enable --now ollama
  sudo chown -R ollama:ollama /data/ollama
}

if ! command -v ollama >/dev/null 2>&1 && [[ ! -x /usr/local/bin/ollama ]]; then
  if [[ "${SKIP_OLLAMA_INSTALL,,}" == "true" ]]; then
    echo "ERROR: ollama not found and SKIP_OLLAMA_INSTALL=true" >&2
    exit 1
  fi
  if ! install_ollama_from_tarball; then
    echo "WARN: Ollama binary missing. Trying official install.sh (often slow/blocked in CN)..."
    if ! curl -fsSL https://ollama.com/install.sh | sh; then
      echo "ERROR: cannot install Ollama from network." >&2
      echo "  Manual: scp ollama-linux-amd64.tar.zst to /tmp/ then re-run this script." >&2
      echo "  See docs/aliyun-staging-deploy.md · Ollama offline install" >&2
      exit 1
    fi
  fi
fi
export PATH="/usr/local/bin:${PATH}"

write_ollama_unit
sleep 2

if ! curl -sf http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "ERROR: Ollama not reachable at http://127.0.0.1:11434" >&2
  echo "  sudo journalctl -u ollama -n 50 --no-pager" >&2
  exit 1
fi
echo "==> Ollama reachable"
# Critical: never leave models dir owned by ecs-user
sudo chown -R ollama:ollama /data/ollama

OLLAMA_MODEL="$(grep -E '^OLLAMA_MODEL=' "$ENV_FILE" | tail -1 | cut -d= -f2- | tr -d '\r" ' || echo qwen2.5:32b)"
EMBEDDING_MODEL="$(grep -E '^EMBEDDING_MODEL=' "$ENV_FILE" | tail -1 | cut -d= -f2- | tr -d '\r" ' || echo nomic-embed-text)"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:32b}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-nomic-embed-text}"

if [[ "${SKIP_MODEL_PULL,,}" != "true" ]]; then
  echo "==> Ensuring models: ${OLLAMA_MODEL}, ${EMBEDDING_MODEL}"
  echo "    Tip: raise ECS public bandwidth peak to 100–200 Mbps before pull; lower after."
  echo "    Offline alternative: docs/offline-customer-deploy.md"
  ollama pull "$OLLAMA_MODEL"
  ollama pull "$EMBEDDING_MODEL"
else
  echo "==> SKIP_MODEL_PULL=true — not pulling models"
fi

# --- deploy stamp -> build args (invalidates app layers; keeps apt/pip cache) ---
# Do NOT use --no-cache for routine updates (LibreOffice apt is slow on Debian mirrors).
if [[ ! -f deploy-stamp.txt ]]; then
  PACKAGED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  DEPLOY_SHA="local-${PACKAGED_AT}"
  printf 'deploy_sha=%s\ngit_sha=nogit\npackaged_at=%s\nprofile=aliyun-staging\ncompose=docker-compose.aliyun-staging.yml\n' \
    "$DEPLOY_SHA" "$PACKAGED_AT" > deploy-stamp.txt
  echo "==> Wrote deploy-stamp.txt (no package stamp found): deploy_sha=$DEPLOY_SHA"
fi

echo "==> Deploy stamp:"
cat deploy-stamp.txt

while IFS= read -r line || [[ -n "$line" ]]; do
  line="${line%$'\r'}"
  [[ -z "$line" || "$line" =~ ^# ]] && continue
  if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]]; then
    export "${BASH_REMATCH[1]}=${BASH_REMATCH[2]}"
  fi
done < deploy-stamp.txt

export DEPLOY_SHA="${deploy_sha:-${DEPLOY_SHA:-unknown}}"
export PACKAGED_AT="${packaged_at:-${PACKAGED_AT:-}}"
export NEXT_PUBLIC_DEPLOY_SHA="$DEPLOY_SHA"
echo "==> Building with DEPLOY_SHA=$DEPLOY_SHA (incremental; apt/pip layers reused)"
echo "    Tip: never use docker compose build --no-cache unless apt packages themselves must refresh."

if [ ! -f "$COMPOSE_FILE" ]; then
  echo "ERROR: compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

# Pre-pull CN base images so Dockerfile.cn build does not hit Docker Hub timeouts
echo "==> Pre-pulling China-mirrored base images (python/node)..."
pull_tag() {
  local src="$1" dest="$2"
  if docker image inspect "$dest" >/dev/null 2>&1; then
    echo "    ok (local): $dest"
    return 0
  fi
  if docker pull "$src"; then
    docker tag "$src" "$dest"
    echo "    pulled: $dest"
  else
    echo "WARN: failed to pull $src — build may hit Docker Hub timeout" >&2
  fi
}
pull_tag docker.m.daocloud.io/library/python:3.11-slim python:3.11-slim
pull_tag docker.m.daocloud.io/library/node:20-alpine node:20-alpine
pull_tag docker.m.daocloud.io/pgvector/pgvector:pg16 pgvector/pgvector:pg16 || true

# Explicit rebuild so DEPLOY_SHA change is always applied before up
echo "==> docker compose build (backend worker frontend)..."
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build backend worker frontend

echo "==> Starting ARIA (production start.sh + staging compose)..."
export COMPOSE_FILE
export ENV_FILE
export ARIA_ROOT
# start.sh may rebuild again; env DEPLOY_SHA/PACKAGED_AT already exported for compose interpolation
bash "$ARIA_ROOT/deploy/scripts/start.sh"

echo "==> Seeding default admin + engineer accounts..."
bash "$ARIA_ROOT/scripts/seed-staging-users.sh" || {
  echo "WARN: user seed failed — run: bash scripts/seed-staging-users.sh" >&2
}

echo "==> Post-deploy verification (containers + /api/v1/health)..."
if ! bash "$ARIA_ROOT/scripts/verify-staging-deploy.sh"; then
  echo "ERROR: post-deploy health-check failed — see messages above." >&2
  echo "  Re-run: cd $ARIA_ROOT && bash scripts/verify-staging-deploy.sh" >&2
  echo "  Health: curl -s http://127.0.0.1/api/v1/health | python3 -m json.tool" >&2
  exit 1
fi

echo "==> Health snapshot:"
curl -sf --max-time 5 http://127.0.0.1/api/v1/health | python3 -m json.tool || true

PUBLIC_IP=$(curl -sf --max-time 2 http://100.100.100.200/latest/meta-data/eipv4 2>/dev/null || true)
echo ""
echo "================================================"
echo " Deploy complete — ARIA R1 staging (Aliyun)"
echo " Mode: MOCK_LLM=false, MOCK_RAG=false, ARIA_UI_PROFILE=r1"
echo " deploy_sha: ${DEPLOY_SHA}"
echo " Health-check: PASSED"
echo " Model: ${OLLAMA_MODEL} + ${EMBEDDING_MODEL}"
if [ -n "$PUBLIC_IP" ]; then
  echo " URL:  http://${PUBLIC_IP}/"
else
  echo " URL:  http://<ECS-public-ip>/"
fi
echo ""
echo " Default logins (staging):"
echo "   admin     / ${SEED_ADMIN_PASSWORD:-admin123}      (kb_admin)"
echo "   engineer  / ${SEED_ENGINEER_PASSWORD:-engineer123} (quote_engineer)"
echo " Health: curl -s http://127.0.0.1/api/v1/health | python3 -m json.tool"
echo " Verify: bash scripts/verify-staging-deploy.sh"
echo " Offline pack: bash scripts/package-offline-delivery.sh"
echo "================================================"
