from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import Base
from app.models.rfq_task import RFQTask
from app.services.rfq_analysis_service import RFQAnalysisService

SEED = Path(__file__).resolve().parents[1] / "backend" / "data" / "config" / "dimension_baseline.v1.json"


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[RFQTask.__table__])
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def analysis_service():
    if not SEED.is_file():
        pytest.skip("seed baseline missing")
    return RFQAnalysisService(
        Settings(
            mock_llm=True,
            mock_rag=True,
            dimension_baseline_path=str(SEED),
            upload_path="./data/uploads",
        )
    )


def test_analyze_task_stops_at_dimension_review(db_session, analysis_service, monkeypatch, tmp_path):
    tmp_path.joinpath("mock.docx").write_bytes(b"mock")
    task = RFQTask(
        file_name="mock.docx",
        file_path=str(tmp_path / "mock.docx"),
        processing_status="queued",
    )
    db_session.add(task)
    db_session.commit()

    rfq_modules = {
        "project_name": "MEB Chassis",
        "platform_type": "MEB",
        "functions_in_scope": ["Chassis"],
    }
    monkeypatch.setattr(
        analysis_service.parse_service,
        "parse_rules_first",
        lambda _path: rfq_modules,
    )

    analysis_service.analyze_task(db_session, task.id)
    db_session.refresh(task)

    assert task.processing_status == "dimension_review"
    assert task.rfq_modules == rfq_modules
    assert task.dimension_draft is not None
    assert len(task.dimension_draft["items"]) >= 1
    assert task.comparison_table is None
    assert task.similar_projects is None


def test_confirm_dimensions_generates_matrix(db_session, analysis_service, monkeypatch):
    draft = analysis_service.dimension_match.match_rfq_to_baseline(
        {
            "project_name": "MEB Chassis MacPherson",
            "functions_in_scope": ["Chassis"],
            "modules": [
                {
                    "function": "Chassis",
                    "module_name": "Front suspension MacPherson layout",
                    "deliverables": ["Suspension CAD"],
                }
            ],
        }
    )
    task = RFQTask(
        file_name="mock.docx",
        file_path="/tmp/mock.docx",
        processing_status="dimension_review",
        rfq_modules={"project_name": "MEB", "functions_in_scope": ["Chassis"], "platform_type": "MEB"},
        dimension_draft=draft,
    )
    db_session.add(task)
    db_session.commit()

    analysis_service.confirm_dimensions(db_session, task, {})
    db_session.refresh(task)

    assert task.processing_status == "completed"
    assert task.comparison_table is not None
    assert task.comparison_table.get("matrix_rows")
    assert task.similar_projects is not None


def test_confirm_dimensions_marks_failed_on_lease_timeout(
    db_session, analysis_service, monkeypatch
):
    from app.services.ollama_concurrency import OllamaLeaseTimeout

    draft = analysis_service.dimension_match.match_rfq_to_baseline(
        {
            "project_name": "MEB Chassis",
            "functions_in_scope": ["Chassis"],
            "modules": [
                {
                    "function": "Chassis",
                    "module_name": "Front suspension",
                    "deliverables": ["CAD"],
                }
            ],
        }
    )
    task = RFQTask(
        file_name="mock.docx",
        file_path="/tmp/mock.docx",
        processing_status="dimension_review",
        rfq_modules={"project_name": "MEB", "functions_in_scope": ["Chassis"]},
        dimension_draft=draft,
    )
    db_session.add(task)
    db_session.commit()

    def boom(*_args, **_kwargs):
        raise OllamaLeaseTimeout("Ollama resource wait timed out for rfq")

    monkeypatch.setattr(
        analysis_service.rag, "search_similar_projects", boom
    )

    with pytest.raises(OllamaLeaseTimeout):
        analysis_service.confirm_dimensions(db_session, task, {})
    db_session.refresh(task)

    assert task.processing_status == "failed"
    assert task.progress == "55"
    assert "繁忙" in (task.status_message or "")
    assert task.error_msg


def test_confirm_dimensions_rejects_without_in_scope(db_session, analysis_service):
    draft = analysis_service.dimension_match.match_rfq_to_baseline(
        {"project_name": "Interior only", "functions_in_scope": ["Interior"]}
    )
    for item in draft["items"]:
        item["in_scope"] = False
    task = RFQTask(
        file_name="mock.docx",
        file_path="/tmp/mock.docx",
        processing_status="dimension_review",
        rfq_modules={"project_name": "Interior"},
        dimension_draft=draft,
    )
    db_session.add(task)
    db_session.commit()

    with pytest.raises(ValueError, match="in_scope"):
        analysis_service.confirm_dimensions(db_session, task, {})


def test_update_dimension_draft_only_in_review(db_session, analysis_service):
    draft = analysis_service.dimension_match.match_rfq_to_baseline(
        {"project_name": "MEB", "functions_in_scope": ["Chassis"]}
    )
    task = RFQTask(
        file_name="mock.docx",
        file_path="/tmp/mock.docx",
        processing_status="completed",
        rfq_modules={"project_name": "MEB"},
        dimension_draft=draft,
    )
    db_session.add(task)
    db_session.commit()

    with pytest.raises(ValueError, match="dimension_draft"):
        analysis_service.update_task_review(
            db_session,
            task,
            dimension_draft={"items": draft["items"]},
        )


def test_recover_orphaned_confirm_phase_rolls_back_to_review(db_session, analysis_service):
    from datetime import datetime, timedelta, timezone

    draft = analysis_service.dimension_match.match_rfq_to_baseline(
        {"project_name": "MEB", "functions_in_scope": ["Chassis"]}
    )
    task = RFQTask(
        file_name="stuck.docx",
        file_path="/tmp/stuck.docx",
        processing_status="retrieving",
        progress="55",
        status_message="正在检索相似历史项目...",
        rfq_modules={"project_name": "MEB"},
        dimension_draft=draft,
        updated_at=datetime.now(timezone.utc) - timedelta(minutes=20),
    )
    db_session.add(task)
    db_session.commit()

    svc = RFQAnalysisService(
        Settings(
            mock_llm=True,
            mock_rag=True,
            dimension_baseline_path=str(SEED),
            task_job_stale_seconds=900,
        )
    )
    recovered = svc.recover_orphaned_confirm_phase(db_session, task)
    assert recovered.processing_status == "dimension_review"
    assert recovered.progress == "40"
    assert "重新确认" in (recovered.status_message or "")


def test_recover_orphaned_confirm_phase_skips_fresh_task(db_session, analysis_service):
    from datetime import datetime, timezone

    task = RFQTask(
        file_name="fresh.docx",
        file_path="/tmp/fresh.docx",
        processing_status="retrieving",
        progress="55",
        rfq_modules={"project_name": "MEB"},
        dimension_draft={"items": [{"in_scope": True}]},
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    db_session.commit()

    svc = RFQAnalysisService(Settings(mock_llm=True, mock_rag=True, task_job_stale_seconds=900))
    same = svc.recover_orphaned_confirm_phase(db_session, task)
    assert same.processing_status == "retrieving"
