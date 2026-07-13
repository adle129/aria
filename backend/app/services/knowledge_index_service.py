"""R1 knowledge index: chunk flatten, Ollama embed, pgvector search."""

from __future__ import annotations

import json
import hashlib
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from collections.abc import Callable

from app.config import Settings
from app.repositories.knowledge_generation_repository import KnowledgeGenerationRepository
from app.services.embedding_service import EmbeddingError, embed_texts
from app.services.ingest.engagement_preview import build_engagement_preview
from app.services.pgvector_store import PgVectorStore, PgVectorUnavailableError
from app.services.rag_service import _filter_hits_by_doc_type, _filter_hits_by_functions
from app.utils.knowledge_paths import canonical_knowledge_source_doc

VALIDATION_NAMESPACE = "validation_corpus"
PRODUCTION_NAMESPACE = "production"
INDEX_STATE_FILE = "pgvector_index_state.json"
logger = logging.getLogger(__name__)


def _chunk_content(item: dict[str, Any]) -> str:
    """Body text; RFQ section_path is prepended for embedding (R1-K11)."""
    content = item.get("content") or item.get("preview") or ""
    meta = item.get("metadata") or {}
    if not str(content).strip():
        content = meta.get("question") or meta.get("chunk_chapter") or "empty"
    body = str(content).strip()
    section_path = (
        item.get("section_path")
        or meta.get("section_path")
        or ""
    ).strip()
    if section_path and not body.startswith(section_path):
        return f"{section_path}\n{body}"
    return body


def flatten_preview_chunks(report: dict[str, Any]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    rfq = report.get("rfq") or {}
    for item in rfq.get("chunks") or []:
        meta = dict(item.get("metadata") or {})
        meta.setdefault("doc_type", "rfq")
        meta.setdefault("chunk_id", item.get("chunk_id"))
        meta.setdefault("chunk_type", item.get("chunk_type"))
        meta.setdefault("chunk_chapter", item.get("chunk_chapter"))
        if item.get("section_path"):
            meta["section_path"] = item["section_path"]
        if item.get("section_depth") is not None:
            meta["section_depth"] = item["section_depth"]
        meta.setdefault("source_doc", rfq.get("path"))
        meta.setdefault("project_name", "validation_corpus")
        meta.setdefault(
            "locator",
            {"chapter": item.get("chunk_chapter"), "chunk_type": item.get("chunk_type")},
        )
        chunks.append(
            {
                "chunk_id": item["chunk_id"],
                "content": _chunk_content(item),
                "chunk_type": item.get("chunk_type"),
                "chunk_chapter": item.get("chunk_chapter"),
                "section_path": item.get("section_path") or meta.get("section_path"),
                "metadata": meta,
            }
        )

    qa = report.get("qa") or {}
    qa_path = qa.get("path")
    if qa_path:
        from app.services.ingest.qa_row_loader import load_qa_rows

        folder = Path(report.get("corpus_path", ""))
        qa_file = folder / qa_path
        if qa_file.exists():
            for item in load_qa_rows(qa_file):
                meta = dict(item.get("metadata") or {})
                meta.setdefault("chunk_id", item.get("chunk_id"))
                meta.setdefault("chunk_type", "qa_row")
                meta.setdefault("source_doc", qa_path)
                meta.setdefault("project_name", "validation_corpus")
                if meta.get("area"):
                    meta["functions"] = [meta["area"]]
                meta.setdefault(
                    "locator",
                    {"row": item.get("row_number"), "area": meta.get("area"), "sheet": "Sheet1"},
                )
                chunks.append(
                    {
                        "chunk_id": item["chunk_id"],
                        "content": _chunk_content(item),
                        "chunk_type": item.get("chunk_type"),
                        "chunk_chapter": meta.get("area") or f"row_{item.get('row_number')}",
                        "metadata": meta,
                    }
                )
    return chunks


def flatten_engagement_chunks(
    report: dict[str, Any],
    manifest: Any,
    kb_root: Path,
    folder: Path,
) -> list[dict[str, Any]]:
    """Production ingest chunks with engagement metadata (R1-K02)."""
    from app.schemas.engagement import EngagementManifest

    if not isinstance(manifest, EngagementManifest):
        manifest = EngagementManifest.model_validate(manifest)

    rel_folder = str(folder.relative_to(kb_root)).replace("\\", "/")
    engagement_id = manifest.engagement_id
    base_meta = {
        "engagement_id": engagement_id,
        "project_name": manifest.project_name,
        "customer": manifest.customer,
        "year": manifest.year,
        "functions": list(manifest.functions or []),
    }

    chunks: list[dict[str, Any]] = []
    rfq = report.get("rfq") or {}
    for item in rfq.get("chunks") or []:
        meta = dict(item.get("metadata") or {})
        meta.update(base_meta)
        meta.setdefault("doc_type", "rfq")
        meta.setdefault("chunk_id", item.get("chunk_id"))
        if item.get("section_path"):
            meta["section_path"] = item["section_path"]
        if item.get("section_depth") is not None:
            meta["section_depth"] = item["section_depth"]
        source = rfq.get("path") or "rfq.docx"
        # Always overwrite: preview/chunkers may set basename-only source_doc.
        meta["source_doc"] = canonical_knowledge_source_doc(rel_folder, source)
        cid = f"{engagement_id}::{item['chunk_id']}"
        chunks.append(
            {
                "chunk_id": cid,
                "content": _chunk_content(item),
                "chunk_type": item.get("chunk_type"),
                "chunk_chapter": item.get("chunk_chapter"),
                "section_path": item.get("section_path") or meta.get("section_path"),
                "metadata": meta,
            }
        )

    qa = report.get("qa") or {}
    qa_path = qa.get("path")
    if qa_path:
        from app.services.ingest.qa_row_loader import load_qa_rows

        qa_file = folder / qa_path
        if qa_file.exists():
            for item in load_qa_rows(qa_file):
                meta = dict(item.get("metadata") or {})
                meta.update(base_meta)
                meta.setdefault("doc_type", "qa")
                meta.setdefault("chunk_id", item.get("chunk_id"))
                meta["source_doc"] = canonical_knowledge_source_doc(rel_folder, qa_path)
                if meta.get("area"):
                    meta["functions"] = [meta["area"]]
                cid = f"{engagement_id}::{item['chunk_id']}"
                chunks.append(
                    {
                        "chunk_id": cid,
                        "content": _chunk_content(item),
                        "chunk_type": item.get("chunk_type"),
                        "chunk_chapter": meta.get("area") or f"row_{item.get('row_number')}",
                        "metadata": meta,
                    }
                )
    return chunks


class KnowledgeIndexService:
    """Index and search knowledge chunks via pgvector (R1)."""

    def __init__(self, settings: Settings, namespace: str = VALIDATION_NAMESPACE):
        self.settings = settings
        self.namespace = namespace
        self._store = PgVectorStore(namespace=namespace)
        self._generations = KnowledgeGenerationRepository()

    def _state_path(self) -> Path:
        # Store index state alongside the knowledge base, not under legacy chroma_path.
        return Path(self.settings.knowledge_base_path).parent / INDEX_STATE_FILE

    def _read_state(self) -> dict[str, Any]:
        path = self._state_path()
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_state(self, state: dict[str, Any]) -> None:
        path = self._state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    def ensure_ready(self) -> None:
        PgVectorStore.ensure_schema()

    def indexed_count(self) -> int:
        try:
            return self._store.count()
        except PgVectorUnavailableError:
            return 0

    def list_indexed_source_docs(self) -> set[str]:
        try:
            return self._store.list_source_docs()
        except PgVectorUnavailableError:
            return set()

    def list_indexed_source_docs_by_engagement(self) -> dict[str, set[str]]:
        try:
            return self._store.list_source_docs_by_engagement()
        except PgVectorUnavailableError:
            return {}

    def index_chunks(
        self,
        chunks: list[dict[str, Any]],
        *,
        clear: bool = True,
        corpus_path: str | None = None,
        source_file: str | None = None,
        created_by_job_id: str | None = None,
    ) -> dict[str, Any]:
        staged = self.build_generation(
            chunks,
            corpus_path=corpus_path,
            source_file=source_file,
            created_by_job_id=created_by_job_id,
        )
        return self.activate_generation(staged)

    def build_generation(
        self,
        chunks: list[dict[str, Any]],
        *,
        corpus_path: str | None = None,
        source_file: str | None = None,
        created_by_job_id: str | None = None,
        request_type: str = "kb_full",
    ) -> dict[str, Any]:
        if self.settings.mock_rag:
            raise EmbeddingError("MOCK_RAG=true：R1 索引需 MOCK_RAG=false + Ollama embedding")
        if not chunks:
            raise ValueError("No chunks to index")
        chunk_ids = [str(c["chunk_id"]) for c in chunks]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("Duplicate chunk_id in generation")

        self.ensure_ready()
        generation_id = str(uuid.uuid4())
        fingerprint_source = "\n".join(
            f"{c['chunk_id']}\0{c['content']}" for c in sorted(chunks, key=lambda row: row["chunk_id"])
        )
        fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()
        self._generations.create(
            generation_id=generation_id,
            namespace=self.namespace,
            embedding_model=self.settings.embedding_model,
            created_by_job_id=created_by_job_id,
            content_fingerprint=fingerprint,
        )

        try:
            texts = [c["content"] for c in chunks]
            embeddings = embed_texts(
                self.settings, texts, request_type=request_type
            )
            metadatas = []
            for c in chunks:
                meta = dict(c.get("metadata") or {})
                meta["chunk_id"] = c["chunk_id"]
                meta["chunk_type"] = c.get("chunk_type") or ""
                meta["chunk_chapter"] = c.get("chunk_chapter") or ""
                metadatas.append(meta)

            self._store.upsert_batch(
                chunk_ids=chunk_ids,
                contents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                generation_id=generation_id,
            )
            stored_count = self._store.count(generation_id=generation_id)
            if stored_count != len(chunks):
                raise ValueError(
                    f"generation chunk count mismatch: expected={len(chunks)} actual={stored_count}"
                )
            self._generations.mark_validated(generation_id, stored_count)
            return {
                "generation_id": generation_id,
                "corpus_path": corpus_path,
                "source_file": source_file,
                "chunk_count": stored_count,
                "namespace": self.namespace,
                "embedding_model": self.settings.embedding_model,
                "content_fingerprint": fingerprint,
            }
        except Exception as exc:
            self.fail_generation(generation_id, str(exc))
            raise

    def build_incremental_generation(
        self,
        changed_chunks: list[dict[str, Any]],
        *,
        carry_engagement_ids: list[str],
        carry_from_generation_id: str | None,
        corpus_path: str | None = None,
        created_by_job_id: str | None = None,
        request_type: str = "kb_incremental",
    ) -> dict[str, Any]:
        if self.settings.mock_rag:
            raise EmbeddingError("MOCK_RAG=true：R1 索引需 MOCK_RAG=false + Ollama embedding")
        if not changed_chunks and not carry_engagement_ids:
            raise ValueError("No chunks to index")
        self.ensure_ready()
        generation_id = str(uuid.uuid4())
        self._generations.create(
            generation_id=generation_id,
            namespace=self.namespace,
            embedding_model=self.settings.embedding_model,
            created_by_job_id=created_by_job_id,
            content_fingerprint="incremental",
        )
        try:
            if changed_chunks:
                texts = [c["content"] for c in changed_chunks]
                embeddings = embed_texts(
                    self.settings, texts, request_type=request_type
                )
                chunk_ids = [str(c["chunk_id"]) for c in changed_chunks]
                metadatas = []
                for c in changed_chunks:
                    meta = dict(c.get("metadata") or {})
                    meta["chunk_id"] = c["chunk_id"]
                    meta["chunk_type"] = c.get("chunk_type") or ""
                    meta["chunk_chapter"] = c.get("chunk_chapter") or ""
                    metadatas.append(meta)
                self._store.upsert_batch(
                    chunk_ids=chunk_ids,
                    contents=texts,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    generation_id=generation_id,
                )
            if carry_engagement_ids and carry_from_generation_id:
                self._store.copy_engagement_chunks(
                    from_generation_id=carry_from_generation_id,
                    to_generation_id=generation_id,
                    engagement_ids=carry_engagement_ids,
                )
            stored_count = self._store.count(generation_id=generation_id)
            if stored_count == 0:
                raise ValueError("incremental generation produced zero chunks")
            self._generations.mark_validated(generation_id, stored_count)
            return {
                "generation_id": generation_id,
                "corpus_path": corpus_path,
                "chunk_count": stored_count,
                "namespace": self.namespace,
                "embedding_model": self.settings.embedding_model,
                "content_fingerprint": "incremental",
            }
        except Exception as exc:
            self.fail_generation(generation_id, str(exc))
            raise

    def activate_generation(self, staged: dict[str, Any]) -> dict[str, Any]:
        generation_id = str(staged["generation_id"])
        previous = self._generations.activate(generation_id, self.namespace)
        now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        state = {
            **staged,
            "active_generation": generation_id,
            "previous_generation": previous,
            "last_index_at": now,
            "vector_store": "pgvector",
        }
        try:
            self._write_state(state)
        except OSError:
            logger.exception("Failed to write compatibility index state for %s", generation_id)
        try:
            self._cleanup_retired()
        except Exception:
            logger.exception("Failed to clean retired knowledge generations")
        return state

    def fail_generation(self, generation_id: str, error: str) -> None:
        self._generations.mark_failed(generation_id, error)
        try:
            self._store.delete_generation(generation_id)
        except PgVectorUnavailableError:
            pass

    def _cleanup_retired(self) -> None:
        for generation_id in self._generations.retired_for_cleanup(self.namespace):
            self._store.delete_generation(generation_id)
            self._generations.delete(generation_id)

    def index_corpus_folder(self, folder: Path, *, clear: bool = True) -> dict[str, Any]:
        report = build_engagement_preview(folder)
        chunks = flatten_preview_chunks(report)
        result = self.index_chunks(chunks, clear=clear, corpus_path=str(folder.resolve()))
        result["indexed_chunks"] = result.pop("chunk_count")
        return result

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        function_filter: list[str] | None = None,
        doc_type_filter: list[str] | None = None,
        request_type: str = "query",
        cancel_check: Callable[[], None] | None = None,
    ) -> list[dict[str, Any]]:
        if self.settings.mock_rag:
            raise EmbeddingError("MOCK_RAG=true：R1 检索需 MOCK_RAG=false")
        if self._store.count() == 0:
            return []

        query_vec = embed_texts(
            self.settings,
            [query],
            request_type=request_type,
            cancel_check=cancel_check,
        )[0]
        # Recall extra chunks; RAGService groups by engagement and applies top_k.
        recall_k = min(max(top_k * 10, 30), 100)
        hits = self._store.search_by_embedding(query_vec, top_k=recall_k)
        for hit in hits:
            meta = hit.get("metadata") or {}
            funcs = meta.get("functions")
            if isinstance(funcs, str) and funcs:
                meta["functions"] = [x.strip() for x in funcs.split(",") if x.strip()]
            hit["metadata"] = meta
            hit.setdefault("chunk_id", meta.get("chunk_id") or hit.get("chunk_id"))

        hits = _filter_hits_by_functions(hits, function_filter)
        hits = _filter_hits_by_doc_type(hits, doc_type_filter)
        return hits

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        try:
            return self._store.get_by_id(chunk_id)
        except PgVectorUnavailableError:
            return None

    def last_index_state(self) -> dict[str, Any]:
        active_id = self._generations.get_active_id(self.namespace)
        if active_id:
            active = self._generations.get(active_id)
            if active:
                return {
                    "active_generation": active.id,
                    "last_index_at": (
                        active.activated_at.isoformat().replace("+00:00", "Z")
                        if active.activated_at
                        else None
                    ),
                    "chunk_count": active.chunk_count,
                    "namespace": active.logical_namespace,
                    "embedding_model": active.embedding_model,
                    "vector_store": "pgvector",
                }
        return self._read_state()
