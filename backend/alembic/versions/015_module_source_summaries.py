"""R1-CHG08: RFQ task module_source_summaries cache for quote source picking."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015_module_source_summaries"
down_revision: Union[str, None] = "014_engagement_space_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "rfq_tasks" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("rfq_tasks")}
    if "module_source_summaries" in existing:
        return
    op.add_column(
        "rfq_tasks", sa.Column("module_source_summaries", sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "rfq_tasks" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("rfq_tasks")}
    if "module_source_summaries" not in existing:
        return
    op.drop_column("rfq_tasks", "module_source_summaries")
