"""Unit tests for R1-CHG13 single-document upsert."""

import io
import shutil
from pathlib import Path

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base
from app.models.engagement import Engagement
from app.repositories.engagement_repository import EngagementRepository
from app.services.engagement_audit_service import EngagementAuditService
from app.services.engagement_document_service import (
    EngagementDocumentConflict,
    EngagementDocumentError,
    EngagementDocumentNotFound,
    EngagementDocumentService,
)
from app.services.engagement_manifest_service import resolve_manifest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RFQ = ROOT / "samples" / "rfq" / "mock_chassis_rfq.docx"


def _xlsx_bytes(sheet_title: str = "Sheet1") -> bytes:
    wb = Workbook()
    wb.active.title = sheet_title
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.fixture
def doc_session(tmp_path, monkeypatch):
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


def _seed_rfq_engagement(session, kb: Path, eng_id: str = "chg13_eng"):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")
    folder = kb / eng_id
    folder.mkdir()
    shutil.copyfile(SAMPLE_RFQ, folder / "RFQ.docx")
    settings = get_settings()
    EngagementAuditService(settings, session).record_upload(
        folder, uploaded_by="tester", tier="copper"
    )
    row = EngagementRepository(session).get_by_id(eng_id)
    assert row is not None
    row.index_status = "indexed"
    session.commit()
    return settings, folder


def test_upsert_qa_updates_manifest_and_sets_pending(doc_session):
    session, kb = doc_session
    settings, folder = _seed_rfq_engagement(session, kb)
    service = EngagementDocumentService(settings, session)

    result = service.upsert_document(
        "chg13_eng",
        doc_type="qa",
        filename="客户问答.xlsx",
        content=_xlsx_bytes(),
        replace=True,
    )
    assert result["engagement_id"] == "chg13_eng"
    assert result["doc_type"] == "qa"
    assert result["needs_reindex"] is True
    assert result["index_status"] == "pending"
    assert result["path"].startswith("Q_A_")
    assert (folder / result["path"]).is_file()

    manifest = resolve_manifest(folder)
    types = {d.doc_type for d in manifest.documents}
    assert "rfq" in types and "qa" in types

    row = EngagementRepository(session).get_by_id("chg13_eng")
    assert row is not None
    assert row.index_status == "pending"
    assert row.tier in {"silver", "gold", "copper"}


def test_replace_rfq_keeps_single_doc_type(doc_session):
    session, kb = doc_session
    settings, folder = _seed_rfq_engagement(session, kb)
    service = EngagementDocumentService(settings, session)

    first = service.upsert_document(
        "chg13_eng",
        doc_type="rfq",
        filename="RFQ_v2.docx",
        content=SAMPLE_RFQ.read_bytes(),
        replace=True,
    )
    second = service.upsert_document(
        "chg13_eng",
        doc_type="rfq",
        filename="RFQ_v3.docx",
        content=SAMPLE_RFQ.read_bytes(),
        replace=True,
    )
    assert first["path"] == second["path"]
    rfq_docs = [d for d in resolve_manifest(folder).documents if d.doc_type == "rfq"]
    assert len(rfq_docs) == 1


def test_replace_false_conflicts(doc_session):
    session, kb = doc_session
    settings, _folder = _seed_rfq_engagement(session, kb)
    service = EngagementDocumentService(settings, session)
    with pytest.raises(EngagementDocumentConflict):
        service.upsert_document(
            "chg13_eng",
            doc_type="rfq",
            filename="RFQ_dup.docx",
            content=SAMPLE_RFQ.read_bytes(),
            replace=False,
        )


def test_bad_suffix_and_missing_project(doc_session):
    session, kb = doc_session
    settings, _folder = _seed_rfq_engagement(session, kb)
    service = EngagementDocumentService(settings, session)
    with pytest.raises(EngagementDocumentError, match="仅支持"):
        service.upsert_document(
            "chg13_eng",
            doc_type="qa",
            filename="bad.docx",
            content=b"not-xlsx",
        )
    with pytest.raises(EngagementDocumentNotFound):
        service.upsert_document(
            "does_not_exist",
            doc_type="rfq",
            filename="RFQ.docx",
            content=SAMPLE_RFQ.read_bytes(),
        )


def test_quote_manpower_naming(doc_session):
    session, kb = doc_session
    settings, folder = _seed_rfq_engagement(session, kb)
    service = EngagementDocumentService(settings, session)
    result = service.upsert_document(
        "chg13_eng",
        doc_type="quote_manpower",
        filename="baseline.xlsx",
        content=_xlsx_bytes("报价"),
    )
    assert "人力" in result["path"] or "报价" in result["path"]
    assert (folder / result["path"]).is_file()
