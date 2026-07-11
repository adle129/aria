from app.config import get_settings


def _production_jobs(monkeypatch) -> None:
    monkeypatch.setenv("MOCK_RAG", "false")
    get_settings.cache_clear()


def test_import_creates_batch_record(client, monkeypatch):
    _production_jobs(monkeypatch)
    created = client.post("/api/v1/knowledge/import").json()["data"]
    batches = client.get("/api/v1/knowledge/batches").json()["data"]["batches"]
    detail = client.get(
        f"/api/v1/knowledge/batches/{batches[0]['import_id']}"
    ).json()["data"]

    assert created["job_id"] == batches[0]["job_id"]
    assert batches[0]["mode"] == "incremental"
    assert batches[0]["status"] == "queued"
    assert detail["import_id"] == batches[0]["import_id"]


def test_upload_records_engagement_audit(client, upload_dir):
    rfq = (
        __import__("pathlib").Path(__file__).resolve().parents[1]
        / "samples"
        / "rfq"
        / "mock_chassis_rfq.docx"
    )
    if not rfq.exists():
        return
    client.post(
        "/api/v1/knowledge/engagements/upload",
        files=[("files", ("RFQ_demo.docx", rfq.read_bytes(), "application/octet-stream"))],
        data={"engagement_id": "audit_demo"},
    )
    rows = client.get("/api/v1/knowledge/engagements").json()["data"]["engagements"]
    match = next(row for row in rows if row["engagement_id"] == "audit_demo")
    assert match["tier"] in {"gold", "silver", "copper"}
    assert match["content_hash"]
    assert match["index_status"] == "pending"


def test_unknown_import_batch_returns_404(client):
    response = client.get("/api/v1/knowledge/batches/not-found")
    assert response.status_code == 404
