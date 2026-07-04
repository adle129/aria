"""ChromaDB persistence for knowledge base documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class ChromaStore:
    def __init__(self, chroma_path: str, collection_name: str = "aria_projects"):
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    def _ensure_client(self):
        if self._collection is not None:
            return
        import chromadb

        Path(self.chroma_path).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=self.chroma_path)
        self._collection = self._client.get_or_create_collection(name=self.collection_name)

    def add_document(self, doc_id: str, text: str, metadata: dict[str, Any]) -> None:
        self._ensure_client()
        assert self._collection is not None
        safe_meta = {k: str(v) for k, v in metadata.items() if v is not None}
        self._collection.upsert(ids=[doc_id], documents=[text], metadatas=[safe_meta])

    def get_metadata(self, doc_id: str) -> dict[str, Any] | None:
        self._ensure_client()
        assert self._collection is not None
        if self._collection.count() == 0:
            return None
        result = self._collection.get(ids=[doc_id], include=["metadatas"])
        metas = result.get("metadatas") or []
        if not metas or not metas[0]:
            return None
        return dict(metas[0])

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        self._ensure_client()
        assert self._collection is not None
        if self._collection.count() == 0:
            return []
        result = self._collection.query(query_texts=[query], n_results=min(top_k, self._collection.count()))
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        hits: list[dict[str, Any]] = []
        for doc, meta, dist in zip(documents, metadatas, distances, strict=False):
            similarity = max(0.0, min(1.0, 1.0 - (dist or 0.0)))
            hits.append(
                {
                    "content": doc,
                    "metadata": meta or {},
                    "similarity_score": round(similarity, 2),
                }
            )
        return sorted(hits, key=lambda x: x["similarity_score"], reverse=True)

    def count(self) -> int:
        self._ensure_client()
        assert self._collection is not None
        return self._collection.count()
