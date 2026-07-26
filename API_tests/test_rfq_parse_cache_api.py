"""API coverage for R1-PERF08: parse cache must not break upload/status contracts."""

from pathlib import Path

from app.database import get_db
from app.main import app
from app.models.rfq_parse_cache import RfqParseCache
from app.models.rfq_task import RFQTask
from app.repositories.rfq_parse_cache_repository import RfqParseCacheRepository
from app.repositories.rfq_task_repository import RFQTaskRepository
from app.services.rfq_parse_cache_service import PARSER_VERSION, build_cache_key, sha256_file

SAMPLE_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "mock_chassis_rfq.docx"


def _db(client):
    return next(app.dependency_overrides[get_db]())


def test_upload_succeeds_when_parse_cache_table_present(client):
    import pytest

    if not SAMPLE_RFQ.is_file():
        pytest.skip("sample RFQ missing")
    with SAMPLE_RFQ.open("rb") as fh:
        resp = client.post(
            "/api/v1/rfq/upload",
            files={
                "file": (
                    "mock_chassis_rfq.docx",
                    fh,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["task_id"]
    assert body["data"]["processing_status"] in {
        "queued",
        "pending",
        "parsing",
        "dimension_review",
    }
    assert "status" in body["data"]


def test_status_after_seeded_cache_hit_payload(client, upload_dir):
    """Seed cache for an existing file hash; status payload stays well-formed."""
    db = _db(client)
    content = b"api-cache-seed-bytes"
    stored = upload_dir / "uploads" / "seed.docx"
    stored.parent.mkdir(parents=True, exist_ok=True)
    stored.write_bytes(content)
    content_hash = sha256_file(stored)
    # baseline version from seed file used by API fixture when present
    baseline_version = "v1"
    key = build_cache_key(
        content_hash=content_hash,
        parser_version=PARSER_VERSION,
        prompt_version="v1",
        baseline_version=baseline_version,
    )
    RfqParseCacheRepository(db).upsert(
        cache_key=key,
        content_hash=content_hash,
        parser_version=PARSER_VERSION,
        prompt_version="v1",
        baseline_version=baseline_version,
        rfq_modules={"project_name": "Seeded", "modules": []},
        dimension_draft={"baseline_version": baseline_version, "items": []},
    )
    task = RFQTask(
        file_name="seed.docx",
        file_path=str(stored),
        processing_status="dimension_review",
        progress="40",
        status_message="等待工程师确认基准维度清单",
        rfq_modules={"project_name": "Seeded", "modules": []},
        dimension_draft={"baseline_version": baseline_version, "items": []},
    )
    RFQTaskRepository(db).create(task)
    task_id = task.id
    db.close()

    status = client.get(f"/api/v1/rfq/tasks/{task_id}/status")
    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "dimension_review"
    assert "等待工程师确认" in (payload.get("message") or "")
    assert payload["progress"] == 40
