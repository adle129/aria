import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

SAMPLE_RFQ = Path(__file__).resolve().parents[1] / "samples" / "rfq" / "mock_chassis_rfq.docx"

# Configure test environment before importing app modules
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["MOCK_LLM"] = "true"
os.environ["MOCK_RAG"] = "true"

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
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    import app.api.v1.rfq as rfq_module
    import app.database as database_module

    settings = get_settings()
    rfq_module.analysis_service.settings = settings
    rfq_module.quote_service.settings = settings
    rfq_module.artifact_service.settings = settings

    monkeypatch.setattr(database_module, "engine", engine)
    monkeypatch.setattr(database_module, "SessionLocal", session_factory)
    monkeypatch.setattr(rfq_module, "SessionLocal", session_factory)

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
