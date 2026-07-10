#!/usr/bin/env bash
# Queue a full knowledge_base reindex for the production worker.
set -euo pipefail

docker exec aria-backend python - <<'PY'
from sqlalchemy.orm import sessionmaker

from app.config import get_settings
from app.database import engine
from app.services.knowledge_index_job_service import KnowledgeIndexJobService

settings = get_settings()
session = sessionmaker(bind=engine)()
try:
    job, reused = KnowledgeIndexJobService(settings).enqueue(
        session,
        mode="full",
        triggered_by="ops:reindex.sh",
    )
    print("Queued:", job.id, "status=", job.status, "reused=", reused)
finally:
    session.close()
PY

echo "Re-index queued. Check GET /api/v1/knowledge/imports/active for progress."
