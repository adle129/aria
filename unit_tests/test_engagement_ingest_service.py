import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.config import Settings
from app.services.engagement_ingest_service import EngagementIngestError, EngagementIngestService
from app.services.knowledge_index_service import flatten_engagement_chunks


SAMPLE_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "mock_chassis_rfq.docx"
QA_TEMPLATE = Path(__file__).resolve().parents[1] / "backend" / "data" / "templates" / "qa_template.xlsx"


@pytest.fixture
def engagement_folder(tmp_path):
    if not SAMPLE_RFQ.exists() or not QA_TEMPLATE.exists():
        pytest.skip("sample rfq or qa template missing")
    folder = tmp_path / "test_engagement"
    folder.mkdir()
    (folder / "RFQ_mock.docx").write_bytes(SAMPLE_RFQ.read_bytes())
    (folder / "Q_A_mock.xlsx").write_bytes(QA_TEMPLATE.read_bytes())
    manifest = {
        "engagement_id": "test_engagement",
        "project_name": "Test Engagement",
        "functions": ["Chassis", "PM"],
        "documents": [
            {"path": "RFQ_mock.docx", "doc_type": "rfq"},
            {"path": "Q_A_mock.xlsx", "doc_type": "qa"},
        ],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return folder


def test_assert_rfqa_gate_rejects_rfq_only():
    with pytest.raises(EngagementIngestError):
        EngagementIngestService.assert_rfqa_gate(
            [{"metadata": {"doc_type": "rfq"}}],
            "x",
        )


def test_prepare_engagement_builds_rfqa_chunks(engagement_folder, tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    target = kb / engagement_folder.name
    target.mkdir()
    for item in engagement_folder.iterdir():
        target.joinpath(item.name).write_bytes(item.read_bytes())

    service = EngagementIngestService(
        Settings(
            knowledge_base_path=str(kb),
            mock_rag=False,
            manpower_baselines_path=str(tmp_path / "baselines.json"),
        )
    )
    manifest, chunks, baseline = service.prepare_engagement(target)
    assert manifest.engagement_id == "test_engagement"
    doc_types = {(c["metadata"] or {}).get("doc_type") for c in chunks}
    assert "rfq" in doc_types
    assert "qa" in doc_types
    assert all(c["metadata"]["engagement_id"] == "test_engagement" for c in chunks)
    assert baseline is None


def test_import_all_mock_embed(engagement_folder, tmp_path, monkeypatch):
    kb = tmp_path / "kb"
    kb.mkdir()
    target = kb / engagement_folder.name
    target.mkdir()
    for item in engagement_folder.iterdir():
        target.joinpath(item.name).write_bytes(item.read_bytes())

    settings = Settings(
        knowledge_base_path=str(kb),
        mock_rag=False,
        manpower_baselines_path=str(tmp_path / "baselines.json"),
        database_url="sqlite://",
    )
    service = EngagementIngestService(settings, db=None)

    class FakeIndex:
        def __init__(self, *_args, **_kwargs):
            pass

        def index_chunks(self, chunks, *, clear=True, corpus_path=None, source_file=None):
            rfq = sum(1 for c in chunks if (c.get("metadata") or {}).get("doc_type") == "rfq")
            qa = sum(1 for c in chunks if (c.get("metadata") or {}).get("doc_type") == "qa")
            assert rfq >= 1 and qa >= 1
            return {"chunk_count": len(chunks), "last_index_at": "2026-07-07T00:00:00Z"}

    monkeypatch.setattr(
        "app.services.engagement_ingest_service.KnowledgeIndexService",
        FakeIndex,
    )
    result = service.import_all()
    assert result["new_chunks"] >= 1
    assert result["doc_type_counts"]["rfq"] >= 1
    assert result["doc_type_counts"]["qa"] >= 1
