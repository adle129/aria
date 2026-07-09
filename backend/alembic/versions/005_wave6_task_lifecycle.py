"""R1 Wave 6: rfq_tasks.archived for task lifecycle management."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_wave6_task_lifecycle"
down_revision: Union[str, None] = "004_wave5_dimension_draft"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "rfq_tasks" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("rfq_tasks")}
    if "archived" not in cols:
        op.add_column(
            "rfq_tasks",
            sa.Column("archived", sa.Boolean(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    op.drop_column("rfq_tasks", "archived")
