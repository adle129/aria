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
    from app.models import project, rfq_task  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_rfq_task_columns()


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
    if not additions:
        return
    with engine.begin() as conn:
        for spec in additions:
            conn.execute(text(f"ALTER TABLE rfq_tasks ADD COLUMN {spec}"))
