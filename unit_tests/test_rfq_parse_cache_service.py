from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import Base
from app.models.rfq_parse_cache import RfqParseCache
from app.services.rfq_parse_cache_service import (
    PARSER_VERSION,
    RfqParseCacheService,
    build_cache_key,
    cache_entry_usable,
    sha256_file,
)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[RfqParseCache.__table__])
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def test_sha256_file_stable(tmp_path: Path):
    p = tmp_path / "a.docx"
    p.write_bytes(b"hello-rfq")
    assert sha256_file(p) == sha256_file(p)
    assert len(sha256_file(p)) == 64


def test_build_cache_key_includes_versions():
    key = build_cache_key(
        content_hash="abc",
        parser_version=PARSER_VERSION,
        prompt_version="v1",
        baseline_version="baseline-1",
    )
    assert key.startswith("abc:")
    assert PARSER_VERSION in key
    assert "v1" in key
    assert "baseline-1" in key


def test_cache_entry_usable_rejects_corrupt():
    assert cache_entry_usable({"modules": []}, {"items": []}) is True
    assert cache_entry_usable("bad", None) is False
    assert cache_entry_usable({"modules": []}, {"items": "nope"}) is False


def test_store_and_lookup_roundtrip(db_session, tmp_path: Path):
    p = tmp_path / "rfq.docx"
    p.write_bytes(b"same-bytes")
    svc = RfqParseCacheService(Settings(database_url="sqlite://", prompt_version="v1"))
    modules = {"project_name": "P", "modules": []}
    draft = {"baseline_version": "bv1", "items": [{"dimension_id": "d1", "in_scope": True}]}

    content_hash, hit_m, hit_d = svc.lookup(db_session, file_path=p, baseline_version="bv1")
    assert hit_m is None and hit_d is None

    svc.store(
        db_session,
        content_hash=content_hash,
        baseline_version="bv1",
        rfq_modules=modules,
        dimension_draft=draft,
    )
    _, hit_m, hit_d = svc.lookup(db_session, file_path=p, baseline_version="bv1")
    assert hit_m == modules
    assert hit_d == draft
    # deepcopy: mutating returned draft must not poison cache
    hit_d["items"].append({"dimension_id": "hack"})
    _, again_m, again_d = svc.lookup(db_session, file_path=p, baseline_version="bv1")
    assert len(again_d["items"]) == 1
    assert again_m == modules


def test_lookup_drops_corrupt_entry(db_session, tmp_path: Path):
    p = tmp_path / "rfq.docx"
    p.write_bytes(b"corrupt-case")
    svc = RfqParseCacheService(Settings(database_url="sqlite://", prompt_version="v1"))
    content_hash = sha256_file(p)
    key = build_cache_key(
        content_hash=content_hash,
        parser_version=PARSER_VERSION,
        prompt_version="v1",
        baseline_version="bv1",
    )
    db_session.add(
        RfqParseCache(
            cache_key=key,
            content_hash=content_hash,
            parser_version=PARSER_VERSION,
            prompt_version="v1",
            baseline_version="bv1",
            rfq_modules="not-a-dict",  # type: ignore[arg-type]
            dimension_draft=None,
        )
    )
    db_session.commit()

    _, modules, draft = svc.lookup(db_session, file_path=p, baseline_version="bv1")
    assert modules is None and draft is None
    assert db_session.scalar(select(func.count()).select_from(RfqParseCache)) == 0


def test_lookup_miss_on_baseline_version_change(db_session, tmp_path: Path):
    p = tmp_path / "rfq.docx"
    p.write_bytes(b"version-sensitive")
    svc = RfqParseCacheService(Settings(database_url="sqlite://", prompt_version="v1"))
    content_hash = sha256_file(p)
    svc.store(
        db_session,
        content_hash=content_hash,
        baseline_version="bv1",
        rfq_modules={"modules": []},
        dimension_draft={"items": []},
    )
    _, m, d = svc.lookup(db_session, file_path=p, baseline_version="bv2")
    assert m is None and d is None
