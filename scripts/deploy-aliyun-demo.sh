#!/usr/bin/env bash
# ARIA Aliyun remote UI demo — one-shot deploy (run on ECS)
# Usage: cd /opt/aria && bash scripts/deploy-aliyun-demo.sh

set -euo pipefail

ARIA_ROOT="${ARIA_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ARIA_ROOT"

echo "==> ARIA Aliyun UI demo deploy"
echo "    Root: $ARIA_ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "==> Installing Docker..."
  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y docker docker-compose-plugin 2>/dev/null || {
      curl -fsSL https://get.docker.com | sudo sh
    }
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y docker 2>/dev/null || curl -fsSL https://get.docker.com | sudo sh
  else
    curl -fsSL https://get.docker.com | sudo sh
  fi
  sudo systemctl enable --now docker
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: docker compose plugin required."
  exit 1
fi

# Optional: speed up pulls on Aliyun ECS (safe if file already exists)
if [ ! -f /etc/docker/daemon.json ] && command -v systemctl >/dev/null 2>&1; then
  echo "==> Configuring Docker registry mirrors (first-time)..."
  sudo mkdir -p /etc/docker
  printf '%s\n' '{
  "registry-mirrors": [
    "https://docker.m.daocloud.io"
  ]
}' | sudo tee /etc/docker/daemon.json >/dev/null
  sudo systemctl restart docker || true
  sleep 2
fi

if [ ! -f .env ]; then
  if [ -f .env.aliyun-demo.example ]; then
    cp .env.aliyun-demo.example .env
    echo "==> Created .env from .env.aliyun-demo.example"
  else
    echo "ERROR: missing .env — copy .env.aliyun-demo.example to .env"
    exit 1
  fi
fi

if grep -q "change_me_before_deploy" .env 2>/dev/null; then
  if command -v openssl >/dev/null 2>&1; then
    PW=$(openssl rand -hex 16)
    sed -i "s/change_me_before_deploy/${PW}/g" .env
    echo "==> Generated POSTGRES_PASSWORD in .env"
  else
    echo "ERROR: set POSTGRES_PASSWORD in .env (replace change_me_before_deploy)"
    exit 1
  fi
fi

# Ensure public HTTP port — default 8888 on Aliyun (port 80 often taken by other apps)
if ! grep -qE '^ARIA_DEMO_HTTP_PORT=' .env 2>/dev/null; then
  echo "ARIA_DEMO_HTTP_PORT=8888" >> .env
  echo "==> Set ARIA_DEMO_HTTP_PORT=8888 in .env (default for Aliyun demo)"
fi

HTTP_PORT=8888
if [ -f .env ]; then
  HTTP_PORT=$(grep -E '^ARIA_DEMO_HTTP_PORT=' .env 2>/dev/null | tail -1 | cut -d= -f2 | tr -d ' "' || echo 8888)
fi
HTTP_PORT="${HTTP_PORT:-8888}"

if command -v ss >/dev/null 2>&1; then
  if ss -tlnp 2>/dev/null | grep -q ':80 '; then
    if [ "$HTTP_PORT" = "80" ]; then
      echo "WARN: port 80 already in use. Set ARIA_DEMO_HTTP_PORT=8888 (or another free port) in .env."
    else
      echo "INFO: port 80 in use by another app; ARIA will listen on host port ${HTTP_PORT}."
    fi
  fi
  if ss -tlnp 2>/dev/null | grep -q ":${HTTP_PORT} "; then
    echo "WARN: port ${HTTP_PORT} already in use. Pick another ARIA_DEMO_HTTP_PORT in .env."
  fi
fi

export ARIA_DEMO_HTTP_PORT="${HTTP_PORT}"

echo "==> Deploy stamp (verify tarball landed in this directory):"
if [ -f deploy-stamp.txt ]; then
  cat deploy-stamp.txt
else
  echo "    (no deploy-stamp.txt — older package?)"
fi

if ! grep -q 'demo/rfq-samples' frontend/src/app/rfq/page.tsx 2>/dev/null; then
  echo "ERROR: frontend source in $(pwd) is STALE (missing demo/rfq-samples API hook)."
  echo "       Common causes:"
  echo "         - tar extracted to a different path than you run deploy from"
  echo "         - uploaded an old aria-deploy.tar.gz"
  echo "       Fix: cd /opt/aria && sudo tar -xzf /tmp/aria-deploy.tar.gz -C /opt/aria"
  exit 1
fi
echo "==> Source check OK (RFQ page has demo sample download API)"

echo "==> Generating demo samples (RFQ + knowledge base mocks)..."
if command -v python3 >/dev/null 2>&1; then
  python3 -m pip install -q python-docx 2>/dev/null || true
  python3 scripts/generate_mock_samples.py
else
  echo "    (skipped: python3 not found — run scripts/generate_mock_samples.py manually)"
fi

echo "==> Building and starting containers (MOCK_LLM + MOCK_RAG, no Ollama)..."
echo "    Rebuilding frontend/backend without cache (ensures UI updates apply)..."
docker compose -f docker-compose.aliyun-demo.yml build --no-cache frontend backend
docker compose -f docker-compose.aliyun-demo.yml up -d --force-recreate

echo "==> Waiting for health check (host port ${HTTP_PORT})..."
for i in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${HTTP_PORT}/api/v1/health" >/dev/null 2>&1; then
    echo "==> Health check passed"
    curl -s "http://127.0.0.1:${HTTP_PORT}/api/v1/health" | head -c 500
    echo ""
    PUBLIC_IP=$(curl -sf --max-time 2 http://100.100.100.200/latest/meta-data/eipv4 2>/dev/null || true)
    echo ""
    echo "================================================"
    echo " Deploy complete — ARIA Platform / Quoting Assistant"
    echo " Mode: MOCK_LLM=true, MOCK_RAG=true (experience tier)"
    if [ -n "$PUBLIC_IP" ]; then
      echo " URL:  http://${PUBLIC_IP}:${HTTP_PORT}/"
    else
      echo " URL:  http://<ECS-public-ip>:${HTTP_PORT}/"
    fi
    echo "       (open ${HTTP_PORT}/TCP in security group if not using 80)"
    echo ""
    echo " Verify:"
    echo "   - Header: ARIA platform + Quoting Assistant tag"
    echo "   - Mock LLM / Mock RAG tags"
    echo "   - Sidebar: App workflow / Platform knowledge base"
    echo ""
    echo " Demo RFQ (on RFQ page — download or one-click trial):"
    echo "   - mock_chassis_rfq.docx (PM + Chassis)"
    echo "   - demo_multifunction_rfq.docx (BIW/EE gap alert)"
    echo "================================================"
    exit 0
  fi
  sleep 3
done

echo "ERROR: health check timed out. Run: docker compose -f docker-compose.aliyun-demo.yml logs"
exit 1
