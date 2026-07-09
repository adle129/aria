#!/usr/bin/env bash
# Re-index knowledge_base engagements into pgvector (production worker container).
set -euo pipefail

docker exec aria-backend python - <<'PY'
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.database import engine
from app.services.engagement_ingest_service import EngagementIngestService
from app.services.rag_service import RAGService

settings = get_settings()
session = sessionmaker(bind=engine)()
try:
    result = EngagementIngestService(settings, session).import_all()
finally:
    session.close()

stats = RAGService(settings).get_stats()
print("Indexed:", result)
print("KB stats:", stats.get("total_chunks"), "chunks,", stats.get("total_projects"), "projects")
PY

echo "Re-index completed."
