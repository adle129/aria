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
