# 生产部署工程文件规格

**状态：** 已实现（见仓库 `docker-compose.prod.yml` 与 `deploy/scripts/`）  
**关联：** [deployment-guide.md](../deployment-guide.md) · [customer-it-infrastructure.md](../customer-it-infrastructure.md)

仓库应包含以下文件（若尚未存在，按本节创建）：

| 文件 | 用途 |
|------|------|
| `docker-compose.prod.yml` | 生产 bind mount |
| `.env.production.example` | 生产环境变量模板 |
| `deploy/scripts/start.sh` | 启动 |
| `deploy/scripts/stop.sh` | 停止 |
| `deploy/scripts/backup.sh` | 日备 |
| `deploy/scripts/reindex.sh` | 全量 ingest |

---

## docker-compose.prod.yml

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: aria-postgres
    environment:
      POSTGRES_DB: aria_db
      POSTGRES_USER: aria_admin
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in .env}
    volumes:
      - ${ARIA_DATA_ROOT:-/data/aria}/postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U aria_admin -d aria_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  backend:
    build: ./backend
    container_name: aria-backend
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql://aria_admin:${POSTGRES_PASSWORD}@postgres:5432/aria_db
    volumes:
      - ${ARIA_DATA_ROOT:-/data/aria}/app:/app/data
    depends_on:
      postgres:
        condition: service_healthy
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped

  worker:
    build: ./backend
    container_name: aria-worker
    command: ["python", "-m", "app.worker"]
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql://aria_admin:${POSTGRES_PASSWORD}@postgres:5432/aria_db
    volumes:
      - ${ARIA_DATA_ROOT:-/data/aria}/app:/app/data
    depends_on:
      postgres:
        condition: service_healthy
    extra_hosts:
      - "host.docker.internal:host-gateway"
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      args:
        NEXT_PUBLIC_API_BASE_URL: /api/v1
    container_name: aria-frontend
    depends_on:
      - backend
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: aria-nginx
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - backend
      - frontend
    restart: unless-stopped
```

---

## .env.production.example（摘要）

```bash
ARIA_DATA_ROOT=/data/aria
POSTGRES_PASSWORD=change-me-strong-password
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:32b
EMBEDDING_MODEL=nomic-embed-text
MOCK_LLM=false
MOCK_RAG=false
OLLAMA_MAX_CONCURRENT=1
# CHROMA_PATH 仅 Demo 遗留；R1 向量在 PostgreSQL pgvector
UPLOAD_PATH=/app/data/uploads
OUTPUT_PATH=/app/data/outputs
KNOWLEDGE_BASE_PATH=/app/data/knowledge_base
TEMPLATE_PATH=/app/data/templates
```

---

## deploy/scripts/reindex.sh

```bash
#!/usr/bin/env bash
set -euo pipefail
docker exec aria-backend python scripts/ingest_documents.py
echo "Re-index completed (full ingest)."
```

`start.sh` / `stop.sh` / `backup.sh` 全文如下（写入 `deploy/scripts/` 并 `chmod +x`）：

### start.sh

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARIA_ROOT="${ARIA_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-$ARIA_ROOT/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ARIA_ROOT/.env}"
if [[ ! -f "$COMPOSE_FILE" ]]; then echo "ERROR: $COMPOSE_FILE not found" >&2; exit 1; fi
if [[ ! -f "$ENV_FILE" ]]; then echo "ERROR: $ENV_FILE not found" >&2; exit 1; fi
cd "$ARIA_ROOT"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
echo "ARIA started."
```

### stop.sh

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARIA_ROOT="${ARIA_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-$ARIA_ROOT/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-$ARIA_ROOT/.env}"
cd "$ARIA_ROOT"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
echo "ARIA stopped."
```

### backup.sh

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARIA_ROOT="${ARIA_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
ENV_FILE="${ENV_FILE:-$ARIA_ROOT/.env}"
if [[ -f "$ENV_FILE" ]]; then set -a; source "$ENV_FILE"; set +a; fi
ARIA_DATA_ROOT="${ARIA_DATA_ROOT:-/data/aria}"
APP_DIR="${ARIA_DATA_ROOT}/app"
BACKUP_ROOT="${ARIA_DATA_ROOT}/backups"
DATE="$(date +%Y%m%d)"
BACKUP_DIR="${BACKUP_ROOT}/${DATE}"
PG_CONTAINER="${PG_CONTAINER:-aria-postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
mkdir -p "$BACKUP_DIR"
docker exec "$PG_CONTAINER" pg_dump -U aria_admin aria_db > "${BACKUP_DIR}/aria_db.sql"
for sub in uploads outputs knowledge_base templates; do
  [[ -d "${APP_DIR}/${sub}" ]] && rsync -a "${APP_DIR}/${sub}/" "${BACKUP_DIR}/${sub}/"
done
find "$BACKUP_ROOT" -maxdepth 1 -type d -name '20*' -mtime +"${RETENTION_DAYS}" -exec rm -rf {} + 2>/dev/null || true
echo "[$(date -Iseconds)] ARIA backup completed" | tee -a /var/log/aria_backup.log
```

---

## 验收

```bash
export ARIA_DATA_ROOT=/data/aria
docker compose -f docker-compose.prod.yml config   # 应显示 bind 至 ${ARIA_DATA_ROOT}
./run_tests.ps1   # 仍使用 docker-compose.yml，须全绿
```
