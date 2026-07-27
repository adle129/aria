"""API tests for R1-CHG13 engagement document upsert."""

import io
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.config import get_settings

SAMPLE_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "mock_chassis_rfq.docx"


def _xlsx_bytes() -> bytes:
    wb = Workbook()
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _seed_engagement(client, eng_id: str = "doc_api_eng"):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample files missing")
    get_settings.cache_clear()
    upload = client.post(
        "/api/v1/knowledge/engagements/upload",
        data={"engagement_id": eng_id},
        files=[
            ("files", ("RFQ_mock.docx", SAMPLE_RFQ.read_bytes(), "application/octet-stream")),
        ],
    )
    assert upload.status_code == 200


def test_document_upsert_qa_success(client, upload_dir):
    _seed_engagement(client)
    resp = client.post(
        "/api/v1/knowledge/engagements/doc_api_eng/documents",
        data={"doc_type": "qa", "replace": "true"},
        files=[("file", ("客户问答.xlsx", _xlsx_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["doc_type"] == "qa"
    assert data["needs_reindex"] is True
    assert data["index_status"] == "pending"
    assert data["path"]

    listed = client.get("/api/v1/knowledge/engagements")
    row = next(r for r in listed.json()["data"]["engagements"] if r["engagement_id"] == "doc_api_eng")
    assert row["index_status"] == "pending"


def test_documents_list_overlays_pending_after_replace(client, upload_dir, monkeypatch):
    """Stale path-based indexed status must become pending when engagement is pending."""
    _seed_engagement(client, "doc_overlay_eng")
    assert (
        client.post(
            "/api/v1/knowledge/engagements/doc_overlay_eng/documents",
            data={"doc_type": "rfq", "replace": "true"},
            files=[
                ("file", ("RFQ_new.docx", SAMPLE_RFQ.read_bytes(), "application/octet-stream"))
            ],
        ).status_code
        == 200
    )

    monkeypatch.setattr(
        "app.services.rag_service.RAGService.list_documents",
        lambda self: [
            {
                "path": "doc_overlay_eng/RFQ_new.docx",
                "engagement_id": "doc_overlay_eng",
                "doc_type": "rfq",
                "status": "indexed",
                "project_name": "doc_overlay_eng",
            }
        ],
    )
    docs = client.get("/api/v1/knowledge/documents")
    assert docs.status_code == 200
    eng_docs = docs.json()["data"]["documents"]
    assert eng_docs
    assert all(d["status"] == "pending" for d in eng_docs)


def test_document_upsert_404_and_400(client, upload_dir):
    _seed_engagement(client, "doc_api_eng2")
    missing = client.post(
        "/api/v1/knowledge/engagements/no_such_eng/documents",
        data={"doc_type": "rfq", "replace": "true"},
        files=[("file", ("RFQ.docx", SAMPLE_RFQ.read_bytes(), "application/octet-stream"))],
    )
    assert missing.status_code == 404

    bad = client.post(
        "/api/v1/knowledge/engagements/doc_api_eng2/documents",
        data={"doc_type": "qa", "replace": "true"},
        files=[("file", ("bad.docx", b"not-xlsx", "application/octet-stream"))],
    )
    assert bad.status_code == 400


def test_document_upsert_conflict_when_replace_false(client, upload_dir):
    _seed_engagement(client, "doc_api_eng3")
    conflict = client.post(
        "/api/v1/knowledge/engagements/doc_api_eng3/documents",
        data={"doc_type": "rfq", "replace": "false"},
        files=[("file", ("RFQ_new.docx", SAMPLE_RFQ.read_bytes(), "application/octet-stream"))],
    )
    assert conflict.status_code == 409
