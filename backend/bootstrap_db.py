"""Docker entrypoint: init_db + alembic upgrade head."""

from alembic import command
from alembic.config import Config

from app.database import init_db


def _alembic_config() -> Config:
    return Config("alembic.ini")


def bootstrap() -> None:
    init_db()
    command.upgrade(_alembic_config(), "head")


if __name__ == "__main__":
    bootstrap()
