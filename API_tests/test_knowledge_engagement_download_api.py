"""API tests for R1-CHG06 knowledge source download."""

from pathlib import Path

from app.config import get_settings

SAMPLE_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "mock_chassis_rfq.docx"


def _seed(client, eng_id: str = "dl_api_eng"):
    if not SAMPLE_RFQ.exists():
        import pytest

        pytest.skip("sample files missing")
    get_settings.cache_clear()
    resp = client.post(
        "/api/v1/knowledge/engagements/upload",
        data={"engagement_id": eng_id},
        files=[
            ("files", ("RFQ_mock.docx", SAMPLE_RFQ.read_bytes(), "application/octet-stream")),
        ],
    )
    assert resp.status_code == 200


def test_download_rfq_returns_file(client, upload_dir, tmp_path, monkeypatch):
    audit = tmp_path / "dl_audit.jsonl"
    monkeypatch.setenv("KNOWLEDGE_DOWNLOAD_AUDIT_PATH", str(audit))
    get_settings.cache_clear()
    _seed(client)

    resp = client.get(
        "/api/v1/knowledge/engagements/dl_api_eng/documents/download",
        params={"doc_type": "rfq", "task_id": "t-1"},
    )
    assert resp.status_code == 200
    assert resp.content[:2] == b"PK" or len(resp.content) > 100
    cd = resp.headers.get("content-disposition", "")
    assert "task-t-1" in cd
    assert audit.is_file()
    audit_text = audit.read_text(encoding="utf-8")
    assert "dl_api_eng" in audit_text
    assert "t-1" in audit_text
    assert "task-t-1" in audit_text

def test_download_missing_404(client, upload_dir):
    missing = client.get(
        "/api/v1/knowledge/engagements/no_dl_eng/documents/download",
        params={"doc_type": "rfq"},
    )
    assert missing.status_code == 404


def test_download_bad_doc_type_400(client, upload_dir):
    _seed(client, eng_id="dl_api_bad_type")
    resp = client.get(
        "/api/v1/knowledge/engagements/dl_api_bad_type/documents/download",
        params={"doc_type": "not_a_type"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == 400
