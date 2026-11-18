"""phone verification: users.phone_verified + phone_otps

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-12
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("phone_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    # Accounts created before SMS verification existed are grandfathered in, so nobody is locked out.
    op.execute(sa.text("UPDATE users SET phone_verified = :t WHERE phone IS NOT NULL").bindparams(t=True))

    op.create_table(
        "phone_otps",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_phone_otps_user_created", "phone_otps", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_phone_otps_user_created", table_name="phone_otps")
    op.drop_table("phone_otps")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("phone_verified")
