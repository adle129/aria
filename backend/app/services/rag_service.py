import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.chroma_store import ChromaStore
from app.services.comparison_service import build_comparison_matrix
from app.services.mock_data import (
    MOCK_COMPARISON_TABLE,
    MOCK_KNOWLEDGE_DOCUMENTS,
    MOCK_KNOWLEDGE_STATS,
    MOCK_RAG_HITS,
)
from app.services.rfq_parser import RFQParser

IMPORT_STATE_FILENAME = "import_state.json"


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


class RAGService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.knowledge_base_path = settings.knowledge_base_path
        self._chroma: ChromaStore | None = None
        self._parser = RFQParser()

    def is_insufficient_evidence(self, hits: list[dict[str, Any]]) -> bool:
        if self.settings.mock_rag:
            return False
        if not hits:
            return True
        max_score = max(float(h.get("similarity_score") or 0.0) for h in hits)
        return max_score < float(self.settings.rag_similarity_threshold)

    def _get_chroma(self) -> ChromaStore:
        if self._chroma is None:
            self._chroma = ChromaStore(self.settings.chroma_path)
        return self._chroma

    def _import_state_path(self) -> Path:
        return Path(self.settings.chroma_path) / IMPORT_STATE_FILENAME

    def _read_import_state(self) -> dict[str, Any]:
        path = self._import_state_path()
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_import_state(self, state: dict[str, Any]) -> None:
        path = self._import_state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _file_hash(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def search_similar_projects(
        self,
        query: str,
        top_k: int = 5,
        function_filter: list[str] | None = None,
        doc_type_filter: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        if self.settings.mock_rag:
            hits = _filter_hits_by_functions(MOCK_RAG_HITS, function_filter)
            hits = _filter_hits_by_doc_type(hits, doc_type_filter)
            return hits[:top_k]

        from app.services.knowledge_index_service import KnowledgeIndexService

        index = KnowledgeIndexService(
            self.settings,
            namespace=self.settings.knowledge_vector_namespace,
        )
        try:
            hits = index.search(
                query,
                top_k=top_k,
                function_filter=function_filter,
                doc_type_filter=doc_type_filter,
            )
        except Exception:
            return []
        return hits

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

    def _projects_from_hits(self, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
        projects: list[dict[str, Any]] = []
        for hit in hits:
            meta = hit.get("metadata") or {}
            name = meta.get("project_name") or "未知项目"
            matched = next(
                (p for p in MOCK_COMPARISON_TABLE["projects"] if p["project_name"] == name),
                None,
            )
            if matched:
                project = dict(matched)
                project["similarity_score"] = hit.get("similarity_score", matched["similarity_score"])
            else:
                project = {
                    "project_name": name,
                    "similarity_score": hit.get("similarity_score", 0.5),
                    "source_doc": meta.get("source_doc", ""),
                    "dimensions": {},
                    "actual_man_days": "—",
                    "deviation_rate": "—",
                    "summary": (hit.get("content") or "")[:120],
                }
            projects.append(project)
        if self.settings.mock_rag:
            return projects or list(MOCK_COMPARISON_TABLE["projects"])
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
        return MOCK_COMPARISON_TABLE["recommendation"]

    def get_stats(self) -> dict[str, Any]:
        if self.settings.mock_rag:
            return {**MOCK_KNOWLEDGE_STATS, "mock_rag": True}

        kb = Path(self.knowledge_base_path)
        docx_files = list(kb.rglob("*.docx")) if kb.exists() else []
        project_dirs = [p for p in kb.iterdir() if p.is_dir()] if kb.exists() else []
        chunk_count = len(docx_files) * 10 if docx_files else 0
        try:
            from app.services.knowledge_index_service import KnowledgeIndexService

            chunk_count = KnowledgeIndexService(self.settings).indexed_count()
        except Exception:
            pass
        import_state = self._read_import_state()
        return {
            "total_documents": len(docx_files),
            "total_chunks": chunk_count,
            "total_projects": len(project_dirs),
            "last_import_at": import_state.get("last_import_at"),
            "function_coverage": {},
            "mock_rag": False,
        }

    def list_documents(self) -> list[dict[str, Any]]:
        if self.settings.mock_rag:
            return [dict(doc) for doc in MOCK_KNOWLEDGE_DOCUMENTS]

        kb = Path(self.knowledge_base_path)
        if not kb.exists():
            return []

        import_state = self._read_import_state()
        failed_map = {
            item.get("path"): item.get("error", "索引失败")
            for item in import_state.get("failed_files", [])
            if item.get("path")
        }
        store = self._get_chroma()
        documents: list[dict[str, Any]] = []

        for doc_path in sorted(kb.rglob("*.docx")):
            rel_path = str(doc_path.relative_to(kb)).replace("\\", "/")
            project_dir = doc_path.relative_to(kb).parts[0] if doc_path.relative_to(kb).parts else "unknown"
            if rel_path in failed_map:
                status = "failed"
                error = failed_map[rel_path]
            elif store.get_metadata(rel_path):
                status = "indexed"
                error = None
            else:
                status = "pending"
                error = None

            entry: dict[str, Any] = {
                "path": rel_path,
                "project_name": project_dir.replace("_", " ").title(),
                "doc_type": infer_doc_type(doc_path.name),
                "status": status,
                "file_size_bytes": doc_path.stat().st_size,
            }
            if error:
                entry["error"] = error
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

        store = self._get_chroma()
        new_docs = 0
        skipped = 0
        failed_files: list[dict[str, str]] = []

        for doc_path in docx_files:
            doc_id = str(doc_path.relative_to(kb)).replace("\\", "/")
            try:
                file_hash = self._file_hash(doc_path)
                existing = store.get_metadata(doc_id)
                if existing and existing.get("file_hash") == file_hash:
                    skipped += 1
                    continue

                text = self._parser.extract_text_from_docx(str(doc_path))
                project_dir = doc_path.relative_to(kb).parts[0] if doc_path.relative_to(kb).parts else "unknown"
                store.add_document(
                    doc_id,
                    text[:8000],
                    {
                        "project_name": project_dir.replace("_", " ").title(),
                        "source_doc": doc_id,
                        "doc_type": infer_doc_type(doc_path.name),
                        "file_hash": file_hash,
                    },
                )
                new_docs += 1
            except Exception as exc:
                failed_files.append({"path": doc_id, "error": str(exc)[:200]})

        self._write_import_state(
            {
                "last_import_at": now,
                "failed_files": failed_files,
            }
        )

        return {
            "new_documents": new_docs,
            "new_chunks": store.count(),
            "skipped": skipped,
            "failed_files": failed_files,
            "last_import_at": now,
        }
