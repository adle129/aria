from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _build_engine():
    settings = get_settings()
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(settings.database_url, connect_args=connect_args)


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models.engagement import Engagement
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
        ],
    )
    _ensure_rfq_task_columns()
    _ensure_pgvector()


def _ensure_pgvector() -> None:
    if engine.dialect.name != "postgresql":
        return
    from app.services.pgvector_store import PgVectorStore

    PgVectorStore.ensure_schema()


def _ensure_rfq_task_columns() -> None:
    """Add Demo Sprint columns to existing databases (no Alembic yet)."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "rfq_tasks" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("rfq_tasks")}
    dialect = engine.dialect.name
    additions = []
    if "solution_draft" not in existing:
        col_type = "JSON" if dialect == "postgresql" else "JSON"
        additions.append(f"solution_draft {col_type}")
    if "qa_items" not in existing:
        col_type = "JSON" if dialect == "postgresql" else "JSON"
        additions.append(f"qa_items {col_type}")
    if "qa_excel_path" not in existing:
        additions.append("qa_excel_path VARCHAR")
    if "owner_id" not in existing:
        additions.append("owner_id VARCHAR")
    if not additions:
        return
    with engine.begin() as conn:
        for spec in additions:
            conn.execute(text(f"ALTER TABLE rfq_tasks ADD COLUMN {spec}"))
