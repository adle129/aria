"""Docker entrypoint: init_db then alembic (init_db covers schema through 003)."""

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from app.database import engine, init_db

STAMP_REVISION = "003_wave1_auth"


def _alembic_config() -> Config:
    return Config("alembic.ini")


def _current_revision() -> str | None:
    inspector = inspect(engine)
    if "alembic_version" not in inspector.get_table_names():
        return None
    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    return row[0] if row else None


def bootstrap() -> None:
    init_db()
    cfg = _alembic_config()
    if _current_revision() is None:
        command.stamp(cfg, STAMP_REVISION)
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    bootstrap()
