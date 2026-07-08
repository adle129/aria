"""PostgreSQL pgvector storage for R1 knowledge chunks."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.database import engine
from app.models.knowledge_chunk import EMBEDDING_DIMENSION, KnowledgeChunk

try:
    from pgvector.sqlalchemy import Vector
except ImportError:  # pragma: no cover
    Vector = None  # type: ignore[misc, assignment]


class PgVectorUnavailableError(RuntimeError):
    pass


class PgVectorStore:
    def __init__(self, namespace: str = "default"):
        self.namespace = namespace

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

    def upsert_batch(
        self,
        *,
        chunk_ids: list[str],
        contents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
        namespace: str | None = None,
    ) -> int:
        self._require_pg()
        ns = namespace or self.namespace
        if not (len(chunk_ids) == len(contents) == len(embeddings) == len(metadatas)):
            raise ValueError("upsert_batch length mismatch")
        with Session(engine) as session:
            for cid, content, emb, meta in zip(chunk_ids, contents, embeddings, metadatas, strict=True):
                if len(emb) != EMBEDDING_DIMENSION:
                    raise ValueError(f"embedding dim {len(emb)} != {EMBEDDING_DIMENSION}")
                row = session.get(KnowledgeChunk, cid)
                if row is None:
                    row = KnowledgeChunk(chunk_id=cid, namespace=ns)
                    session.add(row)
                row.namespace = ns
                row.content = content
                row.embedding = emb
                row.chunk_metadata = meta
            session.commit()
        return len(chunk_ids)

    def count(self, namespace: str | None = None) -> int:
        self._require_pg()
        ns = namespace or self.namespace
        with Session(engine) as session:
            return session.scalar(
                select(func.count()).select_from(KnowledgeChunk).where(KnowledgeChunk.namespace == ns)
            ) or 0

    def list_source_docs(self, namespace: str | None = None) -> set[str]:
        self._require_pg()
        ns = namespace or self.namespace
        sql = text(
            """
            SELECT DISTINCT metadata->>'source_doc' AS source_doc
            FROM knowledge_chunks
            WHERE namespace = :ns AND metadata->>'source_doc' IS NOT NULL
            """
        )
        with Session(engine) as session:
            rows = session.execute(sql, {"ns": ns}).scalars().all()
        return {str(row) for row in rows if row}

    def get_by_id(self, chunk_id: str) -> dict[str, Any] | None:
        self._require_pg()
        with Session(engine) as session:
            row = session.get(KnowledgeChunk, chunk_id)
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
    ) -> list[dict[str, Any]]:
        self._require_pg()
        if len(query_embedding) != EMBEDDING_DIMENSION:
            raise ValueError(f"query embedding dim {len(query_embedding)} != {EMBEDDING_DIMENSION}")
        ns = namespace or self.namespace
        vec_literal = "[" + ",".join(str(float(x)) for x in query_embedding) + "]"
        sql = text(
            """
            SELECT chunk_id, content, metadata,
                   1 - (embedding <=> CAST(:qvec AS vector)) AS similarity
            FROM knowledge_chunks
            WHERE namespace = :ns AND embedding IS NOT NULL
            ORDER BY embedding <=> CAST(:qvec AS vector)
            LIMIT :limit
            """
        )
        with Session(engine) as session:
            rows = session.execute(sql, {"qvec": vec_literal, "ns": ns, "limit": top_k}).mappings().all()
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
