"""R1-PERF09: query embedding short-TTL cache table."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_query_embedding_cache"
down_revision: Union[str, None] = "010_rfq_parse_cache"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "query_embedding_cache" in inspector.get_table_names():
        return
    op.create_table(
        "query_embedding_cache",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("cache_key", sa.String(length=256), nullable=False),
        sa.Column("query_hash", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=128), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_hit_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("cache_key", name="uq_query_embedding_cache_key"),
    )
    op.create_index("ix_query_embedding_cache_cache_key", "query_embedding_cache", ["cache_key"])
    op.create_index("ix_query_embedding_cache_query_hash", "query_embedding_cache", ["query_hash"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "query_embedding_cache" not in inspector.get_table_names():
        return
    op.drop_index("ix_query_embedding_cache_query_hash", table_name="query_embedding_cache")
    op.drop_index("ix_query_embedding_cache_cache_key", table_name="query_embedding_cache")
    op.drop_table("query_embedding_cache")
