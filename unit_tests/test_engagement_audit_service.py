import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base
from app.models.engagement import Engagement
from app.repositories.engagement_repository import EngagementRepository
from app.services.engagement_audit_service import EngagementAuditService
from app.services.engagement_content_hash import compute_engagement_content_hash
from app.services.engagement_ingest_service import EngagementIngestService
from app.services.engagement_manifest_service import resolve_manifest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RFQ = ROOT / "samples" / "rfq" / "mock_chassis_rfq.docx"


@pytest.fixture
def audit_session(tmp_path, monkeypatch):
    kb = tmp_path / "kb"
    kb.mkdir()
    monkeypatch.setenv("KNOWLEDGE_BASE_PATH", str(kb))
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[Engagement.__table__])
    session = sessionmaker(bind=engine)()
    yield session, kb
    session.close()
    get_settings.cache_clear()


def test_content_hash_is_stable_for_same_folder(tmp_path):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")
    folder = tmp_path / "eng"
    folder.mkdir()
    shutil.copyfile(SAMPLE_RFQ, folder / "RFQ.docx")
    first = compute_engagement_content_hash(folder)
    second = compute_engagement_content_hash(folder)
    assert first == second
    assert len(first) == 64


def test_record_upload_persists_audit_fields(audit_session):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")
    session, kb = audit_session
    folder = kb / "demo_eng"
    folder.mkdir()
    shutil.copyfile(SAMPLE_RFQ, folder / "RFQ.docx")
    settings = get_settings()
    service = EngagementAuditService(settings, session)
    row = service.record_upload(folder, uploaded_by="user-1", tier="copper")
    assert row.id == "demo_eng"
    assert row.uploaded_by == "user-1"
    assert row.tier == "copper"
    assert row.content_hash


def test_record_upload_preserves_last_indexed_at(audit_session):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")
    session, kb = audit_session
    folder = kb / "demo_eng"
    folder.mkdir()
    shutil.copyfile(SAMPLE_RFQ, folder / "RFQ.docx")
    settings = get_settings()
    service = EngagementAuditService(settings, session)
    prior = datetime(2026, 1, 15, 8, 0, 0, tzinfo=UTC)
    first = service.record_upload(folder, uploaded_by="user-1", tier="copper")
    first.last_indexed_at = prior
    first.index_status = "indexed"
    session.commit()

    row = service.record_upload(folder, uploaded_by="user-2", tier="copper")
    assert row.index_status == "pending"
    assert row.uploaded_by == "user-2"
    assert row.last_indexed_at is not None
    assert row.last_indexed_at.replace(tzinfo=UTC) == prior


def test_persist_engagement_indexed_bumps_last_indexed_at(audit_session):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")
    session, kb = audit_session
    folder = kb / "demo_eng"
    folder.mkdir()
    shutil.copyfile(SAMPLE_RFQ, folder / "RFQ.docx")
    settings = get_settings()
    audit = EngagementAuditService(settings, session)
    prior = datetime(2026, 1, 15, 8, 0, 0, tzinfo=UTC)
    row = audit.record_upload(folder, uploaded_by="user-1", tier="copper")
    row.last_indexed_at = prior
    row.index_status = "indexed"
    session.commit()

    ingest = EngagementIngestService(settings, session)
    manifest = resolve_manifest(folder)
    ingest._persist_engagement(manifest, folder, index_status="pending")
    pending = EngagementRepository(session).get_by_id("demo_eng")
    assert pending is not None
    assert pending.index_status == "pending"
    assert pending.last_indexed_at is not None
    assert pending.last_indexed_at.replace(tzinfo=UTC) == prior

    before = datetime.now(UTC)
    ingest._persist_engagement(manifest, folder, index_status="indexed")
    indexed = EngagementRepository(session).get_by_id("demo_eng")
    assert indexed is not None
    assert indexed.index_status == "indexed"
    assert indexed.last_indexed_at is not None
    indexed_at = indexed.last_indexed_at.replace(tzinfo=UTC)
    assert indexed_at >= before - timedelta(seconds=1)
    assert indexed_at != prior
