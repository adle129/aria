"""R1-KH02: asynchronous knowledge index job lifecycle."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_kh02_index_jobs"
down_revision: Union[str, None] = "005_wave6_task_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "task_jobs" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("task_jobs")}
    additions = [
        ("result_summary", sa.Column("result_summary", sa.JSON(), nullable=True)),
        ("priority", sa.Column("priority", sa.Integer(), nullable=False, server_default="0")),
        ("phase", sa.Column("phase", sa.String(length=64), nullable=True)),
        (
            "progress_current",
            sa.Column("progress_current", sa.Integer(), nullable=False, server_default="0"),
        ),
        (
            "progress_total",
            sa.Column("progress_total", sa.Integer(), nullable=False, server_default="0"),
        ),
        ("single_flight_key", sa.Column("single_flight_key", sa.String(length=128), nullable=True)),
        ("heartbeat_at", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True)),
        (
            "cancel_requested_at",
            sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        ),
    ]
    for name, column in additions:
        if name not in cols:
            op.add_column("task_jobs", column)

    op.create_index(
        "ix_task_jobs_single_flight_key",
        "task_jobs",
        ["single_flight_key"],
        unique=False,
    )
    if bind.dialect.name == "postgresql":
        op.create_index(
            "uq_task_jobs_active_single_flight",
            "task_jobs",
            ["job_type", "single_flight_key"],
            unique=True,
            postgresql_where=sa.text(
                "single_flight_key IS NOT NULL AND status IN ('queued', 'running')"
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_index("uq_task_jobs_active_single_flight", table_name="task_jobs")
    op.drop_index("ix_task_jobs_single_flight_key", table_name="task_jobs")
    for name in [
        "cancel_requested_at",
        "heartbeat_at",
        "single_flight_key",
        "progress_total",
        "progress_current",
        "phase",
        "priority",
        "result_summary",
    ]:
        op.drop_column("task_jobs", name)
