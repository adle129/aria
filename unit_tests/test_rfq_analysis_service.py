from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import Base
from app.models.rfq_parse_cache import RfqParseCache
from app.models.rfq_task import RFQTask
from app.models.task_job import TaskJob
from app.services.rfq_analysis_service import RFQAnalysisService

SEED = Path(__file__).resolve().parents[1] / "backend" / "data" / "config" / "dimension_baseline.v1.json"


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[RFQTask.__table__, TaskJob.__table__, RfqParseCache.__table__],
    )
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


@pytest.fixture
def analysis_service(tmp_path):
    if not SEED.is_file():
        pytest.skip("seed baseline missing")
    return RFQAnalysisService(
        Settings(
            mock_llm=True,
            mock_rag=True,
            dimension_baseline_path=str(SEED),
            upload_path=str(tmp_path / "uploads"),
            prompt_version="v1",
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
        lambda _path, **kwargs: rfq_modules,
    )

    analysis_service.analyze_task(db_session, task.id)
    db_session.refresh(task)

    assert task.processing_status == "dimension_review"
    assert task.rfq_modules == rfq_modules
    assert task.dimension_draft is not None
    assert len(task.dimension_draft["items"]) >= 1
    assert task.comparison_table is None
    assert task.similar_projects is None


def test_analyze_task_uses_parse_cache_on_second_run(db_session, analysis_service, monkeypatch, tmp_path):
    """PERF08: same file bytes + versions skip parse and match."""
    rfq_path = tmp_path / "cached.docx"
    rfq_path.write_bytes(b"identical-content-for-cache")

    rfq_modules = {
        "project_name": "Cached Project",
        "platform_type": "MEB",
        "functions_in_scope": ["Chassis"],
        "modules": [],
    }
    parse_calls = {"n": 0}
    match_calls = {"n": 0}

    def fake_parse(_path, **kwargs):
        parse_calls["n"] += 1
        return rfq_modules

    real_match = analysis_service.dimension_match.match_rfq_to_baseline

    def counting_match(*args, **kwargs):
        match_calls["n"] += 1
        return real_match(*args, **kwargs)

    monkeypatch.setattr(analysis_service.parse_service, "parse_rules_first", fake_parse)
    monkeypatch.setattr(analysis_service.dimension_match, "match_rfq_to_baseline", counting_match)

    t1 = RFQTask(file_name="cached.docx", file_path=str(rfq_path), processing_status="queued")
    db_session.add(t1)
    db_session.commit()
    analysis_service.analyze_task(db_session, t1.id)
    db_session.refresh(t1)
    assert t1.processing_status == "dimension_review"
    assert parse_calls["n"] == 1
    assert match_calls["n"] == 1
    draft_first = t1.dimension_draft

    t2 = RFQTask(file_name="cached.docx", file_path=str(rfq_path), processing_status="queued")
    db_session.add(t2)
    db_session.commit()
    analysis_service.analyze_task(db_session, t2.id)
    db_session.refresh(t2)
    assert t2.processing_status == "dimension_review"
    assert t2.rfq_modules == rfq_modules
    assert t2.dimension_draft is not None
    assert t2.dimension_draft.get("baseline_version") == draft_first.get("baseline_version")
    assert parse_calls["n"] == 1
    assert match_calls["n"] == 1
    # Owner isolation: task-local copy — mutating t2 draft must not rewrite t1
    t2.dimension_draft["items"] = []
    db_session.refresh(t1)
    assert len(t1.dimension_draft.get("items") or []) >= 1


def test_confirm_dimensions_generates_matrix(db_session, analysis_service, monkeypatch):
    draft = analysis_service.dimension_match.match_rfq_to_baseline(
        {
            "project_name": "MEB Chassis MacPherson",
            "functions_in_scope": ["Chassis"],
            "platform_type": "MEB",
            "development_scope": [{"id": "4.1", "title": "工作内容及要求"}],
        }
    )
    task = RFQTask(
        file_name="meb.docx",
        file_path="/tmp/meb.docx",
        processing_status="dimension_review",
        rfq_modules={
            "project_name": "MEB Chassis MacPherson",
            "functions_in_scope": ["Chassis"],
            "platform_type": "MEB",
            "development_scope": [{"id": "4.1", "title": "工作内容及要求"}],
        },
        dimension_draft=draft,
    )
    db_session.add(task)
    db_session.commit()

    captured: dict[str, object] = {}
    original_search = analysis_service.rag.search_similar_projects

    def fake_search(query, top_k=3, **kwargs):
        captured["query"] = query
        captured["doc_type_filter"] = kwargs.get("doc_type_filter")
        captured["rfq_modules"] = kwargs.get("rfq_modules")
        return original_search(
            query,
            top_k=top_k,
            doc_type_filter=kwargs.get("doc_type_filter"),
            rfq_modules=kwargs.get("rfq_modules"),
            draft=kwargs.get("draft"),
        )

    monkeypatch.setattr(analysis_service.rag, "search_similar_projects", fake_search)
    result = analysis_service.confirm_dimensions(db_session, task, {})
    db_session.refresh(task)

    assert result.reused is False
    assert result.job.job_type == "rfq_confirm"
    assert result.job.payload["task_id"] == task.id
    assert result.job.payload["draft_fingerprint"]
    assert task.processing_status == "completed"
    assert task.comparison_table is not None
    assert task.comparison_table.get("matrix_rows")
    assert task.similar_projects is not None
    assert "工作内容及要求" not in str(captured.get("query"))
    assert "MEB Chassis MacPherson" in str(captured.get("query"))
    assert "Chassis" in str(captured.get("query"))
    assert captured.get("doc_type_filter") == ["rfq"]
    assert isinstance(captured.get("rfq_modules"), dict)
    assert captured["rfq_modules"].get("project_name") == "MEB Chassis MacPherson"


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
        analysis_service.execute_confirm_job(db_session, task.id)
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


def test_confirm_dimensions_enqueues_job_without_inline(db_session, analysis_service, monkeypatch):
    draft = analysis_service.dimension_match.match_rfq_to_baseline(
        {
            "project_name": "MEB Chassis",
            "functions_in_scope": ["Chassis"],
            "platform_type": "MEB",
        }
    )
    draft["items"][0]["in_scope"] = True
    task = RFQTask(
        file_name="meb.docx",
        file_path="/tmp/meb.docx",
        processing_status="dimension_review",
        rfq_modules={"project_name": "MEB Chassis", "functions_in_scope": ["Chassis"]},
        dimension_draft=draft,
    )
    db_session.add(task)
    db_session.commit()

    monkeypatch.setattr(analysis_service.job_service, "uses_inline_worker", lambda: False)
    result = analysis_service.confirm_dimensions(db_session, task, {})
    db_session.refresh(task)

    assert result.reused is False
    assert result.job.job_type == "rfq_confirm"
    assert result.job.status == "queued"
    assert result.job.phase == "queued"
    assert result.job.priority == 300
    assert result.job.single_flight_key == f"rfq_confirm:{task.id}"
    assert result.job.payload["task_id"] == task.id
    assert result.job.payload["draft_fingerprint"] == analysis_service.draft_fingerprint(
        task.dimension_draft
    )
    assert task.processing_status == "queued"
    assert task.status_message == "对比表任务排队中"
    assert task.comparison_table is None


def test_confirm_dimensions_reuses_active_job(db_session, analysis_service, monkeypatch):
    draft = analysis_service.dimension_match.match_rfq_to_baseline(
        {"project_name": "MEB", "functions_in_scope": ["Chassis"]}
    )
    draft["items"][0]["in_scope"] = True
    task = RFQTask(
        file_name="meb.docx",
        file_path="/tmp/meb.docx",
        processing_status="dimension_review",
        rfq_modules={"project_name": "MEB", "functions_in_scope": ["Chassis"]},
        dimension_draft=draft,
    )
    db_session.add(task)
    db_session.commit()

    monkeypatch.setattr(analysis_service.job_service, "uses_inline_worker", lambda: False)
    first = analysis_service.confirm_dimensions(db_session, task, {})
    second = analysis_service.confirm_dimensions(db_session, task, {})

    assert second.reused is True
    assert second.job.id == first.job.id


def test_confirm_dimensions_queue_full(db_session, analysis_service, monkeypatch):
    from app.services.rfq_analysis_service import RfqQueueFullError

    draft = analysis_service.dimension_match.match_rfq_to_baseline(
        {"project_name": "MEB", "functions_in_scope": ["Chassis"]}
    )
    draft["items"][0]["in_scope"] = True
    task = RFQTask(
        file_name="meb.docx",
        file_path="/tmp/meb.docx",
        processing_status="dimension_review",
        rfq_modules={"project_name": "MEB"},
        dimension_draft=draft,
    )
    db_session.add(task)
    db_session.commit()

    monkeypatch.setattr(analysis_service.settings, "task_max_queue_size", 0)
    with pytest.raises(RfqQueueFullError) as exc:
        analysis_service.confirm_dimensions(db_session, task, {})
    assert exc.value.queue_depth >= 0

def test_confirm_dimensions_rejects_when_phase2_in_flight(db_session, analysis_service):
    task = RFQTask(
        file_name="meb.docx",
        file_path="/tmp/meb.docx",
        processing_status="retrieving",
        rfq_modules={"project_name": "MEB"},
        dimension_draft={"items": [{"dimension_id": "d1", "in_scope": True}]},
    )
    db_session.add(task)
    db_session.commit()

    with pytest.raises(ValueError, match="正在生成"):
        analysis_service.confirm_dimensions(db_session, task, {})


def test_confirm_reuses_rejects_different_fingerprint(db_session, analysis_service, monkeypatch):
    draft = analysis_service.dimension_match.match_rfq_to_baseline(
        {"project_name": "MEB", "functions_in_scope": ["Chassis"]}
    )
    draft["items"][0]["in_scope"] = True
    task = RFQTask(
        file_name="meb.docx",
        file_path="/tmp/meb.docx",
        processing_status="dimension_review",
        rfq_modules={"project_name": "MEB", "functions_in_scope": ["Chassis"]},
        dimension_draft=draft,
    )
    db_session.add(task)
    db_session.commit()

    monkeypatch.setattr(analysis_service.job_service, "uses_inline_worker", lambda: False)
    first = analysis_service.confirm_dimensions(db_session, task, {})
    other_items = [{**draft["items"][0], "in_scope": True, "work_content": "完全不同的勾选内容"}]
    with pytest.raises(ValueError, match="正在生成"):
        analysis_service.confirm_dimensions(
            db_session,
            task,
            {"items": other_items, "custom_items": []},
        )
    assert first.job.id


def test_get_status_payload_includes_job_phase(db_session, analysis_service):
    from datetime import datetime, timezone

    from app.models.task_job import TaskJob
    from app.repositories.task_job_repository import TaskJobRepository

    task = RFQTask(
        file_name="phase.docx",
        file_path="/tmp/phase.docx",
        processing_status="retrieving",
        progress="55",
        status_message="正在检索相似历史项目...",
        rfq_modules={"project_name": "MEB"},
        dimension_draft={"items": [{"dimension_id": "d1", "in_scope": True}]},
    )
    db_session.add(task)
    db_session.commit()
    now = datetime.now(timezone.utc)
    job = TaskJob(
        job_type="rfq_confirm",
        ref_id=task.id,
        status="running",
        phase="retrieving",
        single_flight_key=f"rfq_confirm:{task.id}",
        started_at=now,
        heartbeat_at=now,
        queued_at=now,
    )
    TaskJobRepository(db_session).create(job)

    payload = analysis_service.get_status_payload(task, db_session)
    assert payload["status"] == "retrieving"
    assert payload["phase"] == "retrieving"
    assert payload["message"] == "正在检索相似历史项目..."
    assert "queue_wait_ms" in payload
    assert "run_ms" in payload


def test_recover_orphan_skips_when_confirm_job_active(db_session, analysis_service):
    from datetime import datetime, timedelta, timezone

    from app.models.task_job import TaskJob
    from app.repositories.task_job_repository import TaskJobRepository

    stale = datetime.now(timezone.utc) - timedelta(seconds=3600)
    task = RFQTask(
        file_name="stale.docx",
        file_path="/tmp/stale.docx",
        processing_status="retrieving",
        progress="55",
        rfq_modules={"project_name": "MEB"},
        dimension_draft={"items": [{"dimension_id": "d1", "in_scope": True}]},
        updated_at=stale,
    )
    db_session.add(task)
    db_session.commit()

    now = datetime.now(timezone.utc)
    job = TaskJob(
        job_type="rfq_confirm",
        ref_id=task.id,
        status="running",
        phase="retrieving",
        single_flight_key=f"rfq_confirm:{task.id}",
        started_at=now,
        heartbeat_at=now,
        queued_at=now,
    )
    TaskJobRepository(db_session).create(job)

    same = analysis_service.recover_orphaned_confirm_phase(db_session, task)
    assert same.processing_status == "retrieving"
