"""R1-KH04: cross-process Ollama resource leases."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_kh04_ollama_leases"
down_revision: Union[str, None] = "007_kh03_atomic_generations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ollama_resource_leases" in inspector.get_table_names():
        return
    op.create_table(
        "ollama_resource_leases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("resource_key", sa.String(length=128), nullable=False),
        sa.Column("holder_id", sa.String(length=255), nullable=False),
        sa.Column("request_type", sa.String(length=32), nullable=False),
        sa.Column("base_priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ollama_leases_resource_status",
        "ollama_resource_leases",
        ["resource_key", "status"],
    )
    op.create_index(
        "ix_ollama_resource_leases_holder_id",
        "ollama_resource_leases",
        ["holder_id"],
    )
    op.create_index(
        "ix_ollama_resource_leases_request_type",
        "ollama_resource_leases",
        ["request_type"],
    )
    op.create_index(
        "ix_ollama_resource_leases_status",
        "ollama_resource_leases",
        ["status"],
    )


def downgrade() -> None:
    op.drop_table("ollama_resource_leases")
