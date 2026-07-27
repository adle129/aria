"""R1-CHG12: engagements.space_id default quoting."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014_engagement_space_id"
down_revision: Union[str, None] = "013_customers_vehicle_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "engagements" not in tables:
        return
    existing = {col["name"] for col in inspector.get_columns("engagements")}
    if "space_id" not in existing:
        op.add_column(
            "engagements",
            sa.Column(
                "space_id",
                sa.String(length=64),
                nullable=False,
                server_default="quoting",
            ),
        )
        op.create_index("ix_engagements_space_id", "engagements", ["space_id"])
        op.execute(sa.text("UPDATE engagements SET space_id = 'quoting' WHERE space_id IS NULL OR space_id = ''"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "engagements" not in tables:
        return
    existing = {col["name"] for col in inspector.get_columns("engagements")}
    if "space_id" in existing:
        op.drop_index("ix_engagements_space_id", table_name="engagements")
        op.drop_column("engagements", "space_id")
