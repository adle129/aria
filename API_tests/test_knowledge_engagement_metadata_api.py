"""API tests for engagement metadata patch + list fields."""

from pathlib import Path

import pytest

from app.config import get_settings

SAMPLE_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "mock_chassis_rfq.docx"


def test_engagements_metadata_patch_and_list(client, upload_dir):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample files missing")
    get_settings.cache_clear()
    upload = client.post(
        "/api/v1/knowledge/engagements/upload",
        data={"engagement_id": "meta_api_eng"},
        files=[
            ("files", ("RFQ_mock.docx", SAMPLE_RFQ.read_bytes(), "application/octet-stream")),
        ],
    )
    assert upload.status_code == 200

    empty = client.patch(
        "/api/v1/knowledge/engagements/meta_api_eng/metadata",
        json={},
    )
    assert empty.status_code == 422

    incomplete = client.patch(
        "/api/v1/knowledge/engagements/meta_api_eng/metadata",
        json={"project_name": "Only Name", "customer": "OEM", "year": 2024, "functions": []},
    )
    assert incomplete.status_code == 422

    assert client.post("/api/v1/knowledge/customers", json={"name": "OEM"}).status_code == 200
    assert client.post("/api/v1/knowledge/customers", json={"name": "OEM-API"}).status_code == 200
    assert client.post("/api/v1/knowledge/vehicle-models", json={"name": "MEB"}).status_code == 200

    missing = client.patch(
        "/api/v1/knowledge/engagements/does_not_exist/metadata",
        json={
            "project_name": "X",
            "customer": "OEM",
            "year": 2024,
            "functions": ["PM"],
        },
    )
    assert missing.status_code == 404

    patched = client.patch(
        "/api/v1/knowledge/engagements/meta_api_eng/metadata",
        json={
            "project_name": "API Meta Project",
            "customer": "OEM-API",
            "vehicle_model": "MEB",
            "year": 2024,
            "functions": ["Chassis", "PM"],
        },
    )
    assert patched.status_code == 200
    data = patched.json()["data"]
    assert data["project_name"] == "API Meta Project"
    assert data["customer"] == "OEM-API"
    assert data["vehicle_model"] == "MEB"
    assert data["year"] == 2024
    assert data["functions"] == ["Chassis", "PM"]
    assert data["metadata_complete"] is True

    listed = client.get("/api/v1/knowledge/engagements")
    assert listed.status_code == 200
    rows = listed.json()["data"]["engagements"]
    row = next(r for r in rows if r["engagement_id"] == "meta_api_eng")
    assert row["customer"] == "OEM-API"
    assert row["vehicle_model"] == "MEB"
    assert row["functions"] == ["Chassis", "PM"]
    assert row["metadata_complete"] is True

    # upload_dir fixture may be KB root or uploads — resolve via settings
    kb = Path(get_settings().knowledge_base_path)
    manifest_path = kb / "meta_api_eng" / "manifest.json"
    assert manifest_path.is_file()
    text = manifest_path.read_text(encoding="utf-8")
    assert "OEM-API" in text
    assert "API Meta Project" in text
    assert "MEB" in text
