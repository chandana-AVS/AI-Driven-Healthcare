import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import CreatedAt, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.healthcare_worker import HealthcareWorkerProfile
    from app.models.patient import PatientProfile


class PatientAccess(UUIDPrimaryKey, CreatedAt, Base):
    """Explicit, revocable grant allowing a healthcare worker to access a patient's records."""

    __tablename__ = "patient_access"
    __table_args__ = (
        # Only one ACTIVE grant per patient/worker pair; revoked rows are kept as history.
        Index(
            "uq_patient_access_active",
            "patient_id",
            "healthcare_worker_id",
            unique=True,
            postgresql_where=text("access_status = 'ACTIVE'"),
            sqlite_where=text("access_status = 'ACTIVE'"),
        ),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    healthcare_worker_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("healthcare_worker_profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    access_status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    granted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    patient: Mapped["PatientProfile"] = relationship()
    worker: Mapped["HealthcareWorkerProfile"] = relationship()
