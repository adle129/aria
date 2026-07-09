"""DEV-only knowledge base debug: preview ingest, pgvector search, internal feedback."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.embedding_service import EmbeddingError
from app.services.ingest.engagement_preview import (
    build_engagement_preview,
    list_corpus_files,
    preview_corpus_file,
)
from app.services.kb_debug_cache import clear_preview, load_preview, save_preview
from app.services.knowledge_index_service import (
    VALIDATION_NAMESPACE,
    KnowledgeIndexService,
    flatten_preview_chunks,
)
from app.services.ollama_service import probe_ollama
from app.services.pgvector_store import PgVectorUnavailableError

INTERNAL_FEEDBACK_TYPES = frozenset(
    {"bad_boundary", "table_corrupt", "metadata_missing", "chunk_ok", "irrelevant", "wrong_snippet"}
)


def _quote_baseline_preview_rows(quote_baselines: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Map parsed quote Excel positions to browsable debug rows (not pgvector chunks)."""
    if not quote_baselines:
        return []
    detail = quote_baselines.get("detail") or {}
    source = str(quote_baselines.get("path") or detail.get("source_file") or "")
    rows: list[dict[str, Any]] = []
    for sheet_name, fn_data in (detail.get("functions") or {}).items():
        if not isinstance(fn_data, dict):
            continue
        for idx, pos in enumerate(fn_data.get("positions") or []):
            if not isinstance(pos, dict):
                continue
            position = str(pos.get("position") or "").strip()
            if not position:
                continue
            chunk_id = f"baseline:{source}:{sheet_name}:{idx}"
            tariff = pos.get("tariff_level") or ""
            total_sum = pos.get("sum")
            excel_row = pos.get("excel_row")
            row_ref = f"行 {excel_row}" if excel_row else "—"
            content = (
                f"Sheet: {sheet_name} · Excel {row_ref} · {position} | "
                f"Tariff Level: {tariff} | Sum: {total_sum}"
            )
            rows.append(
                {
                    "chunk_id": chunk_id,
                    "content": content,
                    "chunk_type": "baseline_row",
                    "chunk_chapter": sheet_name,
                    "char_count": len(content),
                    "preview": content[:400],
                    "metadata": {
                        "doc_type": "quote_manpower",
                        "source_doc": source,
                        "sheet": sheet_name,
                        "excel_row": excel_row,
                        "function": sheet_name,
                        "position": position,
                        "tariff_level": tariff,
                        "sum": total_sum,
                        "nonzero_month_cells": pos.get("nonzero_month_cells"),
                    },
                }
            )
    return rows


def _preview_rows_from_cache(cached: dict[str, Any]) -> list[dict[str, Any]]:
    vector_rows = flatten_preview_chunks(cached)
    if vector_rows:
        return vector_rows
    if cached.get("file_role") == "quote_manpower":
        return _quote_baseline_preview_rows(cached.get("quote_baselines"))
    return vector_rows

_SERVICE_SINGLETON: "KBDebugService | None" = None


def _default_corpus(settings: Settings) -> Path:
    return Path(settings.validation_corpus_path)


def _qa_areas_from_cache(cached: dict[str, Any] | None) -> list[str]:
    if not cached:
        return []
    qa = cached.get("qa") or {}
    preset = qa.get("areas")
    if isinstance(preset, list) and preset:
        return sorted({str(a).strip() for a in preset if str(a).strip()})
    areas: set[str] = set()
    for chunk in flatten_preview_chunks(cached):
        meta = chunk.get("metadata") or {}
        if meta.get("doc_type") == "qa":
            area = str(meta.get("area") or "").strip()
            if area:
                areas.add(area)
    return sorted(areas)


def get_kb_debug_service_singleton(settings: Settings) -> "KBDebugService":
    global _SERVICE_SINGLETON
    key = str(_default_corpus(settings).resolve())
    if _SERVICE_SINGLETON is None or str(_default_corpus(_SERVICE_SINGLETON.settings).resolve()) != key:
        _SERVICE_SINGLETON = KBDebugService(settings)
    return _SERVICE_SINGLETON


class KBDebugService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._index = KnowledgeIndexService(settings, namespace=VALIDATION_NAMESPACE)

    def _load_cache(self) -> dict[str, Any] | None:
        return load_preview(self.settings)

    def _store_cache(self, report: dict[str, Any]) -> dict[str, Any]:
        report["corpus_path"] = str(_default_corpus(self.settings).resolve())
        report["indexable_chunks"] = flatten_preview_chunks(report)
        save_preview(self.settings, report)
        return report

    def get_status(self) -> dict[str, Any]:
        probe = probe_ollama(
            self.settings.ollama_base_url,
            self.settings.ollama_model,
            self.settings.embedding_model,
        )
        state = self._index.last_index_state()
        corpus = _default_corpus(self.settings)
        pg_ok = self._index._store.is_available()
        cached = self._load_cache()
        return {
            "kb_debug_enabled": self.settings.kb_debug_enabled,
            "aria_ui_profile": self.settings.aria_ui_profile,
            "mock_rag": self.settings.mock_rag,
            "vector_store": "pgvector" if pg_ok else "unavailable",
            "pgvector_ready": pg_ok,
            "corpus_path": str(corpus),
            "corpus_exists": corpus.is_dir(),
            "indexed_chunks": self._index.indexed_count(),
            "last_index_at": state.get("last_index_at"),
            "last_corpus_path": state.get("corpus_path"),
            "last_indexed_file": state.get("source_file"),
            "preview_file": cached.get("target_file") if cached else None,
            "preview_chunk_count": len(cached.get("indexable_chunks") or []) if cached else 0,
            "embedding_model": self.settings.embedding_model,
            "ollama_reachable": probe["ollama_reachable"],
            "embedding_model_ready": probe["embedding_model_ready"],
            "ollama_error": probe["ollama_error"],
        }

    def list_corpus_files(self, corpus_path: Path | None = None) -> list[dict[str, Any]]:
        folder = corpus_path or _default_corpus(self.settings)
        if not folder.is_dir():
            raise FileNotFoundError(f"Corpus not found: {folder}")
        return list_corpus_files(folder)

    def preview_ingest(self, corpus_path: Path | None = None) -> dict[str, Any]:
        folder = corpus_path or _default_corpus(self.settings)
        if not folder.is_dir():
            raise FileNotFoundError(f"Corpus not found: {folder}")
        report = build_engagement_preview(folder)
        report["target_file"] = None
        report["file_role"] = "all"
        return self._store_cache(report)

    def preview_file(self, filename: str, corpus_path: Path | None = None) -> dict[str, Any]:
        folder = corpus_path or _default_corpus(self.settings)
        if not folder.is_dir():
            raise FileNotFoundError(f"Corpus not found: {folder}")
        report = preview_corpus_file(folder, filename)
        return self._store_cache(report)

    def list_chunks(
        self,
        *,
        doc_type: str | None = None,
        source_file: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        cached = self._load_cache()
        if cached is None:
            return {
                "total": 0,
                "items": [],
                "source": "empty",
                "hint": "Select a file and run preview first",
                "target_file": None,
                "qa_areas": [],
            }

        all_chunks = _preview_rows_from_cache(cached)
        file_role = cached.get("file_role")
        if source_file:
            all_chunks = [
                c
                for c in all_chunks
                if str((c.get("metadata") or {}).get("source_doc", "")) == source_file
            ]
        if doc_type:
            all_chunks = [c for c in all_chunks if (c.get("metadata") or {}).get("doc_type") == doc_type]
        page = all_chunks[offset : offset + limit]
        items = [
            {
                "chunk_id": c["chunk_id"],
                "chunk_type": c.get("chunk_type"),
                "chunk_chapter": c.get("chunk_chapter"),
                "char_count": len(c.get("content") or ""),
                "preview": (c.get("content") or "")[:400],
                "metadata": c.get("metadata") or {},
            }
            for c in page
        ]
        return {
            "total": len(all_chunks),
            "items": items,
            "source": "preview",
            "target_file": cached.get("target_file"),
            "file_role": cached.get("file_role"),
            "browse_mode": "baseline_rows" if file_role == "quote_manpower" and all_chunks else "vector_chunks",
            "quote_baselines": cached.get("quote_baselines"),
            "archive_only": cached.get("archive_only") or [],
            "qa_areas": _qa_areas_from_cache(cached),
        }

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        cached = self._load_cache()
        if cached:
            for c in _preview_rows_from_cache(cached):
                if c["chunk_id"] == chunk_id:
                    return {
                        "chunk_id": c["chunk_id"],
                        "content": c.get("content"),
                        "chunk_type": c.get("chunk_type"),
                        "chunk_chapter": c.get("chunk_chapter"),
                        "metadata": c.get("metadata") or {},
                    }
        return self._index.get_chunk(chunk_id)

    def index_corpus(self, corpus_path: Path | None = None, *, clear: bool = True) -> dict[str, Any]:
        folder = corpus_path or _default_corpus(self.settings)
        try:
            return self._index_corpus_folder(folder, clear=clear)
        except PgVectorUnavailableError as exc:
            raise EmbeddingError(str(exc)) from exc

    def index_file(self, filename: str, corpus_path: Path | None = None, *, clear: bool = True) -> dict[str, Any]:
        cached = self._load_cache()
        if not cached or cached.get("target_file") != filename:
            self.preview_file(filename, corpus_path)
            cached = self._load_cache()
        if cached is None:
            raise FileNotFoundError(f"Preview missing for: {filename}")

        chunks = flatten_preview_chunks(cached)
        if not chunks:
            role = cached.get("file_role") or "unknown"
            raise ValueError(
                f"No indexable chunks for {filename} (role={role}). "
                "Quote/PPT/PDF are metadata-only in R1 debug."
            )
        try:
            state = self._index.index_chunks(
                chunks,
                clear=clear,
                corpus_path=str(_default_corpus(self.settings).resolve()),
                source_file=filename,
            )
        except PgVectorUnavailableError as exc:
            raise EmbeddingError(str(exc)) from exc
        state["indexed_chunks"] = state.pop("chunk_count")
        return state

    def _index_corpus_folder(self, folder: Path, *, clear: bool = True) -> dict[str, Any]:
        return self._index.index_corpus_folder(folder, clear=clear)

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        function_filter: list[str] | None = None,
        doc_type_filter: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        try:
            return self._index.search(
                query,
                top_k=top_k,
                function_filter=function_filter,
                doc_type_filter=doc_type_filter,
            )
        except PgVectorUnavailableError as exc:
            raise EmbeddingError(str(exc)) from exc

    def submit_feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        feedback_type = payload.get("feedback_type")
        if feedback_type not in INTERNAL_FEEDBACK_TYPES:
            raise ValueError(f"Invalid feedback_type: {feedback_type}")

        record = {
            "id": str(uuid.uuid4()),
            "audience": "internal",
            "source_context": payload.get("source_context") or "chunk_inspector",
            "feedback_type": feedback_type,
            "query": payload.get("query"),
            "chunk_id": payload.get("chunk_id"),
            "comment": (payload.get("comment") or "")[:1000],
            "snapshot": payload.get("snapshot") or {},
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        }
        path = Path(self.settings.feedback_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def run_eval(self, queries: list[dict[str, Any]], *, top_k: int = 3) -> dict[str, Any]:
        from app.services.retrieval_eval_service import evaluate_retrieval_queries

        def search(q: str, doc_types: list[str] | None) -> list[dict[str, Any]]:
            return self.search(q, top_k=top_k, doc_type_filter=doc_types)

        return evaluate_retrieval_queries(search, queries, top_k=top_k)
