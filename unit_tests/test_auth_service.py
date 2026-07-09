import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base
from app.models.user import USER_ROLE_QUOTE_ENGINEER, USER_ROLE_KB_ADMIN
from app.services.auth_service import AuthService


@pytest.fixture
def auth_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.models.user import User

    Base.metadata.create_all(bind=engine, tables=[User.__table__])
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def auth_service(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-key")
    get_settings.cache_clear()
    return AuthService(get_settings())


def test_hash_and_verify_password(auth_service):
    hashed = auth_service.hash_password("secret123")
    assert auth_service.verify_password("secret123", hashed)
    assert not auth_service.verify_password("wrong", hashed)


def test_create_user_and_authenticate(auth_db, auth_service):
    user = auth_service.create_user(
        auth_db,
        username="eng01",
        password="pass123",
        display_name="张工",
        role=USER_ROLE_QUOTE_ENGINEER,
    )
    assert user.id
    assert user.role == USER_ROLE_QUOTE_ENGINEER

    ok = auth_service.authenticate(auth_db, "eng01", "pass123")
    assert ok is not None
    assert ok.username == "eng01"

    assert auth_service.authenticate(auth_db, "eng01", "bad") is None
    assert auth_service.authenticate(auth_db, "missing", "pass123") is None


def test_create_user_duplicate_username(auth_db, auth_service):
    auth_service.create_user(
        auth_db,
        username="dup",
        password="pass123",
        display_name="A",
    )
    with pytest.raises(ValueError, match="用户名已存在"):
        auth_service.create_user(
            auth_db,
            username="dup",
            password="pass123",
            display_name="B",
        )


def test_jwt_roundtrip(auth_db, auth_service):
    user = auth_service.create_user(
        auth_db,
        username="admin01",
        password="pass123",
        display_name="Admin",
        role=USER_ROLE_KB_ADMIN,
    )
    token, expires_at = auth_service.create_access_token(user)
    assert expires_at > __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    resolved = auth_service.resolve_user_from_token(auth_db, token)
    assert resolved is not None
    assert resolved.id == user.id

    assert auth_service.resolve_user_from_token(auth_db, "bad.token.here") is None


def test_change_password(auth_db, auth_service):
    user = auth_service.create_user(
        auth_db, username="pwchange", password="old123!", display_name="改密者"
    )
    auth_service.change_password(auth_db, user, "old123!", "new456!")
    assert auth_service.authenticate(auth_db, "pwchange", "new456!") is not None
    assert auth_service.authenticate(auth_db, "pwchange", "old123!") is None


def test_change_password_wrong_old(auth_db, auth_service):
    user = auth_service.create_user(
        auth_db, username="pwwrong", password="real123", display_name="错误测试"
    )
    with pytest.raises(ValueError, match="原密码错误"):
        auth_service.change_password(auth_db, user, "wrong!", "newpass")


def test_list_and_update_users(auth_db, auth_service):
    auth_service.create_user(auth_db, username="u1", password="p1", display_name="用户一")
    auth_service.create_user(
        auth_db, username="u2", password="p2", display_name="用户二", role=USER_ROLE_KB_ADMIN
    )
    users = auth_service.list_users(auth_db)
    assert len(users) == 2

    updated = auth_service.update_user(
        auth_db, users[0].id, display_name="改名后", is_active=False
    )
    assert updated.display_name == "改名后"
    assert updated.is_active is False


def test_update_user_not_found(auth_db, auth_service):
    with pytest.raises(ValueError, match="用户不存在"):
        auth_service.update_user(auth_db, "nonexistent-id")


def test_user_detail_includes_is_active(auth_db, auth_service):
    user = auth_service.create_user(
        auth_db, username="detail_u", password="p", display_name="详情"
    )
    detail = auth_service.user_detail(user)
    assert detail["is_active"] is True
    assert "created_at" in detail
    assert "password_hash" not in detail


def test_user_public(auth_db, auth_service):
    user = auth_service.create_user(
        auth_db,
        username="pub",
        password="pass123",
        display_name="公开名",
    )
    payload = auth_service.user_public(user)
    assert payload["username"] == "pub"
    assert payload["display_name"] == "公开名"
    assert "password" not in payload
