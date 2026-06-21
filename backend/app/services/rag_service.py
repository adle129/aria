from pathlib import Path
from typing import Any

from app.config import Settings
from app.services.chroma_store import ChromaStore
from app.services.comparison_service import build_comparison_matrix
from app.services.mock_data import MOCK_COMPARISON_TABLE, MOCK_RAG_HITS
from app.services.rfq_parser import RFQParser


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


class RAGService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.knowledge_base_path = settings.knowledge_base_path
        self._chroma: ChromaStore | None = None
        self._parser = RFQParser()

    def _get_chroma(self) -> ChromaStore:
        if self._chroma is None:
            self._chroma = ChromaStore(self.settings.chroma_path)
        return self._chroma

    def search_similar_projects(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if self.settings.mock_rag:
            return MOCK_RAG_HITS[:top_k]

        hits = self._get_chroma().search(query, top_k=top_k)
        if hits:
            return hits
        return MOCK_RAG_HITS[:top_k]

    def build_comparison_table(
        self, rfq_data: dict[str, Any], similar_docs: list[dict[str, Any]]
    ) -> dict[str, Any]:
        scores = [doc.get("similarity_score", 0.0) for doc in similar_docs]
        confidence = calculate_overall_confidence(scores)

        if self.settings.mock_rag:
            table = dict(MOCK_COMPARISON_TABLE)
            table["overall_confidence"] = confidence
        else:
            table = {
                "comparison_dimensions": MOCK_COMPARISON_TABLE["comparison_dimensions"],
                "projects": self._projects_from_hits(similar_docs),
                "recommendation": self._build_recommendation(similar_docs),
            }
            table["overall_confidence"] = confidence

        matrix = build_comparison_matrix(
            rfq_data,
            table["projects"],
            dimensions=table.get("comparison_dimensions"),
        )
        table.update(matrix)
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
        return projects or list(MOCK_COMPARISON_TABLE["projects"])

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
        kb = Path(self.knowledge_base_path)
        docx_files = list(kb.rglob("*.docx")) if kb.exists() else []
        project_dirs = [p for p in kb.iterdir() if p.is_dir()] if kb.exists() else []
        chunk_count = len(docx_files) * 10 if docx_files else 0
        if not self.settings.mock_rag:
            try:
                chunk_count = self._get_chroma().count()
            except Exception:
                pass
        return {
            "total_documents": len(docx_files),
            "total_chunks": chunk_count,
            "total_projects": len(project_dirs),
            "last_import_at": None,
            "mock_rag": self.settings.mock_rag,
        }

    def import_documents(self) -> dict[str, int]:
        kb = Path(self.knowledge_base_path)
        docx_files = list(kb.rglob("*.docx")) if kb.exists() else []
        if self.settings.mock_rag:
            return {
                "new_documents": len(docx_files),
                "new_chunks": len(docx_files) * 10,
                "skipped": 0,
            }

        store = self._get_chroma()
        new_docs = 0
        skipped = 0
        for doc_path in docx_files:
            doc_id = str(doc_path.relative_to(kb)).replace("\\", "/")
            try:
                text = self._parser.extract_text_from_docx(str(doc_path))
                project_dir = doc_path.relative_to(kb).parts[0] if doc_path.relative_to(kb).parts else "unknown"
                store.add_document(
                    doc_id,
                    text[:8000],
                    {
                        "project_name": project_dir.replace("_", " ").title(),
                        "source_doc": doc_id,
                        "doc_type": "summary",
                    },
                )
                new_docs += 1
            except Exception:
                skipped += 1
        return {
            "new_documents": new_docs,
            "new_chunks": store.count(),
            "skipped": skipped,
        }
