"""Unit tests for R1-CHG14 engagement trash + hard refs."""

import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.database import Base
from app.models.engagement import Engagement
from app.models.rfq_task import RFQTask
from app.services.engagement_audit_service import EngagementAuditService
from app.services.engagement_reference_service import (
    EngagementReferenceService,
    can_soft_delete_engagement,
)
from app.services.engagement_trash_service import (
    EngagementTrashConflict,
    EngagementTrashService,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_RFQ = ROOT / "samples" / "rfq" / "mock_chassis_rfq.docx"


@pytest.fixture
def trash_session(tmp_path, monkeypatch):
    kb = tmp_path / "knowledge_base"
    kb.mkdir()
    monkeypatch.setenv("KNOWLEDGE_BASE_PATH", str(kb))
    monkeypatch.setenv("MANPOWER_BASELINES_PATH", str(tmp_path / "baselines.json"))
    get_settings.cache_clear()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine, tables=[Engagement.__table__, RFQTask.__table__]
    )
    session = sessionmaker(bind=engine)()
    yield session, kb, tmp_path
    session.close()
    get_settings.cache_clear()


def _seed(session, kb: Path, eng_id: str = "trash_eng"):
    if not SAMPLE_RFQ.exists():
        pytest.skip("sample rfq missing")
    folder = kb / eng_id
    folder.mkdir()
    shutil.copyfile(SAMPLE_RFQ, folder / "RFQ.docx")
    settings = get_settings()
    row = EngagementAuditService(settings, session).record_upload(
        folder, uploaded_by="tester", tier="copper"
    )
    row.index_status = "failed"
    session.commit()
    return settings


def test_can_soft_delete_policy():
    assert can_soft_delete_engagement(tier="copper", index_status="failed", has_hard_refs=False)
    assert not can_soft_delete_engagement(
        tier="gold", index_status="indexed", has_hard_refs=False, document_count=3
    )
    assert can_soft_delete_engagement(
        tier="gold", index_status="indexed", has_hard_refs=False, document_count=0
    )
    assert not can_soft_delete_engagement(
        tier="copper", index_status="failed", has_hard_refs=True
    )


def test_hard_ref_from_function_source_map(trash_session):
    session, kb, _tmp = trash_session
    _seed(session, kb)
    session.add(
        RFQTask(
            id="task-1",
            file_name="a.docx",
            file_path="/tmp/a.docx",
            archived=False,
            function_source_map={"PM": "trash_eng", "BIW": None},
        )
    )
    session.add(
        RFQTask(
            id="task-2",
            file_name="b.docx",
            file_path="/tmp/b.docx",
            archived=False,
            comparison_table={
                "projects": [{"engagement_id": "trash_eng", "project_name": "X"}]
            },
        )
    )
    session.add(
        RFQTask(
            id="task-archived",
            file_name="c.docx",
            file_path="/tmp/c.docx",
            archived=True,
            function_source_map={"PM": "trash_eng"},
        )
    )
    session.commit()
    refs = EngagementReferenceService(session).list_hard_ref_task_ids("trash_eng")
    assert refs == ["task-1", "task-2"]
    mapped = EngagementReferenceService(session).engagement_ref_task_ids()
    assert mapped["trash_eng"] == ["task-1", "task-2"]
    assert "other_eng" not in mapped


def test_soft_delete_moves_to_trash_and_blocks_refs(trash_session):
    session, kb, tmp = trash_session
    settings = _seed(session, kb)
    service = EngagementTrashService(settings, session)

    result = service.soft_delete("trash_eng", deleted_by="admin-1")
    assert result["moved_to_trash"] is True
    assert result["purge_after"]
    assert not (kb / "trash_eng").exists()
    trash_dir = tmp / "trash" / "quoting" / "trash_eng"
    assert trash_dir.is_dir()
    assert (trash_dir / "trash_meta.json").is_file()
    assert session.get(Engagement, "trash_eng") is None

    # Restore then set gold+indexed → policy block
    restored = service.restore("trash_eng", restored_by="admin-1")
    assert restored["restored"] is True
    assert (kb / "trash_eng").is_dir()
    row = session.get(Engagement, "trash_eng")
    assert row is not None
    row.tier = "gold"
    row.index_status = "indexed"
    session.commit()
    with pytest.raises(EngagementTrashConflict, match="一键删除"):
        service.soft_delete("trash_eng")


def test_soft_delete_conflict_when_referenced(trash_session):
    session, kb, _tmp = trash_session
    settings = _seed(session, kb)
    session.add(
        RFQTask(
            id="task-ref",
            file_name="b.docx",
            file_path="/tmp/b.docx",
            archived=False,
            comparison_table={
                "projects": [{"engagement_id": "trash_eng", "project_name": "X"}]
            },
        )
    )
    session.commit()
    service = EngagementTrashService(settings, session)
    with pytest.raises(EngagementTrashConflict) as exc:
        service.soft_delete("trash_eng")
    assert "task-ref" in exc.value.ref_task_ids
