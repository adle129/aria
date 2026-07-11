import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base
from app.models.engagement import Engagement
from app.services.engagement_audit_service import EngagementAuditService
from app.services.engagement_content_hash import compute_engagement_content_hash

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
