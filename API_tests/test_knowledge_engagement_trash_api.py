"""API tests for R1-CHG14 engagement soft-delete / restore."""

from pathlib import Path

import pytest

from app.config import get_settings

SAMPLE_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "mock_chassis_rfq.docx"


def _seed(client, eng_id: str = "trash_api_eng"):
    if not SAMPLE_RFQ.exists():
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


def test_soft_delete_and_restore(client, upload_dir):
    _seed(client)
    listed = client.get("/api/v1/knowledge/engagements")
    row = next(
        r for r in listed.json()["data"]["engagements"] if r["engagement_id"] == "trash_api_eng"
    )
    assert row["deletable"] is True

    deleted = client.delete("/api/v1/knowledge/engagements/trash_api_eng")
    assert deleted.status_code == 200
    data = deleted.json()["data"]
    assert data["moved_to_trash"] is True
    assert data["purge_after"]

    after = client.get("/api/v1/knowledge/engagements")
    ids = {r["engagement_id"] for r in after.json()["data"]["engagements"]}
    assert "trash_api_eng" not in ids

    restored = client.post("/api/v1/knowledge/trash/engagements/trash_api_eng/restore")
    assert restored.status_code == 200
    assert restored.json()["data"]["restored"] is True
    assert restored.json()["data"]["needs_reindex"] is True

    again = client.get("/api/v1/knowledge/engagements")
    ids2 = {r["engagement_id"] for r in again.json()["data"]["engagements"]}
    assert "trash_api_eng" in ids2


def test_soft_delete_404(client, upload_dir):
    missing = client.delete("/api/v1/knowledge/engagements/no_such_trash_eng")
    assert missing.status_code == 404


def test_list_exposes_ref_task_ids_and_blocks_delete(client, upload_dir):
    from app.database import SessionLocal
    from app.models.rfq_task import RFQTask

    eng_id = "trash_ref_list_eng"
    _seed(client, eng_id)
    db = SessionLocal()
    try:
        db.add(
            RFQTask(
                id="rfq-ref-task-1",
                file_name="ref.docx",
                file_path="/tmp/ref.docx",
                archived=False,
                function_source_map={"PM": eng_id},
            )
        )
        db.commit()
    finally:
        db.close()

    listed = client.get("/api/v1/knowledge/engagements")
    row = next(
        r for r in listed.json()["data"]["engagements"] if r["engagement_id"] == eng_id
    )
    assert row["has_hard_refs"] is True
    assert row["deletable"] is False
    assert row["ref_task_ids"] == ["rfq-ref-task-1"]

    blocked = client.delete(f"/api/v1/knowledge/engagements/{eng_id}")
    assert blocked.status_code == 409
    body = blocked.json()
    assert "rfq-ref-task-1" in (body.get("data") or {}).get("ref_task_ids", [])


def test_document_delete_and_trash_list_restore_purge(client, upload_dir):
    SAMPLE_QA = (
        Path(__file__).resolve().parents[1]
        / "backend"
        / "data"
        / "templates"
        / "qa_template.xlsx"
    )
    eng_id = "trash_doc_api_eng"
    if not SAMPLE_RFQ.exists() or not SAMPLE_QA.exists():
        pytest.skip("sample files missing")
    get_settings.cache_clear()
    up = client.post(
        "/api/v1/knowledge/engagements/upload",
        data={"engagement_id": eng_id},
        files=[
            ("files", ("RFQ_mock.docx", SAMPLE_RFQ.read_bytes(), "application/octet-stream")),
            ("files", ("Q_A_mock.xlsx", SAMPLE_QA.read_bytes(), "application/octet-stream")),
        ],
    )
    assert up.status_code == 200

    deleted = client.delete(
        f"/api/v1/knowledge/engagements/{eng_id}/documents",
        params={"doc_type": "qa"},
    )
    assert deleted.status_code == 200
    body = deleted.json()["data"]
    assert body["moved_to_trash"] is True
    trash_id = body["trash_id"]
    assert trash_id.startswith("doc__")

    listed = client.get("/api/v1/knowledge/trash")
    assert listed.status_code == 200
    items = listed.json()["data"]["items"]
    assert any(i["trash_id"] == trash_id for i in items)

    restored = client.post(f"/api/v1/knowledge/trash/{trash_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["data"]["restored"] is True

    deleted2 = client.delete(
        f"/api/v1/knowledge/engagements/{eng_id}/documents",
        params={"doc_type": "qa"},
    )
    tid2 = deleted2.json()["data"]["trash_id"]
    purged = client.delete(f"/api/v1/knowledge/trash/{tid2}")
    assert purged.status_code == 200
    assert purged.json()["data"]["purged"] is True

    empty = client.get("/api/v1/knowledge/trash")
    assert empty.json()["data"]["items"] == []


def test_document_delete_404(client, upload_dir):
    missing = client.delete(
        "/api/v1/knowledge/engagements/no_doc_eng/documents",
        params={"doc_type": "qa"},
    )
    assert missing.status_code == 404