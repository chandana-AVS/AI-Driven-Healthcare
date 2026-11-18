"""admin self-registration profiles

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.String(length=50), nullable=False),
        sa.Column("hospital_name", sa.String(length=150), nullable=False),
        sa.Column("verification_status", sa.String(length=30), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "verification_status IN ('PENDING','VERIFIED','REJECTED')", name="ck_admin_verification_status"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("hospital_name", "employee_id", name="uq_admin_hospital_employee"),
    )
    op.create_index(
        "ix_admin_profiles_verification_status", "admin_profiles", ["verification_status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_admin_profiles_verification_status", table_name="admin_profiles")
    op.drop_table("admin_profiles")
