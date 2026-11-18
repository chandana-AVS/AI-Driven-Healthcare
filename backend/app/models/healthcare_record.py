import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import CreatedAt, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.document import MedicalDocument
    from app.models.user import User


class HealthcareRecord(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "healthcare_records"
    __table_args__ = (Index("ix_records_patient_date", "patient_id", "record_date"),)

    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    record_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("medical_documents.id", ondelete="SET NULL"), nullable=True
    )

    document: Mapped[Optional["MedicalDocument"]] = relationship()
    creator: Mapped[Optional["User"]] = relationship()
