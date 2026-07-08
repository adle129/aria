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
    token = auth_service.create_access_token(user)
    resolved = auth_service.resolve_user_from_token(auth_db, token)
    assert resolved is not None
    assert resolved.id == user.id

    assert auth_service.resolve_user_from_token(auth_db, "bad.token.here") is None


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
