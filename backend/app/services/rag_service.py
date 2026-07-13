import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.comparison_service import (
    build_comparison_matrix,
    build_matrix_from_dimension_draft,
)
from app.services.mock_data import (
    MOCK_COMPARISON_TABLE,
    MOCK_KNOWLEDGE_DOCUMENTS,
    MOCK_KNOWLEDGE_STATS,
    MOCK_RAG_HITS,
)

logger = logging.getLogger(__name__)


class RAGProductionError(RuntimeError):
    """Raised when a Demo-only RAG path is invoked in production (MOCK_RAG=false)."""


def calculate_overall_confidence(similarity_scores: list[float]) -> str:
    if not similarity_scores:
        return "低"
    max_score = max(similarity_scores)
    count = len(similarity_scores)
    if count >= 3 and max_score >= 0.85:
        return "高"
    if count >= 1 and max_score >= 0.70:
        return "中"
    return "低"


def compute_function_coverage(
    functions_in_scope: list[str] | None,
    similar_docs: list[dict[str, Any]],
) -> dict[str, list[str]]:
    covered: set[str] = set()
    for hit in similar_docs:
        meta = hit.get("metadata") or {}
        for fn in meta.get("functions") or []:
            covered.add(str(fn))
    in_scope = [str(f) for f in (functions_in_scope or [])]
    uncovered = [f for f in in_scope if f not in covered]
    return {
        "in_scope": in_scope,
        "covered": sorted(covered),
        "uncovered": uncovered,
    }


def infer_doc_type(filename: str) -> str:
    name = filename.lower()
    if "rfq" in name:
        return "rfq"
    if "qa" in name or "q_a" in name:
        return "qa"
    if "quote" in name:
        return "quote_manpower"
    if "proposal" in name or "sow" in name:
        return "summary"
    return "summary"


def _filter_hits_by_functions(
    hits: list[dict[str, Any]], function_filter: list[str] | None
) -> list[dict[str, Any]]:
    if not function_filter:
        return hits
    wanted = set(function_filter)
    filtered: list[dict[str, Any]] = []
    for hit in hits:
        meta = hit.get("metadata") or {}
        hit_functions = set(meta.get("functions") or [])
        if wanted & hit_functions:
            filtered.append(hit)
    return filtered


def _filter_hits_by_doc_type(
    hits: list[dict[str, Any]], doc_type_filter: list[str] | None
) -> list[dict[str, Any]]:
    if not doc_type_filter:
        return hits
    wanted = set(doc_type_filter)
    filtered: list[dict[str, Any]] = []
    for hit in hits:
        meta = hit.get("metadata") or {}
        doc_type = meta.get("doc_type")
        if doc_type in wanted:
            filtered.append(hit)
    return filtered


def _engagement_group_key(hit: dict[str, Any]) -> str:
    meta = hit.get("metadata") or {}
    eid = meta.get("engagement_id")
    if eid:
        return f"eng:{eid}"
    source = meta.get("source_doc") or ""
    if source:
        return f"src:{source}"
    name = meta.get("project_name") or "unknown"
    return f"name:{name}"


def _group_similarity_score(
    group_hits: list[dict[str, Any]],
    *,
    score_mode: str = "max",
    score_top_m: int = 3,
) -> float:
    scores = sorted(
        (float(h.get("similarity_score") or 0.0) for h in group_hits),
        reverse=True,
    )
    if not scores:
        return 0.0
    if score_mode == "mean_top_m":
        use = scores[: max(1, score_top_m)]
        return sum(use) / len(use)
    return scores[0]


def group_hits_by_engagement(
    hits: list[dict[str, Any]],
    *,
    top_k: int,
    citations_per_group: int = 3,
    score_mode: str = "max",
    score_top_m: int = 3,
) -> list[dict[str, Any]]:
    """Aggregate chunk hits into engagement groups (R1-K11).

    score_mode:
      - max: project score = best chunk (knowledge search / default)
      - mean_top_m: mean of top-m chunk scores (RFQ similar-project ranking)
    """
    buckets: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for hit in hits:
        key = _engagement_group_key(hit)
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(hit)

    groups: list[dict[str, Any]] = []
    for key in order:
        group_hits = sorted(
            buckets[key],
            key=lambda h: float(h.get("similarity_score") or 0.0),
            reverse=True,
        )
        citations = group_hits[:citations_per_group]
        best = citations[0]
        meta = best.get("metadata") or {}
        groups.append(
            {
                "engagement_id": meta.get("engagement_id"),
                "project_name": meta.get("project_name") or "未知项目",
                "similarity_score": round(
                    _group_similarity_score(
                        group_hits,
                        score_mode=score_mode,
                        score_top_m=score_top_m,
                    ),
                    3,
                ),
                "source_doc": meta.get("source_doc"),
                "metadata": {
                    "project_name": meta.get("project_name"),
                    "source_doc": meta.get("source_doc"),
                    "doc_type": meta.get("doc_type"),
                    "functions": list(meta.get("functions") or []),
                    "year": meta.get("year"),
                    "customer": meta.get("customer"),
                    "engagement_id": meta.get("engagement_id"),
                },
                "hits": citations,
            }
        )

    groups.sort(key=lambda g: float(g.get("similarity_score") or 0.0), reverse=True)
    return groups[:top_k]


def flatten_group_hits(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for group in groups:
        flat.extend(group.get("hits") or [])
    return flat


class RAGService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.knowledge_base_path = settings.knowledge_base_path

    def _index_service(self):
        from app.services.knowledge_index_service import KnowledgeIndexService

        return KnowledgeIndexService(
            self.settings,
            namespace=self.settings.knowledge_vector_namespace,
        )

    def is_insufficient_evidence(self, hits: list[dict[str, Any]]) -> bool:
        if self.settings.mock_rag:
            return False
        if not hits:
            return True
        max_score = max(float(h.get("similarity_score") or 0.0) for h in hits)
        return max_score < float(self.settings.rag_similarity_threshold)

    def search_similar_projects(
        self,
        query: str,
        top_k: int = 5,
        function_filter: list[str] | None = None,
        doc_type_filter: list[str] | None = None,
        *,
        request_type: str = "query",
        cancel_check: Callable[[], None] | None = None,
        rfq_modules: dict[str, Any] | None = None,
        draft: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Return one representative hit per engagement for RFQ Top-N.

        Project rank uses mean of top-3 chunk scores, then optional structured
        fusion (functions / scope titles / name) when rfq_modules is provided.
        Defaults to RFQ chunks only; pass doc_type_filter to override.
        """
        from app.services.rfq_structured_similarity import rerank_similar_groups

        recall_projects = max(top_k * 3, 10) if rfq_modules is not None else top_k
        groups = self.search_grouped(
            query,
            top_k=recall_projects,
            function_filter=function_filter,
            doc_type_filter=["rfq"] if doc_type_filter is None else doc_type_filter,
            request_type=request_type,
            cancel_check=cancel_check,
            citations_per_group=5,
            score_mode="mean_top_m",
            score_top_m=3,
        )
        if rfq_modules is not None:
            groups = rerank_similar_groups(
                groups,
                rfq_modules,
                draft=draft,
                top_k=top_k,
            )
        else:
            groups = groups[:top_k]

        results: list[dict[str, Any]] = []
        for group in groups:
            hits = group.get("hits") or []
            if not hits:
                continue
            hit = dict(hits[0])
            hit["similarity_score"] = group.get("similarity_score")
            meta = dict(hit.get("metadata") or {})
            if group.get("vector_score") is not None:
                meta["vector_score"] = group.get("vector_score")
            if group.get("structured_score") is not None:
                meta["structured_score"] = group.get("structured_score")
            hit["metadata"] = meta
            results.append(hit)
        return results

    def search_grouped(
        self,
        query: str,
        top_k: int = 5,
        function_filter: list[str] | None = None,
        doc_type_filter: list[str] | None = None,
        *,
        request_type: str = "query",
        cancel_check: Callable[[], None] | None = None,
        citations_per_group: int = 3,
        score_mode: str = "max",
        score_top_m: int = 3,
    ) -> list[dict[str, Any]]:
        """Search and aggregate by engagement; top_k = number of projects."""
        started = time.monotonic()
        if self.settings.mock_rag:
            hits = _filter_hits_by_functions(MOCK_RAG_HITS, function_filter)
            hits = _filter_hits_by_doc_type(hits, doc_type_filter)
            return group_hits_by_engagement(
                hits,
                top_k=top_k,
                citations_per_group=citations_per_group,
                score_mode=score_mode,
                score_top_m=score_top_m,
            )

        index = self._index_service()
        hits = index.search(
            query,
            top_k=top_k,
            function_filter=function_filter,
            doc_type_filter=doc_type_filter,
            request_type=request_type,
            cancel_check=cancel_check,
        )
        groups = group_hits_by_engagement(
            hits,
            top_k=top_k,
            citations_per_group=citations_per_group,
            score_mode=score_mode,
            score_top_m=score_top_m,
        )
        max_score = max(
            (float(g.get("similarity_score") or 0.0) for g in groups),
            default=0.0,
        )
        flat = flatten_group_hits(groups)
        logger.info(
            "rag_search request_type=%s top_k=%s groups=%d hits=%d max_similarity=%.3f "
            "insufficient=%s elapsed_ms=%d",
            request_type,
            top_k,
            len(groups),
            len(flat),
            max_score,
            self.is_insufficient_evidence(flat),
            int((time.monotonic() - started) * 1000),
        )
        return groups

    def build_comparison_table(
        self, rfq_data: dict[str, Any], similar_docs: list[dict[str, Any]]
    ) -> dict[str, Any]:
        scores = [doc.get("similarity_score", 0.0) for doc in similar_docs]
        confidence = calculate_overall_confidence(scores)
        insufficient = self.is_insufficient_evidence(similar_docs)

        if self.settings.mock_rag:
            table = dict(MOCK_COMPARISON_TABLE)
            table["overall_confidence"] = confidence
            table["insufficient_evidence"] = False
            hit_engagement = {
                (h.get("metadata") or {}).get("project_name"): (h.get("metadata") or {}).get(
                    "engagement_id"
                )
                for h in similar_docs
            }
            enriched_projects: list[dict[str, Any]] = []
            for project in MOCK_COMPARISON_TABLE["projects"]:
                proj = dict(project)
                eid = hit_engagement.get(project["project_name"]) or project.get("engagement_id")
                if eid:
                    proj["engagement_id"] = eid
                enriched_projects.append(proj)
            table["projects"] = enriched_projects
        elif insufficient:
            table = {
                "comparison_dimensions": MOCK_COMPARISON_TABLE["comparison_dimensions"],
                "projects": [],
                "recommendation": "暂无足够历史项目依据，请补充知识库或人工核对",
                "overall_confidence": "低",
                "insufficient_evidence": True,
            }
        else:
            table = {
                "comparison_dimensions": MOCK_COMPARISON_TABLE["comparison_dimensions"],
                "projects": self._projects_from_hits(similar_docs),
                "recommendation": self._build_recommendation(similar_docs),
                "overall_confidence": confidence,
                "insufficient_evidence": False,
            }

        matrix = build_comparison_matrix(
            rfq_data,
            table["projects"],
            dimensions=table.get("comparison_dimensions"),
        )
        table.update(matrix)
        table["function_coverage"] = compute_function_coverage(
            rfq_data.get("functions_in_scope"),
            similar_docs,
        )
        return table

    def build_comparison_table_from_draft(
        self,
        rfq_data: dict[str, Any],
        similar_docs: list[dict[str, Any]],
        dimension_draft: dict[str, Any],
    ) -> dict[str, Any]:
        items = list(dimension_draft.get("items") or [])
        custom = list(dimension_draft.get("custom_items") or [])
        in_scope_items = [i for i in items + custom if i.get("in_scope") is True]
        if not in_scope_items:
            raise ValueError("至少选择一项 in_scope 维度")

        scores = [doc.get("similarity_score", 0.0) for doc in similar_docs]
        confidence = calculate_overall_confidence(scores)
        insufficient = self.is_insufficient_evidence(similar_docs)
        comparison_dimensions = [str(i.get("name", "")) for i in in_scope_items if i.get("name")]

        if self.settings.mock_rag:
            table = dict(MOCK_COMPARISON_TABLE)
            table["comparison_dimensions"] = comparison_dimensions
            table["overall_confidence"] = confidence
            table["insufficient_evidence"] = False
            hit_engagement = {
                (h.get("metadata") or {}).get("project_name"): (h.get("metadata") or {}).get(
                    "engagement_id"
                )
                for h in similar_docs
            }
            enriched_projects: list[dict[str, Any]] = []
            for project in MOCK_COMPARISON_TABLE["projects"]:
                proj = dict(project)
                eid = hit_engagement.get(project["project_name"]) or project.get("engagement_id")
                if eid:
                    proj["engagement_id"] = eid
                enriched_projects.append(proj)
            table["projects"] = enriched_projects[:3]
        elif insufficient:
            table = {
                "comparison_dimensions": comparison_dimensions,
                "projects": [],
                "recommendation": "暂无足够历史项目依据，请补充知识库或人工核对",
                "overall_confidence": "低",
                "insufficient_evidence": True,
            }
        else:
            table = {
                "comparison_dimensions": comparison_dimensions,
                "projects": self._projects_from_hits(similar_docs[:3]),
                "recommendation": self._build_recommendation(similar_docs),
                "overall_confidence": confidence,
                "insufficient_evidence": False,
            }

        matrix = build_matrix_from_dimension_draft(in_scope_items, table["projects"])
        table.update(matrix)
        table["function_coverage"] = compute_function_coverage(
            rfq_data.get("functions_in_scope"),
            similar_docs,
        )
        return table

    def _projects_from_hits(self, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        projects: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        for hit in hits:
            meta = hit.get("metadata") or {}
            name = meta.get("project_name") or "未知项目"
            engagement_id = meta.get("engagement_id")
            dedupe_key = _engagement_group_key(hit)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            if self.settings.mock_rag:
                # In mock mode use the pre-built mock project data if name matches.
                matched = next(
                    (p for p in MOCK_COMPARISON_TABLE["projects"] if p["project_name"] == name),
                    None,
                )
                if matched:
                    project = dict(matched)
                    project["similarity_score"] = hit.get(
                        "similarity_score", matched["similarity_score"]
                    )
                    if engagement_id:
                        project["engagement_id"] = engagement_id
                    projects.append(project)
                    continue

            # Production: build project entry from real chunk metadata.
            projects.append(
                {
                    "project_name": name,
                    "similarity_score": hit.get("similarity_score", 0.5),
                    "source_doc": meta.get("source_doc", ""),
                    "engagement_id": engagement_id,
                    "customer": meta.get("customer", ""),
                    "year": meta.get("year"),
                    "functions": list(meta.get("functions") or []),
                    "dimensions": {},
                    "actual_man_days": "—",
                    "deviation_rate": "—",
                    "summary": (hit.get("content") or "")[:120],
                }
            )

        if self.settings.mock_rag and not projects:
            return list(MOCK_COMPARISON_TABLE["projects"])
        return projects

    def _build_recommendation(self, hits: list[dict[str, Any]]) -> str:
        if not hits:
            return "暂无足够历史项目，请人工补充参考"
        names = [
            (h.get("metadata") or {}).get("project_name", "")
            for h in hits[:2]
            if (h.get("metadata") or {}).get("project_name")
        ]
        if names:
            return f"建议参考 {'、'.join(names)}"
        return "已找到相似项目，请参考对比矩阵"

    def get_stats(self) -> dict[str, Any]:
        if self.settings.mock_rag:
            return {**MOCK_KNOWLEDGE_STATS, "mock_rag": True}

        kb = Path(self.knowledge_base_path)
        doc_extensions = {"*.docx", "*.doc", "*.xlsx", "*.xls"}
        doc_files = (
            [f for ext in doc_extensions for f in kb.rglob(ext)]
            if kb.exists()
            else []
        )
        project_dirs = (
            [p for p in kb.iterdir() if p.is_dir() and not p.name.startswith(".")]
            if kb.exists()
            else []
        )
        index = self._index_service()
        chunk_count = index.indexed_count()
        state = index.last_index_state()
        return {
            "total_documents": len(doc_files),
            "total_chunks": chunk_count,
            "total_projects": len(project_dirs),
            "last_import_at": state.get("last_index_at"),
            "active_generation": state.get("active_generation"),
            "vector_store": "pgvector",
            "embedding_model": state.get("embedding_model") or self.settings.embedding_model,
            "function_coverage": {},
            "mock_rag": False,
        }

    def list_documents(self) -> list[dict[str, Any]]:
        if self.settings.mock_rag:
            return [dict(doc) for doc in MOCK_KNOWLEDGE_DOCUMENTS]

        kb = Path(self.knowledge_base_path)
        if not kb.exists():
            return []

        from app.services.engagement_manifest_service import (
            ManifestLoadError,
            resolve_manifest,
        )
        from app.services.manpower_baselines_store import ManpowerBaselinesStore
        from app.utils.knowledge_paths import is_document_source_indexed

        index = self._index_service()
        by_engagement: dict[str, set[str]] = {}
        scoped = getattr(index, "list_indexed_source_docs_by_engagement", None)
        if callable(scoped):
            by_engagement = scoped() or {}
        # Older mocks / empty engagement metadata: fall back to flat source_doc set.
        if not by_engagement:
            flat = index.list_indexed_source_docs()
            if flat:
                by_engagement = {"": flat}

        baseline_sources_by_engagement: dict[str, set[str]] = {}
        for project in ManpowerBaselinesStore(self.settings).read().get("projects") or []:
            eng_id = str(project.get("engagement_id") or "")
            source = str(project.get("source_doc") or "")
            if eng_id and source:
                baseline_sources_by_engagement.setdefault(eng_id, set()).add(source)

        documents: list[dict[str, Any]] = []

        for folder in sorted(p for p in kb.iterdir() if p.is_dir() and not p.name.startswith(".")):
            try:
                manifest = resolve_manifest(folder)
            except (ManifestLoadError, ValueError, json.JSONDecodeError):
                continue

            rel_folder = str(folder.relative_to(kb)).replace("\\", "/")
            indexed_sources = set(by_engagement.get(manifest.engagement_id) or ())
            indexed_sources |= by_engagement.get("", set())
            quote_sources = baseline_sources_by_engagement.get(manifest.engagement_id, set())

            for doc in manifest.documents:
                rel_path = f"{rel_folder}/{doc.path}".replace("\\", "/")
                if doc.doc_type == "quote_manpower":
                    status = (
                        "indexed"
                        if is_document_source_indexed(quote_sources, rel_folder, doc.path)
                        else "pending"
                    )
                else:
                    status = (
                        "indexed"
                        if is_document_source_indexed(indexed_sources, rel_folder, doc.path)
                        else "pending"
                    )
                doc_path = folder / doc.path
                entry: dict[str, Any] = {
                    "path": rel_path,
                    "project_name": manifest.project_name,
                    "engagement_id": manifest.engagement_id,
                    "doc_type": doc.doc_type,
                    "status": status,
                }
                if doc_path.is_file():
                    entry["file_size_bytes"] = doc_path.stat().st_size
                documents.append(entry)

        return documents

    def import_documents(self) -> dict[str, Any]:
        kb = Path(self.knowledge_base_path)
        docx_files = list(kb.rglob("*.docx")) if kb.exists() else []
        now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        if self.settings.mock_rag:
            return {
                "new_documents": len(docx_files),
                "new_chunks": len(docx_files) * 10,
                "skipped": 0,
                "failed_files": [],
                "last_import_at": now,
            }

        raise RAGProductionError(
            "MOCK_RAG=false 时请使用 EngagementIngestService（POST /api/v1/knowledge/reindex）"
        )
