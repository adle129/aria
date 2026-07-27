"""R1-CHG03: RFQ task function_source_map for per-Function quote sources."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012_function_source_map"
down_revision: Union[str, None] = "011_query_embedding_cache"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "rfq_tasks" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("rfq_tasks")}
    if "function_source_map" in existing:
        return
    op.add_column("rfq_tasks", sa.Column("function_source_map", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "rfq_tasks" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("rfq_tasks")}
    if "function_source_map" not in existing:
        return
    op.drop_column("rfq_tasks", "function_source_map")
