"""R1-KH13 integration gates (PostgreSQL + mocked Ollama adapters)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.config import Settings
from app.services.disk_guard_service import DiskCapacityError, DiskGuardService, DiskUsage
from app.services.engagement_upload_service import EngagementUploadError


def test_disk_guard_blocks_when_usage_above_threshold(tmp_path, monkeypatch):
    monkeypatch.setenv("DISK_WRITE_PROTECT_PERCENT", "90")
    settings = Settings(
        knowledge_base_path=str(tmp_path / "kb"),
        disk_write_protect_percent=90,
    )
    guard = DiskGuardService(
        settings,
        usage_provider=lambda _path: DiskUsage(100, 95, 5),
    )
    with pytest.raises(DiskCapacityError):
        guard.assert_writable(required_bytes=1)


def test_zip_traversal_rejected(tmp_path):
    import zipfile

    settings = Settings(knowledge_base_path=str(tmp_path / "kb"))
    from app.services.engagement_upload_service import (
        EngagementUploadService,
        _safe_extract_zip,
    )

    service = EngagementUploadService(settings)
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../RFQ.docx", b"bad")
    with pytest.raises(EngagementUploadError):
        _safe_extract_zip(archive, tmp_path / "out", settings)


def test_incremental_skip_returns_without_embedding(tmp_path, monkeypatch):
    monkeypatch.setenv("MOCK_RAG", "false")
    kb = tmp_path / "kb" / "demo"
    kb.mkdir(parents=True)
    (kb / "manifest.json").write_text(
        '{"engagement_id":"demo","project_name":"Demo","documents":[]}',
        encoding="utf-8",
    )
    (kb / "RFQ.docx").write_bytes(b"fake")

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from app.database import Base
    from app.models.engagement import Engagement
    from app.services.engagement_content_hash import compute_engagement_content_hash
    from app.services.engagement_ingest_service import EngagementIngestService

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[Engagement.__table__])
    session = sessionmaker(bind=engine)()
    settings = Settings(knowledge_base_path=str(tmp_path / "kb"), mock_rag=False)
    content_hash = compute_engagement_content_hash(kb)
    session.add(
        Engagement(
            id="demo",
            project_name="Demo",
            folder_path="demo",
            manifest={},
            index_status="indexed",
            content_hash=content_hash,
            tier="copper",
        )
    )
    session.commit()

    service = EngagementIngestService(settings, session)
    with (
        patch(
            "app.services.engagement_ingest_service.KnowledgeIndexService"
        ) as mock_index_cls,
        patch.object(
            EngagementIngestService,
            "prepare_engagement",
            side_effect=AssertionError("should not parse unchanged engagement"),
        ),
    ):
        mock_index_cls.return_value._generations.get_active_id.return_value = "active-gen"
        result = service.import_all(mode="incremental")

    assert result["skipped"] == 1
    assert result["new_chunks"] == 0
