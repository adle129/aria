"""R1 Wave 1: task_jobs queue + knowledge_chunks pgvector baseline."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_wave1_task_jobs"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "task_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("ref_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("worker_id", sa.String(length=128), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_task_jobs_job_type", "task_jobs", ["job_type"])
    op.create_index("ix_task_jobs_ref_id", "task_jobs", ["ref_id"])
    op.create_index("ix_task_jobs_status", "task_jobs", ["status"])

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                chunk_id VARCHAR(128) PRIMARY KEY,
                namespace VARCHAR(64) NOT NULL DEFAULT 'default',
                content TEXT NOT NULL,
                embedding vector(768),
                metadata JSONB NOT NULL DEFAULT '{}',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_namespace ON knowledge_chunks (namespace)"
        )


def downgrade() -> None:
    bind = op.get_bind()
    op.drop_index("ix_task_jobs_status", table_name="task_jobs")
    op.drop_index("ix_task_jobs_ref_id", table_name="task_jobs")
    op.drop_index("ix_task_jobs_job_type", table_name="task_jobs")
    op.drop_table("task_jobs")
    if bind.dialect.name == "postgresql":
        op.execute("DROP TABLE IF EXISTS knowledge_chunks")
