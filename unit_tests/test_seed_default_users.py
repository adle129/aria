"""Tests for seed_default_users helper."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base
from app.models.user import USER_ROLE_KB_ADMIN, USER_ROLE_QUOTE_ENGINEER, User
from app.repositories.user_repository import UserRepository


@pytest.fixture
def auth_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[User.__table__])
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def _load_seed_module():
    path = Path(__file__).resolve().parents[1] / "backend" / "scripts" / "seed_default_users.py"
    spec = importlib.util.spec_from_file_location("seed_default_users", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_seed_default_users_creates_admin_and_engineer(auth_db, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("JWT_SECRET", "test-secret-key")
    get_settings.cache_clear()
    mod = _load_seed_module()

    lines = mod.seed_default_users(
        admin_username="admin",
        admin_password="admin123",
        admin_display_name="系统管理员",
        engineer_username="engineer",
        engineer_password="engineer123",
        engineer_display_name="报价工程师",
        db=auth_db,
    )
    assert any(line.startswith("created\tadmin\t") for line in lines)
    assert any(line.startswith("created\tengineer\t") for line in lines)

    repo = UserRepository(auth_db)
    admin = repo.get_by_username("admin")
    eng = repo.get_by_username("engineer")
    assert admin is not None and admin.role == USER_ROLE_KB_ADMIN
    assert eng is not None and eng.role == USER_ROLE_QUOTE_ENGINEER


def test_seed_default_users_idempotent(auth_db, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("JWT_SECRET", "test-secret-key")
    get_settings.cache_clear()
    mod = _load_seed_module()

    kwargs = dict(
        admin_username="admin",
        admin_password="admin123",
        admin_display_name="系统管理员",
        engineer_username="engineer",
        engineer_password="engineer123",
        engineer_display_name="报价工程师",
        db=auth_db,
    )
    mod.seed_default_users(**kwargs)
    lines = mod.seed_default_users(**kwargs)
    assert all(line.startswith("exists\t") for line in lines)
