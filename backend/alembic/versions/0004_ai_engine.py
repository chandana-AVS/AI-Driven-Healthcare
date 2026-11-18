"""milestone 2: document_analyses + knowledge-base fields on healthcare_content

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-15
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_analyses",
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("language_code", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("model", sa.String(length=60), nullable=True),
        sa.Column("requested_by", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["medical_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "language_code", name="uq_analysis_document_language"),
    )
    op.create_index("ix_document_analyses_document_id", "document_analyses", ["document_id"], unique=False)

    with op.batch_alter_table("healthcare_content") as batch:
        batch.add_column(sa.Column("content_type", sa.String(length=30), nullable=False, server_default="ARTICLE"))
        batch.add_column(sa.Column("translation_group_id", sa.Uuid(), nullable=True))
        batch.create_index("ix_healthcare_content_content_type", ["content_type"], unique=False)
        batch.create_index("ix_healthcare_content_translation_group_id", ["translation_group_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("healthcare_content") as batch:
        batch.drop_index("ix_healthcare_content_translation_group_id")
        batch.drop_index("ix_healthcare_content_content_type")
        batch.drop_column("translation_group_id")
        batch.drop_column("content_type")
    op.drop_index("ix_document_analyses_document_id", table_name="document_analyses")
    op.drop_table("document_analyses")
