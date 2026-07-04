from pathlib import Path

import pytest


@pytest.fixture
def demo_samples_dir(tmp_path, monkeypatch):
    rfq_dir = tmp_path / "samples" / "rfq"
    rfq_dir.mkdir(parents=True)
    (rfq_dir / "mock_chassis_rfq.docx").write_bytes(b"pk-mock-chassis")
    (rfq_dir / "demo_multifunction_rfq.docx").write_bytes(b"pk-demo-multi")
    monkeypatch.setenv("SAMPLES_RFQ_PATH", str(rfq_dir))
    from app.config import get_settings

    get_settings.cache_clear()
    yield rfq_dir
    get_settings.cache_clear()


def test_list_demo_rfq_samples(client, demo_samples_dir):
    resp = client.get("/api/v1/demo/rfq-samples")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    samples = body["data"]["samples"]
    assert len(samples) == 2
    filenames = {s["filename"] for s in samples}
    assert filenames == {"mock_chassis_rfq.docx", "demo_multifunction_rfq.docx"}
    assert all(s["download_url"].startswith("/api/v1/demo/rfq-samples/") for s in samples)


def test_download_demo_rfq_sample(client, demo_samples_dir):
    resp = client.get("/api/v1/demo/rfq-samples/mock_chassis_rfq.docx")
    assert resp.status_code == 200
    assert resp.content == b"pk-mock-chassis"
    assert "wordprocessingml" in resp.headers.get("content-type", "")


def test_download_demo_rfq_sample_not_found(client, upload_dir, monkeypatch):
    from app.config import get_settings

    empty = Path(upload_dir) / "empty_rfq"
    empty.mkdir()
    monkeypatch.setenv("SAMPLES_RFQ_PATH", str(empty))
    get_settings.cache_clear()

    resp = client.get("/api/v1/demo/rfq-samples/mock_chassis_rfq.docx")
    assert resp.status_code == 404

    get_settings.cache_clear()


def test_download_demo_rfq_sample_invalid_name(client, demo_samples_dir):
    resp = client.get("/api/v1/demo/rfq-samples/not_allowed.docx")
    assert resp.status_code == 404
