from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import CreatedAt, UUIDPrimaryKey, utcnow

if TYPE_CHECKING:
    from app.models.admin_profile import AdminProfile
    from app.models.healthcare_worker import HealthcareWorkerProfile
    from app.models.patient import PatientProfile


class User(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email IS NOT NULL OR phone IS NOT NULL", name="ck_users_email_or_phone"),
        CheckConstraint("role IN ('PATIENT','HEALTHCARE_WORKER','ADMIN')", name="ck_users_role"),
        Index("ix_users_role", "role"),
    )

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    patient_profile: Mapped[Optional["PatientProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    worker_profile: Mapped[Optional["HealthcareWorkerProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    admin_profile: Mapped[Optional["AdminProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
