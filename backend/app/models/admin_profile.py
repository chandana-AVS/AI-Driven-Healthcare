import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import CreatedAt, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.user import User


class AdminProfile(UUIDPrimaryKey, CreatedAt, Base):
    """Details submitted by a self-registered administrator. Must be approved by an existing verified admin."""

    __tablename__ = "admin_profiles"
    __table_args__ = (
        UniqueConstraint("hospital_name", "employee_id", name="uq_admin_hospital_employee"),
        CheckConstraint(
            "verification_status IN ('PENDING','VERIFIED','REJECTED')", name="ck_admin_verification_status"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(String(50), nullable=False)
    hospital_name: Mapped[str] = mapped_column(String(150), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)

    user: Mapped["User"] = relationship(back_populates="admin_profile")
