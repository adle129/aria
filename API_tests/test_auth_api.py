"""API tests for R1-AUTH01–03 (login, me, RFQ owner isolation)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models.user import USER_ROLE_KB_ADMIN, USER_ROLE_QUOTE_ENGINEER
from app.services.auth_service import AuthService


@pytest.fixture
def auth_client(upload_dir, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("JWT_SECRET", "test-secret-key")
    get_settings.cache_clear()

    from fastapi.testclient import TestClient

    from app.models.engagement import Engagement
    from app.models.project import Project
    from app.models.rfq_task import RFQTask
    from app.models.task_job import TaskJob
    from app.models.user import User

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

    settings = get_settings()
    rfq_module.analysis_service.settings = settings
    rfq_module.quote_service.settings = settings
    rfq_module.artifact_service.settings = settings

    monkeypatch.setattr(database_module, "engine", engine)
    monkeypatch.setattr(database_module, "SessionLocal", session_factory)

    db = session_factory()
    AuthService(settings).create_user(
        db,
        username="eng01",
        password="pass123",
        display_name="工程师甲",
        role=USER_ROLE_QUOTE_ENGINEER,
    )
    AuthService(settings).create_user(
        db,
        username="eng02",
        password="pass456",
        display_name="工程师乙",
        role=USER_ROLE_QUOTE_ENGINEER,
    )
    AuthService(settings).create_user(
        db,
        username="kbadmin",
        password="admin123",
        display_name="库管",
        role=USER_ROLE_KB_ADMIN,
    )
    db.close()

    app.dependency_overrides[get_db] = override_get_db
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def _login(client, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def test_login_success_and_me(auth_client):
    token = _login(auth_client, "eng01", "pass123")
    me = auth_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    data = me.json()["data"]
    assert data["username"] == "eng01"
    assert data["display_name"] == "工程师甲"


def test_login_wrong_password(auth_client):
    response = auth_client.post(
        "/api/v1/auth/login",
        json={"username": "eng01", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["msg"] == "用户名或密码错误"


def test_rfq_requires_auth_when_enabled(auth_client):
    response = auth_client.get("/api/v1/rfq/tasks")
    assert response.status_code == 401
    assert response.json()["msg"] == "未登录"


def test_rfq_owner_isolation(auth_client, sample_rfq_bytes):
    token_a = _login(auth_client, "eng01", "pass123")
    token_b = _login(auth_client, "eng02", "pass456")

    upload = auth_client.post(
        "/api/v1/rfq/upload",
        files={
            "file": (
                "mock_chassis_rfq.docx",
                sample_rfq_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert upload.status_code == 200
    task_id = upload.json()["data"]["task_id"]

    own = auth_client.get(
        f"/api/v1/rfq/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert own.status_code == 200

    other = auth_client.get(
        f"/api/v1/rfq/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert other.status_code == 404
    assert other.json()["msg"] == "任务 ID 不存在"

    listed = auth_client.get(
        "/api/v1/rfq/tasks",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert listed.status_code == 200
    assert all(item["task_id"] != task_id for item in listed.json()["data"])


def test_logout_ok(auth_client):
    token = _login(auth_client, "eng01", "pass123")
    response = auth_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["ok"] is True


def test_engineer_cannot_reindex(auth_client, monkeypatch):
    monkeypatch.setenv("MOCK_RAG", "false")
    get_settings.cache_clear()
    token = _login(auth_client, "eng01", "pass123")
    resp = auth_client.post(
        "/api/v1/knowledge/reindex",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
    assert resp.json()["msg"] == "需要资料库管理员权限"


def test_kb_admin_can_reindex(auth_client, monkeypatch):
    monkeypatch.setenv("MOCK_RAG", "false")
    get_settings.cache_clear()

    class FakeIngest:
        def __init__(self, settings, db=None):
            pass

        def import_all(self):
            return {
                "new_documents": 0,
                "new_chunks": 0,
                "skipped": 0,
                "failed_files": [],
                "last_import_at": "2026-07-07T00:00:00Z",
                "engagements_indexed": 0,
                "doc_type_counts": {},
            }

    monkeypatch.setattr("app.api.v1.knowledge.EngagementIngestService", FakeIngest)
    token = _login(auth_client, "kbadmin", "admin123")
    resp = auth_client.post(
        "/api/v1/knowledge/reindex",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_health_includes_auth_enabled(auth_client):
    resp = auth_client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["auth_enabled"] is True
