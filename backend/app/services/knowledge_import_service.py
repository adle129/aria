from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.knowledge_import import KnowledgeImport
from app.models.task_job import TaskJob
from app.repositories.knowledge_import_repository import KnowledgeImportRepository


class KnowledgeImportService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = KnowledgeImportRepository(db)

    def create_for_job(self, job: TaskJob) -> KnowledgeImport:
        existing = self.repo.get_by_job_id(job.id)
        if existing is not None:
            return existing
        payload = job.payload or {}
        record = KnowledgeImport(
            job_id=job.id,
            triggered_by=payload.get("triggered_by"),
            batch_id=payload.get("batch_id"),
            mode=payload.get("mode", "full"),
            status=job.status,
            started_at=job.started_at,
            failed_files=[],
            engagements=[],
        )
        return self.repo.create(record)

    def sync_job_started(self, job: TaskJob) -> KnowledgeImport:
        record = self.repo.get_by_job_id(job.id) or self.create_for_job(job)
        record.status = "running"
        record.started_at = job.started_at or datetime.now(timezone.utc)
        return self.repo.update(record)

    def sync_job_finished(
        self,
        job: TaskJob,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> KnowledgeImport:
        record = self.repo.get_by_job_id(job.id) or self.create_for_job(job)
        record.status = job.status
        record.finished_at = job.finished_at or datetime.now(timezone.utc)
        record.error_message = error or job.error_message
        payload = job.payload or {}
        record.generation_id = payload.get("generation_id")
        if result:
            record.new_documents = int(result.get("new_documents") or 0)
            record.new_chunks = int(result.get("new_chunks") or 0)
            record.skipped = int(result.get("skipped") or 0)
            failed_files = result.get("failed_files") or []
            record.failed_files = failed_files
            record.failed_count = len(failed_files)
            record.engagements = result.get("engagements") or []
        return self.repo.update(record)

    def get(self, import_id: str) -> KnowledgeImport | None:
        return self.repo.get_by_id(import_id)

    def get_by_job(self, job_id: str) -> KnowledgeImport | None:
        return self.repo.get_by_job_id(job_id)

    def list(self, *, limit: int, offset: int) -> list[KnowledgeImport]:
        return self.repo.list_recent(limit=limit, offset=offset)

    @staticmethod
    def serialize(record: KnowledgeImport) -> dict[str, Any]:
        return {
            "import_id": record.id,
            "job_id": record.job_id,
            "triggered_by": record.triggered_by,
            "batch_id": record.batch_id,
            "mode": record.mode,
            "status": record.status,
            "generation_id": record.generation_id,
            "new_documents": record.new_documents,
            "new_chunks": record.new_chunks,
            "skipped": record.skipped,
            "failed_count": record.failed_count,
            "failed_files": record.failed_files,
            "engagements": record.engagements,
            "error_message": record.error_message,
            "started_at": record.started_at,
            "finished_at": record.finished_at,
            "created_at": record.created_at,
        }
