"""PostgreSQL pgvector storage for R1 knowledge chunks."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.database import engine
from app.models.knowledge_chunk import EMBEDDING_DIMENSION, KnowledgeChunk
from app.models.knowledge_index_generation import KnowledgeIndexGeneration, KnowledgeIndexState
from app.repositories.knowledge_generation_repository import KnowledgeGenerationRepository

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover
    Vector = None  # type: ignore[misc, assignment]

try:
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    _HAS_PG_INSERT = True
except ImportError:  # pragma: no cover
    _HAS_PG_INSERT = False

_UPSERT_BATCH_SIZE = 200


class PgVectorUnavailableError(RuntimeError):
    pass


class PgVectorStore:
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace
        self.generations = KnowledgeGenerationRepository()

    @staticmethod
    def is_available() -> bool:
        return engine.dialect.name == "postgresql"

    @staticmethod
    def ensure_schema() -> None:
        if not PgVectorStore.is_available():
            return
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        from app.database import Base
        from app.models import knowledge_chunk  # noqa: F401

        KnowledgeIndexGeneration.__table__.create(bind=engine, checkfirst=True)
        KnowledgeIndexState.__table__.create(bind=engine, checkfirst=True)
        KnowledgeChunk.__table__.create(bind=engine, checkfirst=True)
        PgVectorStore._ensure_embedding_column()

    @staticmethod
    def _ensure_embedding_column() -> None:
        """Add embedding column when table was created before pgvector package was installed."""
        if Vector is None:
            return
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"""
                    DO $$ BEGIN
                        ALTER TABLE knowledge_chunks
                            ADD COLUMN embedding vector({EMBEDDING_DIMENSION});
                    EXCEPTION
                        WHEN duplicate_column THEN NULL;
                    END $$;
                    """
                )
            )
        PgVectorStore._ensure_hnsw_index()

    @staticmethod
    def _ensure_hnsw_index() -> None:
        """Create HNSW approximate-nearest-neighbor index for cosine search (pgvector ≥0.5)."""
        if Vector is None:
            return
        try:
            # HNSW index creation cannot run inside a transaction block.
            with engine.connect() as conn:
                conn = conn.execution_options(isolation_level="AUTOCOMMIT")
                conn.execute(
                    text(
                        """
                        CREATE INDEX IF NOT EXISTS idx_kc_embedding_cosine
                        ON knowledge_chunks
                        USING hnsw (embedding vector_cosine_ops)
                        WITH (m = 16, ef_construction = 64)
                        """
                    )
                )
        except Exception:  # noqa: BLE001 — older pgvector / unsupported backend
            pass

    def _require_pg(self) -> None:
        if not self.is_available():
            raise PgVectorUnavailableError(
                "pgvector 需要 PostgreSQL（R1）。请使用 docker compose 启动 postgres，"
                "或设置 DATABASE_URL=postgresql://..."
            )
        if Vector is None or "embedding" not in KnowledgeChunk.__table__.columns:
            raise PgVectorUnavailableError(
                "Python 包 pgvector 未安装或 knowledge_chunks 缺少 embedding 列。"
                "请确认 requirements-ai.txt 含 pgvector==0.3.6 并重建 backend 镜像，然后重新索引。"
            )

    def clear_namespace(self, namespace: str | None = None) -> int:
        self._require_pg()
        ns = namespace or self.namespace
        with Session(engine) as session:
            result = session.execute(delete(KnowledgeChunk).where(KnowledgeChunk.namespace == ns))
            session.commit()
            return result.rowcount or 0

    def delete_generation(self, generation_id: str) -> int:
        self._require_pg()
        with Session(engine) as session:
            result = session.execute(
                delete(KnowledgeChunk).where(KnowledgeChunk.generation_id == generation_id)
            )
            session.commit()
            return result.rowcount or 0

    def upsert_batch(
        self,
        *,
        chunk_ids: list[str],
        contents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        namespace: str | None = None,
        generation_id: str,
    ) -> int:
        self._require_pg()
        ns = namespace or self.namespace
        if not (len(chunk_ids) == len(contents) == len(embeddings) == len(metadatas)):
            raise ValueError("upsert_batch length mismatch")

        for emb in embeddings:
            if len(emb) != EMBEDDING_DIMENSION:
                raise ValueError(f"embedding dim {len(emb)} != {EMBEDDING_DIMENSION}")

        if _HAS_PG_INSERT:
            # Bulk INSERT ... ON CONFLICT: O(1) round-trips instead of O(N).
            with Session(engine) as session:
                for start in range(0, len(chunk_ids), _UPSERT_BATCH_SIZE):
                    sl = slice(start, start + _UPSERT_BATCH_SIZE)
                    rows = [
                        {
                            "chunk_id": cid,
                            "generation_id": generation_id,
                            "namespace": ns,
                            "content": content,
                            "embedding": emb,
                            "metadata": meta,
                        }
                        for cid, content, emb, meta in zip(
                            chunk_ids[sl], contents[sl], embeddings[sl], metadatas[sl]
                        )
                    ]
                    stmt = pg_insert(KnowledgeChunk.__table__).values(rows)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["generation_id", "chunk_id"],
                        set_={
                            "namespace": stmt.excluded.namespace,
                            "content": stmt.excluded.content,
                            "embedding": stmt.excluded.embedding,
                            "metadata": stmt.excluded.metadata,
                        },
                    )
                    session.execute(stmt)
                session.commit()
        else:
            # Fallback for non-PostgreSQL backends (unit tests with SQLite).
            with Session(engine) as session:
                for cid, content, emb, meta in zip(
                    chunk_ids, contents, embeddings, metadatas, strict=True
                ):
                    row = session.get(KnowledgeChunk, (generation_id, cid))
                    if row is None:
                        row = KnowledgeChunk(
                            generation_id=generation_id,
                            chunk_id=cid,
                            namespace=ns,
                        )
                        session.add(row)
                    row.namespace = ns
                    row.content = content
                    row.embedding = emb
                    row.chunk_metadata = meta
                session.commit()

        return len(chunk_ids)

    def copy_engagement_chunks(
        self,
        *,
        from_generation_id: str,
        to_generation_id: str,
        engagement_ids: list[str],
        namespace: str | None = None,
    ) -> int:
        self._require_pg()
        if not engagement_ids:
            return 0
        ns = namespace or self.namespace
        with Session(engine) as session:
            rows = session.scalars(
                select(KnowledgeChunk).where(
                    KnowledgeChunk.namespace == ns,
                    KnowledgeChunk.generation_id == from_generation_id,
                )
            ).all()
            copied = 0
            for row in rows:
                meta = dict(row.chunk_metadata or {})
                if meta.get("engagement_id") not in engagement_ids:
                    continue
                existing = session.get(
                    KnowledgeChunk, (to_generation_id, row.chunk_id)
                )
                if existing is None:
                    existing = KnowledgeChunk(
                        generation_id=to_generation_id,
                        chunk_id=row.chunk_id,
                        namespace=ns,
                    )
                    session.add(existing)
                existing.namespace = ns
                existing.content = row.content
                existing.embedding = row.embedding
                existing.chunk_metadata = meta
                copied += 1
            session.commit()
            return copied

    def count(
        self,
        namespace: str | None = None,
        *,
        generation_id: str | None = None,
    ) -> int:
        self._require_pg()
        ns = namespace or self.namespace
        generation_id = generation_id or self.generations.get_active_id(ns)
        if generation_id is None:
            return 0
        with Session(engine) as session:
            return session.scalar(
                select(func.count())
                .select_from(KnowledgeChunk)
                .where(
                    KnowledgeChunk.namespace == ns,
                    KnowledgeChunk.generation_id == generation_id,
                )
            ) or 0

    def list_source_docs(
        self,
        namespace: str | None = None,
        *,
        generation_id: str | None = None,
    ) -> set[str]:
        self._require_pg()
        ns = namespace or self.namespace
        generation_id = generation_id or self.generations.get_active_id(ns)
        if generation_id is None:
            return set()
        sql = text(
            """
            SELECT DISTINCT metadata->>'source_doc' AS source_doc
            FROM knowledge_chunks
            WHERE namespace = :ns
              AND generation_id = :generation_id
              AND metadata->>'source_doc' IS NOT NULL
            """
        )
        with Session(engine) as session:
            rows = session.execute(
                sql,
                {"ns": ns, "generation_id": generation_id},
            ).scalars().all()
        return {str(row) for row in rows if row}

    def get_by_id(self, chunk_id: str) -> dict[str, Any] | None:
        self._require_pg()
        generation_id = self.generations.get_active_id(self.namespace)
        if generation_id is None:
            return None
        with Session(engine) as session:
            row = session.get(KnowledgeChunk, (generation_id, chunk_id))
            if row is None:
                return None
            meta = dict(row.chunk_metadata or {})
            return {
                "chunk_id": row.chunk_id,
                "content": row.content,
                "chunk_type": meta.get("chunk_type"),
                "chunk_chapter": meta.get("chunk_chapter"),
                "metadata": meta,
            }

    def search_by_embedding(
        self,
        query_embedding: list[float],
        *,
        top_k: int = 5,
        namespace: str | None = None,
        generation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        self._require_pg()
        if len(query_embedding) != EMBEDDING_DIMENSION:
            raise ValueError(f"query embedding dim {len(query_embedding)} != {EMBEDDING_DIMENSION}")
        ns = namespace or self.namespace
        generation_id = generation_id or self.generations.get_active_id(ns)
        if generation_id is None:
            return []
        vec_literal = "[" + ",".join(str(float(x)) for x in query_embedding) + "]"
        sql = text(
            """
            SELECT chunk_id, content, metadata,
                   1 - (embedding <=> CAST(:qvec AS vector)) AS similarity
            FROM knowledge_chunks
            WHERE namespace = :ns
              AND generation_id = :generation_id
              AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:qvec AS vector)
            LIMIT :limit
            """
        )
        with Session(engine) as session:
            rows = session.execute(
                sql,
                {
                    "qvec": vec_literal,
                    "ns": ns,
                    "generation_id": generation_id,
                    "limit": top_k,
                },
            ).mappings().all()
        hits: list[dict[str, Any]] = []
        for row in rows:
            meta = row["metadata"]
            if isinstance(meta, str):
                meta = json.loads(meta)
            meta = dict(meta or {})
            hits.append(
                {
                    "chunk_id": row["chunk_id"],
                    "content": row["content"],
                    "metadata": meta,
                    "similarity_score": round(float(row["similarity"] or 0.0), 3),
                }
            )
        return hits
