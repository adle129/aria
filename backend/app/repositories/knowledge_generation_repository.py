from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.database import engine
from app.models.knowledge_index_generation import KnowledgeIndexGeneration, KnowledgeIndexState


class KnowledgeGenerationRepository:
    def __init__(self, bind: Engine | None = None):
        self.bind = bind or engine

    def create(
        self,
        *,
        generation_id: str,
        namespace: str,
        embedding_model: str,
        created_by_job_id: str | None,
        content_fingerprint: str,
    ) -> KnowledgeIndexGeneration:
        row = KnowledgeIndexGeneration(
            id=generation_id,
            logical_namespace=namespace,
            status="building",
            created_by_job_id=created_by_job_id,
            schema_version="v1",
            embedding_model=embedding_model,
            content_fingerprint=content_fingerprint,
        )
        with Session(self.bind) as session:
            session.add(row)
            session.commit()
            session.refresh(row)
            session.expunge(row)
        return row

    def get_active_id(self, namespace: str) -> str | None:
        try:
            with Session(self.bind) as session:
                state = session.get(KnowledgeIndexState, namespace)
                return state.active_generation_id if state else None
        except OperationalError:
            if self.bind.dialect.name == "sqlite":
                return None
            raise

    def get(self, generation_id: str) -> KnowledgeIndexGeneration | None:
        try:
            with Session(self.bind) as session:
                row = session.get(KnowledgeIndexGeneration, generation_id)
                if row:
                    session.expunge(row)
                return row
        except OperationalError:
            if self.bind.dialect.name == "sqlite":
                return None
            raise

    def mark_validated(self, generation_id: str, chunk_count: int) -> None:
        with Session(self.bind) as session:
            row = session.get(KnowledgeIndexGeneration, generation_id)
            if row is None:
                raise ValueError(f"generation not found: {generation_id}")
            row.status = "validating"
            row.chunk_count = chunk_count
            row.validated_at = datetime.now(UTC)
            session.commit()

    def mark_failed(self, generation_id: str, error: str) -> None:
        with Session(self.bind) as session:
            row = session.get(KnowledgeIndexGeneration, generation_id)
            if row is None:
                return
            row.status = "failed"
            row.error_summary = error[:2000]
            session.commit()

    def activate(self, generation_id: str, namespace: str) -> str | None:
        now = datetime.now(UTC)
        with Session(self.bind) as session, session.begin():
            generation = session.get(KnowledgeIndexGeneration, generation_id)
            if generation is None or generation.logical_namespace != namespace:
                raise ValueError(f"invalid generation: {generation_id}")
            if generation.status != "validating":
                raise ValueError(
                    f"generation {generation_id} must be validating, got {generation.status}"
                )
            state = session.scalar(
                select(KnowledgeIndexState)
                .where(KnowledgeIndexState.logical_namespace == namespace)
                .with_for_update()
            )
            if state is None:
                state = KnowledgeIndexState(
                    logical_namespace=namespace,
                    active_generation_id=None,
                    previous_generation_id=None,
                    version=0,
                )
                session.add(state)
            old_id = state.active_generation_id
            if old_id:
                old = session.get(KnowledgeIndexGeneration, old_id)
                if old:
                    old.status = "retired"
            generation.status = "active"
            generation.activated_at = now
            state.previous_generation_id = old_id
            state.active_generation_id = generation_id
            state.version = (state.version or 0) + 1
            state.updated_at = now
        return old_id

    def protected_generation_ids(self, namespace: str) -> set[str]:
        with Session(self.bind) as session:
            state = session.get(KnowledgeIndexState, namespace)
            if state is None:
                return set()
            return {
                value
                for value in (state.active_generation_id, state.previous_generation_id)
                if value
            }

    def retired_for_cleanup(self, namespace: str) -> list[str]:
        protected = self.protected_generation_ids(namespace)
        with Session(self.bind) as session:
            rows = session.scalars(
                select(KnowledgeIndexGeneration.id).where(
                    KnowledgeIndexGeneration.logical_namespace == namespace,
                    KnowledgeIndexGeneration.status.in_(("retired", "failed")),
                )
            )
            return [row for row in rows if row not in protected]

    def delete(self, generation_id: str) -> None:
        with Session(self.bind) as session:
            row = session.get(KnowledgeIndexGeneration, generation_id)
            if row:
                session.delete(row)
                session.commit()
