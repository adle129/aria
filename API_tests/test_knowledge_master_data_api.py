"""API tests for customer / vehicle_model master data + engagement filters."""

from pathlib import Path

import pytest

from app.config import get_settings

SAMPLE_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "mock_chassis_rfq.docx"


def test_customer_and_vehicle_model_crud(client):
    empty = client.get("/api/v1/knowledge/customers")
    assert empty.status_code == 200
    assert empty.json()["data"]["customers"] == []

    created = client.post("/api/v1/knowledge/customers", json={"name": "OEM-MD"})
    assert created.status_code == 200
    cid = created.json()["data"]["id"]
    assert created.json()["data"]["name"] == "OEM-MD"

    dup = client.post("/api/v1/knowledge/customers", json={"name": "OEM-MD"})
    assert dup.status_code == 409

    listed = client.get("/api/v1/knowledge/customers")
    assert any(c["id"] == cid for c in listed.json()["data"]["customers"])

    patched = client.patch(
        f"/api/v1/knowledge/customers/{cid}",
        json={"is_active": False},
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["is_active"] is False
    assert client.get("/api/v1/knowledge/customers").json()["data"]["customers"] == []
    inactive = client.get("/api/v1/knowledge/customers?include_inactive=true")
    assert len(inactive.json()["data"]["customers"]) == 1

    vm = client.post("/api/v1/knowledge/vehicle-models", json={"name": "MEB"})
    assert vm.status_code == 200
    mid = vm.json()["data"]["id"]
    assert client.get("/api/v1/knowledge/vehicle-models").json()["data"]["vehicle_models"][0][
        "name"
    ] == "MEB"
    renamed = client.patch(
        f"/api/v1/knowledge/vehicle-models/{mid}",
        json={"name": "PPE"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["data"]["name"] == "PPE"

    missing = client.patch(
        "/api/v1/knowledge/vehicle-models/does-not-exist",
        json={"is_active": False},
    )
    assert missing.status_code == 404

    renamed = client.patch(
        f"/api/v1/knowledge/customers/{cid}",
        json={"name": "OEM-MD-2", "is_active": True},
    )
    assert renamed.status_code == 200
    assert renamed.json()["data"]["name"] == "OEM-MD-2"

    deleted = client.delete(f"/api/v1/knowledge/customers/{cid}")
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted"] is True
    assert client.get("/api/v1/knowledge/customers?include_inactive=true").json()["data"][
        "customers"
    ] == []

    gone = client.delete("/api/v1/knowledge/customers/does-not-exist")
    assert gone.status_code == 404


def test_metadata_requires_master_customer_and_filters(client, upload_dir):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample files missing")
    get_settings.cache_clear()
    upload = client.post(
        "/api/v1/knowledge/engagements/upload",
        data={"engagement_id": "md_filter_eng"},
        files=[
            ("files", ("RFQ_mock.docx", SAMPLE_RFQ.read_bytes(), "application/octet-stream")),
        ],
    )
    assert upload.status_code == 200

    reject = client.patch(
        "/api/v1/knowledge/engagements/md_filter_eng/metadata",
        json={
            "project_name": "Filter Proj",
            "customer": "NotInMaster",
            "year": 2025,
            "functions": ["PM"],
        },
    )
    assert reject.status_code == 400

    assert client.post("/api/v1/knowledge/customers", json={"name": "FilterOEM"}).status_code == 200
    assert client.post("/api/v1/knowledge/vehicle-models", json={"name": "EV-SUV"}).status_code == 200

    patched = client.patch(
        "/api/v1/knowledge/engagements/md_filter_eng/metadata",
        json={
            "project_name": "Filter Proj",
            "customer": "FilterOEM",
            "vehicle_model": "EV-SUV",
            "year": 2025,
            "functions": ["PM", "Chassis"],
        },
    )
    assert patched.status_code == 200
    data = patched.json()["data"]
    assert data["customer"] == "FilterOEM"
    assert data["vehicle_model"] == "EV-SUV"

    filtered = client.get(
        "/api/v1/knowledge/engagements",
        params={"customer": "FilterOEM", "vehicle_model": "EV-SUV"},
    )
    assert filtered.status_code == 200
    rows = filtered.json()["data"]["engagements"]
    assert any(r["engagement_id"] == "md_filter_eng" for r in rows)

    miss = client.get(
        "/api/v1/knowledge/engagements",
        params={"customer": "FilterOEM", "vehicle_model": "Other"},
    )
    assert miss.json()["data"]["engagements"] == []

    kb = Path(get_settings().knowledge_base_path)
    text = (kb / "md_filter_eng" / "manifest.json").read_text(encoding="utf-8")
    assert "EV-SUV" in text
    assert "FilterOEM" in text
