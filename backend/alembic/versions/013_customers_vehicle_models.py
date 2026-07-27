"""R1-CHG05: customer / vehicle_model master data + engagement.vehicle_model."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013_customers_vehicle_models"
down_revision: Union[str, None] = "012_function_source_map"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "customers" not in tables:
        op.create_table(
            "customers",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("name", name="uq_customers_name"),
        )
        op.create_index("ix_customers_name", "customers", ["name"])

    if "vehicle_models" not in tables:
        op.create_table(
            "vehicle_models",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("name", name="uq_vehicle_models_name"),
        )
        op.create_index("ix_vehicle_models_name", "vehicle_models", ["name"])

    if "engagements" in tables:
        existing = {col["name"] for col in inspector.get_columns("engagements")}
        if "vehicle_model" not in existing:
            op.add_column(
                "engagements",
                sa.Column("vehicle_model", sa.String(length=256), nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "engagements" in tables:
        existing = {col["name"] for col in inspector.get_columns("engagements")}
        if "vehicle_model" in existing:
            op.drop_column("engagements", "vehicle_model")

    if "vehicle_models" in tables:
        op.drop_index("ix_vehicle_models_name", table_name="vehicle_models")
        op.drop_table("vehicle_models")

    if "customers" in tables:
        op.drop_index("ix_customers_name", table_name="customers")
        op.drop_table("customers")
