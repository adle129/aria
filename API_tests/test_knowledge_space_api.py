"""API tests for R1-CHG12 Knowledge Space defaults."""

from pathlib import Path

import pytest

from app.config import get_settings

SAMPLE_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "mock_chassis_rfq.docx"


def test_engagements_default_space_and_reject_unknown(client, upload_dir):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample files missing")
    get_settings.cache_clear()
    upload = client.post(
        "/api/v1/knowledge/engagements/upload",
        data={"engagement_id": "space_api_eng"},
        files=[
            ("files", ("RFQ_mock.docx", SAMPLE_RFQ.read_bytes(), "application/octet-stream")),
        ],
    )
    assert upload.status_code == 200

    listed = client.get("/api/v1/knowledge/engagements")
    assert listed.status_code == 200
    body = listed.json()["data"]
    assert body["space_id"] == "quoting"
    row = next(r for r in body["engagements"] if r["engagement_id"] == "space_api_eng")
    assert row["space_id"] == "quoting"

    bad = client.get("/api/v1/knowledge/engagements", params={"space_id": "unknown_lib"})
    assert bad.status_code == 400

    # finance is reserved but empty for now
    empty_finance = client.get("/api/v1/knowledge/engagements", params={"space_id": "finance"})
    assert empty_finance.status_code == 200
    assert empty_finance.json()["data"]["space_id"] == "finance"
    assert empty_finance.json()["data"]["engagements"] == []
