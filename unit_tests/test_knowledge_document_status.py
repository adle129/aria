"""Unit tests for document status overlay after engagement pending/failed."""

from app.services.knowledge_document_status import overlay_document_index_status


def test_overlay_forces_pending_when_engagement_pending():
    docs = [
        {
            "path": "e1/Q_A.xlsx",
            "engagement_id": "e1",
            "status": "indexed",
            "doc_type": "qa",
        },
        {
            "path": "e2/RFQ.docx",
            "engagement_id": "e2",
            "status": "indexed",
            "doc_type": "rfq",
        },
    ]
    out = overlay_document_index_status(docs, {"e1": "pending", "e2": "indexed"})
    assert out[0]["status"] == "pending"
    assert out[1]["status"] == "indexed"


def test_overlay_forces_failed_when_engagement_failed():
    docs = [{"path": "e1/a.docx", "engagement_id": "e1", "status": "indexed"}]
    out = overlay_document_index_status(docs, {"e1": "failed"})
    assert out[0]["status"] == "failed"


def test_overlay_noop_without_map():
    docs = [{"path": "e1/a.docx", "engagement_id": "e1", "status": "indexed"}]
    assert overlay_document_index_status(docs, {})[0]["status"] == "indexed"
