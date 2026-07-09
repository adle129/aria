"""REG-D01/M01: dimension_review + confirm-dimensions matrix structure (Mock RAG)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RFQ = ROOT / "samples" / "rfq" / "mock_chassis_rfq.docx"
DIMENSION_BASELINE_SEED = ROOT / "backend" / "data" / "config" / "dimension_baseline.v1.json"


def _wait_dimension_review(client: TestClient, task_id: str) -> None:
    for _ in range(40):
        status = client.get(f"/api/v1/rfq/tasks/{task_id}/status").json()
        if status["status"] == "dimension_review":
            return
        if status["status"] in {"failed", "completed"}:
            break
        time.sleep(0.05)
    raise AssertionError(f"task {task_id} did not reach dimension_review")


def _wait_completed(client: TestClient, task_id: str) -> None:
    for _ in range(40):
        status = client.get(f"/api/v1/rfq/tasks/{task_id}/status").json()
        if status["status"] in {"completed", "failed"}:
            return
        time.sleep(0.05)


@pytest.fixture
def regression_client(tmp_path, monkeypatch):
    if not SAMPLE_RFQ.is_file():
        pytest.skip(f"missing {SAMPLE_RFQ}")

    template_src = ROOT / "backend" / "data" / "templates"
    template_dst = tmp_path / "templates"
    template_dst.mkdir(exist_ok=True)
    for name in ("quote_template.xlsx", "qa_template.xlsx"):
        src = template_src / name
        if src.is_file():
            (template_dst / name).write_bytes(src.read_bytes())

    monkeypatch.setenv("UPLOAD_PATH", str(tmp_path / "uploads"))
    monkeypatch.setenv("OUTPUT_PATH", str(tmp_path / "outputs"))
    monkeypatch.setenv("TEMPLATE_PATH", str(template_dst))
    monkeypatch.setenv("KNOWLEDGE_BASE_PATH", str(tmp_path / "kb"))
    if DIMENSION_BASELINE_SEED.is_file():
        monkeypatch.setenv("DIMENSION_BASELINE_PATH", str(DIMENSION_BASELINE_SEED))
    (tmp_path / "uploads").mkdir(exist_ok=True)
    (tmp_path / "outputs").mkdir(exist_ok=True)
    (tmp_path / "kb").mkdir(exist_ok=True)

    from app.config import get_settings
    from app.database import Base, get_db
    from app.main import app
    from app.models.engagement import Engagement
    from app.models.project import Project
    from app.models.rfq_task import RFQTask
    from app.models.task_job import TaskJob
    from app.models.user import User

    get_settings.cache_clear()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[
            Project.__table__,
            User.__table__,
            RFQTask.__table__,
            TaskJob.__table__,
            Engagement.__table__,
        ],
    )
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    import app.api.v1.rfq as rfq_module
    import app.database as database_module
    from app.services.rfq_analysis_service import RFQAnalysisService

    settings = get_settings()
    rfq_module.analysis_service = RFQAnalysisService(settings)
    rfq_module.quote_service.settings = settings
    rfq_module.artifact_service.settings = settings
    monkeypatch.setattr(database_module, "engine", engine)
    monkeypatch.setattr(database_module, "SessionLocal", session_factory)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_reg_d01_dimension_draft_structure(regression_client):
    upload = regression_client.post(
        "/api/v1/rfq/upload",
        files={
            "file": (
                "mock_chassis_rfq.docx",
                SAMPLE_RFQ.read_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert upload.status_code == 200, upload.text
    task_id = upload.json()["data"]["task_id"]
    _wait_dimension_review(regression_client, task_id)

    task = regression_client.get(f"/api/v1/rfq/tasks/{task_id}").json()["data"]
    assert task["processing_status"] == "dimension_review"
    draft = task.get("dimension_draft") or {}
    items = draft.get("items") or []
    assert len(items) >= 1
    assert draft.get("baseline_version")
    assert task["comparison_table"] is None
    assert task["artifacts_status"]["rfq_parsed"] is True


def test_reg_m01_confirm_matrix_structure(regression_client):
    upload = regression_client.post(
        "/api/v1/rfq/upload",
        files={
            "file": (
                "mock_chassis_rfq.docx",
                SAMPLE_RFQ.read_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    task_id = upload.json()["data"]["task_id"]
    _wait_dimension_review(regression_client, task_id)
    task = regression_client.get(f"/api/v1/rfq/tasks/{task_id}").json()["data"]
    items = task["dimension_draft"]["items"]
    if not any(i.get("in_scope") for i in items):
        items = [{**items[0], "in_scope": True}] if items else []

    confirm = regression_client.post(
        f"/api/v1/rfq/tasks/{task_id}/confirm-dimensions",
        json={
            "baseline_version": task["dimension_draft"].get("baseline_version"),
            "items": items,
            "custom_items": task["dimension_draft"].get("custom_items") or [],
        },
    )
    assert confirm.status_code == 200, confirm.text
    _wait_completed(regression_client, task_id)

    done = regression_client.get(f"/api/v1/rfq/tasks/{task_id}").json()["data"]
    table = done.get("comparison_table") or {}
    projects = table.get("projects") or []
    matrix_rows = table.get("matrix_rows") or []
    assert len(projects) <= 3
    assert isinstance(matrix_rows, list)
    assert len(matrix_rows) >= 1 or table.get("insufficient_evidence") is True
