import io
import zipfile
from pathlib import Path

import pytest

from app.config import get_settings

SAMPLE_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "mock_chassis_rfq.docx"
QA_TEMPLATE = Path(__file__).resolve().parents[1] / "backend" / "data" / "templates" / "qa_template.xlsx"
SEED_BASELINE = (
    Path(__file__).resolve().parents[1] / "backend" / "data" / "config" / "dimension_baseline.v1.json"
)


def _engagement_zip(name: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{name}/RFQ_mock.docx", SAMPLE_RFQ.read_bytes())
        zf.writestr(f"{name}/Q_A_mock.xlsx", QA_TEMPLATE.read_bytes())
    return buf.getvalue()


def test_engagements_upload_loose_files(client, upload_dir, monkeypatch):
    if not SAMPLE_RFQ.exists() or not QA_TEMPLATE.exists():
        pytest.skip("sample files missing")
    get_settings.cache_clear()
    resp = client.post(
        "/api/v1/knowledge/engagements/upload",
        data={"engagement_id": "api_engagement"},
        files=[
            ("files", ("RFQ_mock.docx", SAMPLE_RFQ.read_bytes(), "application/octet-stream")),
            ("files", ("Q_A_mock.xlsx", QA_TEMPLATE.read_bytes(), "application/octet-stream")),
        ],
    )
    assert resp.status_code == 200
    packs = resp.json()["data"]["packs"]
    assert len(packs) == 1
    assert packs[0]["engagement_id"] == "api_engagement"
    assert packs[0]["status"] == "stored"
    assert packs[0]["stored"] is True
    assert packs[0]["tier"] == "silver"
    assert packs[0]["indexable"] is True
    assert packs[0]["automation_impacts"]


def test_engagements_upload_zip(client, upload_dir, monkeypatch):
    if not SAMPLE_RFQ.exists() or not QA_TEMPLATE.exists():
        pytest.skip("sample files missing")
    get_settings.cache_clear()
    resp = client.post(
        "/api/v1/knowledge/engagements/upload",
        files=[("files", ("pack.zip", _engagement_zip("zip_api_eng"), "application/zip"))],
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["packs"][0]["engagement_id"] == "zip_api_eng"


def test_engagements_upload_rfq_only_is_indexable_copper(client, upload_dir):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")
    get_settings.cache_clear()
    resp = client.post(
        "/api/v1/knowledge/engagements/upload",
        data={"engagement_id": "api_copper_engagement"},
        files=[
            ("files", ("RFQ_mock.docx", SAMPLE_RFQ.read_bytes(), "application/octet-stream")),
        ],
    )

    assert resp.status_code == 200
    pack = resp.json()["data"]["packs"][0]
    assert pack["status"] == "stored"
    assert pack["tier"] == "copper"
    assert pack["indexable"] is True
    assert pack["missing"] == ["qa", "quote_manpower"]
    assert len(pack["automation_impacts"]) == 2


def test_engagements_upload_missing_engagement_id_400(client, upload_dir):
    get_settings.cache_clear()
    resp = client.post(
        "/api/v1/knowledge/engagements/upload",
        files=[("files", ("RFQ.docx", b"data", "application/octet-stream"))],
    )
    assert resp.status_code == 400
