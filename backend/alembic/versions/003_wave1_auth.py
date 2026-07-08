"""R1 Wave 1: users table + rfq_tasks.owner_id."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_wave1_auth"
down_revision: Union[str, None] = "002_wave2_engagements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.add_column("rfq_tasks", sa.Column("owner_id", sa.String(), nullable=True))
    op.create_index("ix_rfq_tasks_owner_id", "rfq_tasks", ["owner_id"])
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_foreign_key(
            "fk_rfq_tasks_owner_id_users",
            "rfq_tasks",
            "users",
            ["owner_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("fk_rfq_tasks_owner_id_users", "rfq_tasks", type_="foreignkey")
    op.drop_index("ix_rfq_tasks_owner_id", table_name="rfq_tasks")
    op.drop_column("rfq_tasks", "owner_id")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
