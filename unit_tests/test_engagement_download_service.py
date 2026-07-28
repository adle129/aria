"""Unit tests for R1-CHG06 engagement source download + audit."""

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
from app.services.engagement_download_service import (
    EngagementDownloadNotFound,
    EngagementDownloadService,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RFQ = ROOT / "samples" / "rfq" / "mock_chassis_rfq.docx"


@pytest.fixture
def download_session(tmp_path, monkeypatch):
    kb = tmp_path / "knowledge_base"
    kb.mkdir()
    audit = tmp_path / "audit" / "downloads.jsonl"
    monkeypatch.setenv("KNOWLEDGE_BASE_PATH", str(kb))
    monkeypatch.setenv("KNOWLEDGE_DOWNLOAD_AUDIT_PATH", str(audit))
    monkeypatch.setenv("MANPOWER_BASELINES_PATH", str(tmp_path / "baselines.json"))
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[Engagement.__table__])
    session = sessionmaker(bind=engine)()
    yield session, kb, audit
    session.close()
    get_settings.cache_clear()


def _seed(session, kb: Path, eng_id: str = "dl_eng"):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")
    folder = kb / eng_id
    folder.mkdir()
    shutil.copyfile(SAMPLE_RFQ, folder / "RFQ.docx")
    settings = get_settings()
    EngagementAuditService(settings, session).record_upload(
        folder, uploaded_by="tester", tier="copper"
    )
    session.commit()
    return settings


def test_resolve_rfq_and_audit(download_session):
    session, kb, audit = download_session
    settings = _seed(session, kb)
    service = EngagementDownloadService(settings, session)
    resolved = service.resolve_document("dl_eng", doc_type="rfq")
    assert resolved["path"].is_file()
    assert resolved["filename"]
    service.append_audit(
        engagement_id="dl_eng",
        doc_type="rfq",
        filename=resolved["filename"],
        user_id="u1",
        username="alice",
        task_id="task-9",
    )
    assert audit.is_file()
    line = audit.read_text(encoding="utf-8").strip()
    assert "dl_eng" in line
    assert "alice" in line
    assert "task-9" in line


def test_resolve_missing_doc_type(download_session):
    session, kb, _audit = download_session
    settings = _seed(session, kb)
    service = EngagementDownloadService(settings, session)
    with pytest.raises(EngagementDownloadNotFound, match="qa"):
        service.resolve_document("dl_eng", doc_type="qa")


def test_download_filename_includes_task_id():
    assert (
        EngagementDownloadService.download_filename("RFQ.docx", task_id="abc-123")
        == "RFQ__task-abc-123.docx"
    )
    assert EngagementDownloadService.download_filename("RFQ.docx") == "RFQ.docx"
    assert (
        EngagementDownloadService.download_filename(
            "RFQ_模板.doc",
            task_id="t-9",
            engagement_id="test",
            doc_type="rfq",
        )
        == "test_rfq__task-t-9.doc"
    )
    assert (
        EngagementDownloadService.download_filename("RFQ.docx", task_id="../x")
        == "RFQ__task-__x.docx"
    )
