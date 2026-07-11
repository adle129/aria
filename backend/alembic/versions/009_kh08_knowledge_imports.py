"""R1-KH08: knowledge import audit batches and engagement audit fields."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_kh08_knowledge_imports"
down_revision: Union[str, None] = "008_kh04_ollama_leases"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "knowledge_imports" not in tables:
        op.create_table(
            "knowledge_imports",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("job_id", sa.String(), nullable=True),
            sa.Column("triggered_by", sa.String(), nullable=True),
            sa.Column("batch_id", sa.String(length=128), nullable=True),
            sa.Column("mode", sa.String(length=32), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("generation_id", sa.String(length=64), nullable=True),
            sa.Column("new_documents", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("new_chunks", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("skipped", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_files", sa.JSON(), nullable=False),
            sa.Column("engagements", sa.JSON(), nullable=False),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["job_id"], ["task_jobs.id"]),
            sa.ForeignKeyConstraint(["triggered_by"], ["users.id"]),
            sa.ForeignKeyConstraint(
                ["generation_id"],
                ["knowledge_index_generations.id"],
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_knowledge_imports_status",
            "knowledge_imports",
            ["status"],
        )
        op.create_index(
            "ix_knowledge_imports_created_at",
            "knowledge_imports",
            ["created_at"],
        )

    engagement_cols = {
        col["name"] for col in inspector.get_columns("engagements")
    }
    if "uploaded_at" not in engagement_cols:
        op.add_column(
            "engagements",
            sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "uploaded_by" not in engagement_cols:
        op.add_column(
            "engagements",
            sa.Column("uploaded_by", sa.String(), nullable=True),
        )
    if "content_hash" not in engagement_cols:
        op.add_column(
            "engagements",
            sa.Column("content_hash", sa.String(length=64), nullable=True),
        )
    if "tier" not in engagement_cols:
        op.add_column(
            "engagements",
            sa.Column("tier", sa.String(length=16), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "knowledge_imports" in inspector.get_table_names():
        op.drop_index("ix_knowledge_imports_created_at", table_name="knowledge_imports")
        op.drop_index("ix_knowledge_imports_status", table_name="knowledge_imports")
        op.drop_table("knowledge_imports")
    for col in ("tier", "content_hash", "uploaded_by", "uploaded_at"):
        engagement_cols = {
            c["name"] for c in inspector.get_columns("engagements")
        }
        if col in engagement_cols:
            op.drop_column("engagements", col)
