"""R1 Wave 5: rfq_tasks.dimension_draft for F1.10c review."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_wave5_dimension_draft"
down_revision: Union[str, None] = "003_wave1_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "rfq_tasks" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("rfq_tasks")}
    if "dimension_draft" not in cols:
        op.add_column("rfq_tasks", sa.Column("dimension_draft", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("rfq_tasks", "dimension_draft")
