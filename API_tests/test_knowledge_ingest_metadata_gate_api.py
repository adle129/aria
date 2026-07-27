"""API: incomplete engagement metadata must not enter the vector index."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import get_settings

SAMPLE_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "mock_chassis_rfq.docx"


def test_reindex_skips_incomplete_metadata_engagement(client, upload_dir, monkeypatch):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")

    monkeypatch.setenv("MOCK_RAG", "false")
    monkeypatch.setenv("KB_ASYNC_INDEX_ENABLED", "false")
    get_settings.cache_clear()
    settings = get_settings()
    kb = Path(settings.knowledge_base_path)
    folder = kb / "api_incomplete_meta"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "RFQ_mock.docx").write_bytes(SAMPLE_RFQ.read_bytes())
    (folder / "manifest.json").write_text(
        json.dumps(
            {
                "engagement_id": "api_incomplete_meta",
                "project_name": "API Incomplete",
                "documents": [{"path": "RFQ_mock.docx", "doc_type": "rfq"}],
            }
        ),
        encoding="utf-8",
    )

    indexed_ids: list[str] = []

    class FakeIndex:
        def __init__(self, *_args, **_kwargs):
            pass

        def build_generation(self, chunks, **_kwargs):
            for c in chunks:
                eid = (c.get("metadata") or {}).get("engagement_id")
                if eid and eid not in indexed_ids:
                    indexed_ids.append(eid)
            return {"generation_id": "api-staged", "chunk_count": len(chunks)}

        def activate_generation(self, staged):
            return {
                **staged,
                "active_generation": staged["generation_id"],
                "last_index_at": "2026-07-26T00:00:00Z",
            }

        def fail_generation(self, generation_id, error):
            return None

    monkeypatch.setattr(
        "app.services.engagement_ingest_service.KnowledgeIndexService",
        FakeIndex,
    )

    resp = client.post("/api/v1/knowledge/reindex")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "api_incomplete_meta" not in indexed_ids
    failed_paths = {f["path"] for f in data.get("failed_files") or []}
    assert "api_incomplete_meta" in failed_paths
    by_id = {e["engagement_id"]: e for e in data.get("engagements") or []}
    assert by_id["api_incomplete_meta"]["status"] == "failed"
    assert by_id["api_incomplete_meta"]["indexable"] is False
