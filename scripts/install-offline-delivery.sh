#!/usr/bin/env bash
# Install ARIA from an offline delivery bundle (customer intranet / air-gap).
# Usage:
#   cd /path/to/aria-offline-YYYYMMDD
#   sudo bash scripts/install-offline-delivery.sh
#
# Prereq: NVIDIA driver, Docker, /data mounted. No ollama pull / docker pull.

set -euo pipefail

BUNDLE_ROOT="${BUNDLE_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$BUNDLE_ROOT"
export PATH="/usr/local/bin:${PATH}"

INSTALL_ROOT="${INSTALL_ROOT:-/opt/aria}"
DATA_ROOT="${ARIA_DATA_ROOT:-/data/aria}"
OLLAMA_MODELS_DIR="${OLLAMA_MODELS_DIR:-/data/ollama/models}"
COMPOSE_FILE="${COMPOSE_FILE:-$INSTALL_ROOT/docker-compose.offline.yml}"

echo "==> ARIA offline install"
echo "    Bundle:  $BUNDLE_ROOT"
echo "    Install: $INSTALL_ROOT"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "ERROR: run as root: sudo bash scripts/install-offline-delivery.sh" >&2
  exit 1
fi
command -v nvidia-smi >/dev/null || { echo "ERROR: nvidia-smi missing" >&2; exit 1; }
command -v docker >/dev/null || { echo "ERROR: docker missing" >&2; exit 1; }
[[ -d /data ]] || { echo "ERROR: /data missing" >&2; exit 1; }

mkdir -p "$DATA_ROOT"/{app/{uploads,outputs,knowledge_base,templates,config,feedback},postgres,backups}
mkdir -p "$OLLAMA_MODELS_DIR" "$INSTALL_ROOT"

echo "==> Installing app files"
cp -a "$BUNDLE_ROOT"/app/. "$INSTALL_ROOT/"
if [[ -d "$BUNDLE_ROOT/app/templates" ]]; then
  cp -a "$BUNDLE_ROOT"/app/templates/. "$DATA_ROOT/app/templates/" 2>/dev/null || true
fi
if [[ -d "$BUNDLE_ROOT/app/config" ]]; then
  mkdir -p "$DATA_ROOT/app/config"
  cp -a "$BUNDLE_ROOT"/app/config/. "$DATA_ROOT/app/config/" 2>/dev/null || true
fi
chmod +x "$INSTALL_ROOT"/deploy/scripts/*.sh "$INSTALL_ROOT"/scripts/*.sh 2>/dev/null || true

export ARIA_ROOT="$INSTALL_ROOT"
export ARIA_DATA_ROOT="$DATA_ROOT"
if [[ -f "$INSTALL_ROOT/scripts/seed-runtime-data.sh" ]]; then
  bash "$INSTALL_ROOT/scripts/seed-runtime-data.sh"
fi

if [[ ! -f "$INSTALL_ROOT/.env" ]]; then
  cp "$INSTALL_ROOT/.env.production.example" "$INSTALL_ROOT/.env"
fi
if grep -qE 'change-me|change_me' "$INSTALL_ROOT/.env" 2>/dev/null; then
  PW=$(openssl rand -hex 16)
  JWT=$(openssl rand -hex 32)
  sed -i "s/change-me-strong-password/${PW}/g" "$INSTALL_ROOT/.env"
  sed -i "s/change-me-with-openssl-rand-hex-32/${JWT}/g" "$INSTALL_ROOT/.env"
  sed -i "s/change_me_before_deploy/${PW}/g" "$INSTALL_ROOT/.env"
  sed -i "s/change_me_jwt_before_deploy/${JWT}/g" "$INSTALL_ROOT/.env"
  echo "==> Generated secrets in .env"
fi
sed -i 's/^MOCK_LLM=.*/MOCK_LLM=false/' "$INSTALL_ROOT/.env"
sed -i 's/^MOCK_RAG=.*/MOCK_RAG=false/' "$INSTALL_ROOT/.env"
grep -q '^ARIA_UI_PROFILE=' "$INSTALL_ROOT/.env" || echo 'ARIA_UI_PROFILE=r1' >> "$INSTALL_ROOT/.env"
sed -i 's/^ARIA_UI_PROFILE=.*/ARIA_UI_PROFILE=r1/' "$INSTALL_ROOT/.env"
grep -q '^ARIA_DATA_ROOT=' "$INSTALL_ROOT/.env" || echo "ARIA_DATA_ROOT=$DATA_ROOT" >> "$INSTALL_ROOT/.env"
sed -i "s|^ARIA_DATA_ROOT=.*|ARIA_DATA_ROOT=$DATA_ROOT|" "$INSTALL_ROOT/.env"

echo "==> Installing Ollama (offline)"
id ollama >/dev/null 2>&1 || useradd -r -s /bin/false -m -d /usr/share/ollama ollama 2>/dev/null || true

if [[ -f "$BUNDLE_ROOT"/bin/ollama-linux-amd64.tar.zst ]]; then
  command -v zstd >/dev/null 2>&1 || yum install -y zstd 2>/dev/null || dnf install -y zstd 2>/dev/null || true
  tar -C /usr/local -I zstd -xvf "$BUNDLE_ROOT"/bin/ollama-linux-amd64.tar.zst
elif [[ -f "$BUNDLE_ROOT"/bin/ollama-linux-amd64.tgz ]]; then
  tar -C /usr/local -xzf "$BUNDLE_ROOT"/bin/ollama-linux-amd64.tgz
elif [[ -f "$BUNDLE_ROOT"/bin/ollama ]]; then
  install -m 755 "$BUNDLE_ROOT"/bin/ollama /usr/local/bin/ollama
else
  echo "ERROR: no ollama binary in bundle bin/" >&2
  exit 1
fi
chmod 755 /usr/local/bin/ollama

echo "==> Restoring models"
tar -C /data/ollama -xzf "$BUNDLE_ROOT"/models/ollama-models.tar.gz
[[ -d /data/ollama/models ]] || { echo "ERROR: models extract failed" >&2; exit 1; }
chown -R ollama:ollama /data/ollama

tee /etc/systemd/system/ollama.service >/dev/null << EOF
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_MODELS=${OLLAMA_MODELS_DIR}"

[Install]
WantedBy=default.target
EOF
systemctl daemon-reload
systemctl enable --now ollama
sleep 2
curl -sf http://127.0.0.1:11434/api/tags >/dev/null || {
  echo "ERROR: Ollama failed"; journalctl -u ollama -n 40 --no-pager; exit 1
}
echo "==> Ollama OK"
curl -s http://127.0.0.1:11434/api/tags | head -c 500
echo ""

echo "==> docker load (no registry)..."
docker load -i "$BUNDLE_ROOT"/images/aria-stack.tar

if [[ -n "${SUDO_USER:-}" ]]; then
  usermod -aG docker "$SUDO_USER" 2>/dev/null || true
  chown -R "$SUDO_USER:$SUDO_USER" "$INSTALL_ROOT" 2>/dev/null || true
fi

echo "==> Starting ARIA (SKIP_BUILD=true, offline compose)..."
run_start() {
  cd "$INSTALL_ROOT"
  export ARIA_ROOT="$INSTALL_ROOT"
  export COMPOSE_FILE="$COMPOSE_FILE"
  export ENV_FILE="$INSTALL_ROOT/.env"
  export SKIP_BUILD=true
  bash deploy/scripts/start.sh
}

if [[ -n "${SUDO_USER:-}" ]]; then
  su - "$SUDO_USER" -c "cd '$INSTALL_ROOT' && ARIA_ROOT='$INSTALL_ROOT' COMPOSE_FILE='$COMPOSE_FILE' ENV_FILE='$INSTALL_ROOT/.env' SKIP_BUILD=true bash deploy/scripts/start.sh"
else
  run_start
fi

echo "==> Seeding default users..."
if [[ -f "$INSTALL_ROOT/scripts/seed-staging-users.sh" ]]; then
  sudo -u "${SUDO_USER:-root}" bash "$INSTALL_ROOT/scripts/seed-staging-users.sh" || \
    bash "$BUNDLE_ROOT/scripts/seed-staging-users.sh" || true
elif [[ -f "$BUNDLE_ROOT/scripts/seed-staging-users.sh" ]]; then
  ARIA_ROOT="$INSTALL_ROOT" bash "$BUNDLE_ROOT/scripts/seed-staging-users.sh" || true
fi

echo ""
echo "================================================"
echo " Offline install complete"
echo " Health: curl -s http://127.0.0.1/api/v1/health"
echo " Login:  admin / admin123 ; engineer / engineer123  (override via SEED_*_PASSWORD)"
echo "================================================"
