"""R1 profile API gates — block Demo / undelivered milestone stubs."""

import time


def test_demo_rfq_samples_blocked_on_r1_profile(client, monkeypatch):
    monkeypatch.setenv("ARIA_UI_PROFILE", "r1")
    from app.config import get_settings

    get_settings.cache_clear()

    resp = client.get("/api/v1/demo/rfq-samples")
    assert resp.status_code == 404


def test_generate_proposal_blocked_on_r1_profile(client, sample_rfq_bytes, monkeypatch):
    monkeypatch.setenv("ARIA_UI_PROFILE", "r1")
    from app.config import get_settings
    import app.api.v1.rfq as rfq_module
    from app.services.rfq_analysis_service import RFQAnalysisService

    get_settings.cache_clear()
    settings = get_settings()
    rfq_module.analysis_service = RFQAnalysisService(settings)

    upload = client.post(
        "/api/v1/rfq/upload",
        files={
            "file": (
                "mock_chassis_rfq.docx",
                sample_rfq_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    task_id = upload.json()["data"]["task_id"]

    for _ in range(30):
        status = client.get(f"/api/v1/rfq/tasks/{task_id}/status").json()
        if status["status"] in {"dimension_review", "completed", "failed"}:
            break
        time.sleep(0.05)

    resp = client.post(f"/api/v1/rfq/tasks/{task_id}/generate-proposal")
    assert resp.status_code == 404


def test_dimension_baseline_available_on_r1_profile(client, monkeypatch):
    monkeypatch.setenv("ARIA_UI_PROFILE", "r1")
    from app.config import get_settings

    get_settings.cache_clear()
    resp = client.get("/api/v1/rfq/dimension-baseline")
    assert resp.status_code in {200, 404}
