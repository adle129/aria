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
