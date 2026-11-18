import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import CreatedAt, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.user import User


class HealthcareWorkerProfile(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "healthcare_worker_profiles"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('PENDING','VERIFIED','REJECTED')", name="ck_worker_verification_status"
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    designation: Mapped[Optional[str]] = mapped_column(String(100))
    organization: Mapped[Optional[str]] = mapped_column(String(150))
    verification_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)

    user: Mapped["User"] = relationship(back_populates="worker_profile")
