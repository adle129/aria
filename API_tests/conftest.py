import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SAMPLE_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "mock_chassis_rfq.docx"
DEMO_MULTIFUNCTION_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "demo_multifunction_rfq.docx"
DIMENSION_BASELINE_SEED = (
    Path(__file__).resolve().parents[1] / "backend" / "data" / "config" / "dimension_baseline.v1.json"
)

# Configure test environment before importing app modules
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["MOCK_LLM"] = "true"
os.environ["MOCK_RAG"] = "true"
os.environ["ARIA_UI_PROFILE"] = "experience"
os.environ["KB_DEBUG_ENABLED"] = "false"
os.environ["OLLAMA_MODEL"] = "qwen2.5:14b"
os.environ["AUTH_ENABLED"] = "false"
os.environ["EMBEDDING_MODEL"] = "nomic-embed-text"

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    template_src = Path(__file__).resolve().parents[1] / "backend" / "data" / "templates"
    template_dst = tmp_path / "templates"
    template_dst.mkdir(exist_ok=True)
    quote_tpl = template_src / "quote_template.xlsx"
    qa_tpl = template_src / "qa_template.xlsx"
    if quote_tpl.exists():
        (template_dst / "quote_template.xlsx").write_bytes(quote_tpl.read_bytes())
    if qa_tpl.exists():
        (template_dst / "qa_template.xlsx").write_bytes(qa_tpl.read_bytes())
    monkeypatch.setenv("UPLOAD_PATH", str(tmp_path / "uploads"))
    monkeypatch.setenv("OUTPUT_PATH", str(tmp_path / "outputs"))
    monkeypatch.setenv("TEMPLATE_PATH", str(template_dst))
    monkeypatch.setenv("KNOWLEDGE_BASE_PATH", str(tmp_path / "kb"))
    if DIMENSION_BASELINE_SEED.is_file():
        monkeypatch.setenv("DIMENSION_BASELINE_PATH", str(DIMENSION_BASELINE_SEED))
    (tmp_path / "uploads").mkdir(exist_ok=True)
    (tmp_path / "outputs").mkdir(exist_ok=True)
    (tmp_path / "kb").mkdir(exist_ok=True)
    get_settings.cache_clear()
    return tmp_path


@pytest.fixture
def client(upload_dir, monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from app.models.engagement import Engagement
    from app.models.knowledge_import import KnowledgeImport
    from app.models.project import Project
    from app.models.rfq_task import RFQTask
    from app.models.task_job import TaskJob
    from app.models.user import User

    Base.metadata.create_all(
        bind=engine,
        tables=[
            Project.__table__,
            User.__table__,
            RFQTask.__table__,
            TaskJob.__table__,
            Engagement.__table__,
            KnowledgeImport.__table__,
        ],
    )
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    import app.api.v1.rfq as rfq_module
    import app.database as database_module
    from app.services.rfq_analysis_service import RFQAnalysisService

    settings = get_settings()
    rfq_module.analysis_service = RFQAnalysisService(settings)
    rfq_module.quote_service.settings = settings
    rfq_module.artifact_service.settings = settings

    monkeypatch.setattr(database_module, "engine", engine)
    monkeypatch.setattr(database_module, "SessionLocal", session_factory)

    app.dependency_overrides[get_db] = override_get_db
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    get_settings.cache_clear()


@pytest.fixture
def sample_rfq_bytes():
    assert SAMPLE_RFQ.exists(), f"Missing sample RFQ: {SAMPLE_RFQ}"
    return SAMPLE_RFQ.read_bytes()


@pytest.fixture
def demo_multifunction_rfq_bytes():
    assert DEMO_MULTIFUNCTION_RFQ.exists(), f"Missing demo RFQ: {DEMO_MULTIFUNCTION_RFQ}"
    return DEMO_MULTIFUNCTION_RFQ.read_bytes()
