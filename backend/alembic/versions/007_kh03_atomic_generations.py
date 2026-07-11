"""R1-KH03: blue/green knowledge index generations."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_kh03_atomic_generations"
down_revision: Union[str, None] = "006_kh02_index_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "knowledge_index_generations" not in tables:
        op.create_table(
            "knowledge_index_generations",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("logical_namespace", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("created_by_job_id", sa.String(), nullable=True),
            sa.Column("schema_version", sa.String(length=32), nullable=False),
            sa.Column("embedding_model", sa.String(length=128), nullable=False),
            sa.Column("content_fingerprint", sa.String(length=64), nullable=True),
            sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_summary", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_knowledge_index_generations_namespace",
            "knowledge_index_generations",
            ["logical_namespace"],
        )
        op.create_index(
            "ix_knowledge_index_generations_status",
            "knowledge_index_generations",
            ["status"],
        )
    if "knowledge_index_state" not in tables:
        op.create_table(
            "knowledge_index_state",
            sa.Column("logical_namespace", sa.String(length=64), nullable=False),
            sa.Column("active_generation_id", sa.String(length=64), nullable=True),
            sa.Column("previous_generation_id", sa.String(length=64), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["active_generation_id"],
                ["knowledge_index_generations.id"],
            ),
            sa.ForeignKeyConstraint(
                ["previous_generation_id"],
                ["knowledge_index_generations.id"],
            ),
            sa.PrimaryKeyConstraint("logical_namespace"),
        )

    if bind.dialect.name != "postgresql":
        return
    inspector = sa.inspect(bind)
    if "knowledge_chunks" not in inspector.get_table_names():
        return
    if "generation_id" in {col["name"] for col in inspector.get_columns("knowledge_chunks")}:
        return

    op.add_column(
        "knowledge_chunks",
        sa.Column("generation_id", sa.String(length=64), nullable=True),
    )
    op.execute(
        """
        INSERT INTO knowledge_index_generations (
            id, logical_namespace, status, schema_version, embedding_model,
            chunk_count, created_at, validated_at, activated_at
        )
        SELECT
            'legacy-' || md5(namespace),
            namespace,
            'active',
            'legacy-v1',
            'nomic-embed-text',
            COUNT(*),
            NOW(),
            NOW(),
            NOW()
        FROM knowledge_chunks
        GROUP BY namespace
        """
    )
    op.execute(
        """
        UPDATE knowledge_chunks
        SET generation_id = 'legacy-' || md5(namespace)
        """
    )
    op.execute(
        """
        INSERT INTO knowledge_index_state (
            logical_namespace, active_generation_id, previous_generation_id,
            version, updated_at
        )
        SELECT namespace, 'legacy-' || md5(namespace), NULL, 1, NOW()
        FROM knowledge_chunks
        GROUP BY namespace
        """
    )
    op.alter_column("knowledge_chunks", "generation_id", nullable=False)
    op.drop_constraint("knowledge_chunks_pkey", "knowledge_chunks", type_="primary")
    op.create_primary_key(
        "knowledge_chunks_pkey",
        "knowledge_chunks",
        ["generation_id", "chunk_id"],
    )
    op.create_foreign_key(
        "fk_knowledge_chunks_generation",
        "knowledge_chunks",
        "knowledge_index_generations",
        ["generation_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_knowledge_chunks_generation_id",
        "knowledge_chunks",
        ["generation_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        inspector = sa.inspect(bind)
        if "knowledge_chunks" in inspector.get_table_names():
            op.execute(
                """
                DELETE FROM knowledge_chunks AS chunks
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM knowledge_index_state AS state
                    WHERE state.logical_namespace = chunks.namespace
                      AND state.active_generation_id = chunks.generation_id
                )
                """
            )
            op.drop_index("ix_knowledge_chunks_generation_id", table_name="knowledge_chunks")
            op.drop_constraint(
                "fk_knowledge_chunks_generation",
                "knowledge_chunks",
                type_="foreignkey",
            )
            op.drop_constraint("knowledge_chunks_pkey", "knowledge_chunks", type_="primary")
            op.create_primary_key(
                "knowledge_chunks_pkey",
                "knowledge_chunks",
                ["chunk_id"],
            )
            op.drop_column("knowledge_chunks", "generation_id")

    op.drop_table("knowledge_index_state")
    op.drop_index(
        "ix_knowledge_index_generations_status",
        table_name="knowledge_index_generations",
    )
    op.drop_index(
        "ix_knowledge_index_generations_namespace",
        table_name="knowledge_index_generations",
    )
    op.drop_table("knowledge_index_generations")
