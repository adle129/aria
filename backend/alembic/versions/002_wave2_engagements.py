"""R1 Wave 2: engagements table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_wave2_engagements"
down_revision: Union[str, None] = "001_wave1_task_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "engagements",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("project_name", sa.String(length=256), nullable=False),
        sa.Column("customer", sa.String(length=256), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("functions", sa.JSON(), nullable=False),
        sa.Column("folder_path", sa.String(length=512), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=True),
        sa.Column("index_status", sa.String(length=32), nullable=False),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("engagements")
