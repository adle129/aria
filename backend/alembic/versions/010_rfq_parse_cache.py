"""R1-PERF08: content-addressed RFQ parse cache table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_rfq_parse_cache"
down_revision: Union[str, None] = "009_kh08_knowledge_imports"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "rfq_parse_cache" in inspector.get_table_names():
        return
    op.create_table(
        "rfq_parse_cache",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("cache_key", sa.String(length=160), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("parser_version", sa.String(length=64), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("baseline_version", sa.String(length=64), nullable=False),
        sa.Column("rfq_modules", sa.JSON(), nullable=False),
        sa.Column("dimension_draft", sa.JSON(), nullable=True),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("cache_key", name="uq_rfq_parse_cache_key"),
    )
    op.create_index("ix_rfq_parse_cache_cache_key", "rfq_parse_cache", ["cache_key"])
    op.create_index("ix_rfq_parse_cache_content_hash", "rfq_parse_cache", ["content_hash"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "rfq_parse_cache" not in inspector.get_table_names():
        return
    op.drop_index("ix_rfq_parse_cache_content_hash", table_name="rfq_parse_cache")
    op.drop_index("ix_rfq_parse_cache_cache_key", table_name="rfq_parse_cache")
    op.drop_table("rfq_parse_cache")
