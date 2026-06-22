#!/usr/bin/env bash
# ARIA 阿里云远程 UI/流程体验环境 — 一键部署（在 ECS 上执行）
# 前置：安全组放行 80/TCP；建议 SSH 仅白名单 IP
# 用法：
#   cd /opt/aria && bash scripts/deploy-aliyun-demo.sh
#   或：ARIA_ROOT=/opt/aria bash scripts/deploy-aliyun-demo.sh

set -euo pipefail

ARIA_ROOT="${ARIA_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
cd "$ARIA_ROOT"

echo "==> ARIA 阿里云 UI Demo 部署"
echo "    目录: $ARIA_ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "==> 安装 Docker..."
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
  echo "ERROR: 需要 docker compose 插件。请安装 docker-compose-plugin 或 Docker CE 最新版。"
  exit 1
fi

if [ ! -f .env ]; then
  if [ -f .env.aliyun-demo.example ]; then
    cp .env.aliyun-demo.example .env
    echo "==> 已从 .env.aliyun-demo.example 创建 .env — 请修改 POSTGRES_PASSWORD 后重新运行"
    exit 1
  else
    echo "ERROR: 缺少 .env，请复制 .env.aliyun-demo.example 为 .env"
    exit 1
  fi
fi

if grep -q "change_me_before_deploy" .env 2>/dev/null; then
  echo "ERROR: 请先在 .env 中设置强密码 POSTGRES_PASSWORD（替换 change_me_before_deploy）"
  exit 1
fi

echo "==> 生成演示样例（RFQ + 知识库 Mock 文档）..."
if command -v python3 >/dev/null 2>&1; then
  python3 -m pip install -q python-docx 2>/dev/null || true
  python3 scripts/generate_mock_samples.py
else
  echo "    (跳过: 未找到 python3，请手动运行 scripts/generate_mock_samples.py)"
fi

echo "==> 构建并启动容器（MOCK_LLM + MOCK_RAG，无 Ollama）..."
docker compose -f docker-compose.aliyun-demo.yml up --build -d

echo "==> 等待服务就绪..."
for i in $(seq 1 60); do
  if curl -sf http://127.0.0.1/api/v1/health >/dev/null 2>&1; then
    echo "==> 健康检查通过"
    curl -s http://127.0.0.1/api/v1/health | head -c 500
    echo ""
    PUBLIC_IP=$(curl -sf --max-time 2 http://100.100.100.200/latest/meta-data/eipv4 2>/dev/null || true)
    echo ""
    echo "================================================"
    echo " 部署完成 — 远程 UI/流程体验环境"
    echo " 模式: MOCK_LLM=true, MOCK_RAG=true（非真实 LLM）"
    if [ -n "$PUBLIC_IP" ]; then
      echo " 访问: http://${PUBLIC_IP}/"
    else
      echo " 访问: http://<ECS公网IP>/"
    fi
    echo " 演示 RFQ:"
    echo "   - samples/rfq/mock_chassis_rfq.docx（基础对标）"
    echo "   - samples/rfq/demo_multifunction_rfq.docx（含 BIW/EE，可触发工程领域缺口提示）"
    echo "================================================"
    exit 0
  fi
  sleep 3
done

echo "ERROR: 健康检查超时。请执行: docker compose -f docker-compose.aliyun-demo.yml logs"
exit 1
