import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import Base, get_db
from app.main import app


@pytest.fixture
def debug_client(upload_dir, monkeypatch):
    monkeypatch.setenv("ARIA_UI_PROFILE", "dev")
    monkeypatch.setenv("KB_DEBUG_ENABLED", "true")
    monkeypatch.setenv("MOCK_RAG", "false")
    get_settings.cache_clear()

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.models.project import Project
    from app.models.rfq_task import RFQTask

    Base.metadata.create_all(bind=engine, tables=[Project.__table__, RFQTask.__table__])
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_kb_debug_disabled_returns_404(client):
    resp = client.get("/api/v1/knowledge/debug/status")
    assert resp.status_code == 404


def test_kb_debug_status_when_enabled(debug_client):
    resp = debug_client.get("/api/v1/knowledge/debug/status")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["kb_debug_enabled"] is True
    assert "corpus_path" in data


def test_kb_debug_list_files(debug_client):
    resp = debug_client.get("/api/v1/knowledge/debug/files")
    assert resp.status_code == 200
    assert "items" in resp.json()["data"]


def test_kb_debug_feedback(debug_client, tmp_path, monkeypatch):
    monkeypatch.setenv("FEEDBACK_PATH", str(tmp_path / "fb.jsonl"))
    get_settings.cache_clear()
    resp = debug_client.post(
        "/api/v1/knowledge/debug/feedback",
        json={"feedback_type": "chunk_ok", "chunk_id": "test-chunk"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["feedback_type"] == "chunk_ok"


def test_kb_debug_feedback_invalid_type(debug_client):
    resp = debug_client.post(
        "/api/v1/knowledge/debug/feedback",
        json={"feedback_type": "invalid_type"},
    )
    assert resp.status_code == 400


def test_health_includes_kb_debug_fields(client, monkeypatch):
    monkeypatch.setenv("ARIA_UI_PROFILE", "dev")
    monkeypatch.setenv("KB_DEBUG_ENABLED", "true")
    get_settings.cache_clear()
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["kb_debug_enabled"] is True
    assert body["aria_ui_profile"] == "dev"
    get_settings.cache_clear()
