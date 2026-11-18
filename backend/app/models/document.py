import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Date, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import CreatedAt, UUIDPrimaryKey

if TYPE_CHECKING:
    from app.models.document_analysis import DocumentAnalysis
    from app.models.patient import PatientProfile
    from app.models.user import User


class MedicalDocument(UUIDPrimaryKey, CreatedAt, Base):
    """Metadata for an original medical document. The file itself lives in private storage (storage_key)."""

    __tablename__ = "medical_documents"
    __table_args__ = (Index("ix_documents_patient_created", "patient_id", "created_at"),)

    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("patient_profiles.id", ondelete="CASCADE"), nullable=False
    )
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    document_date: Mapped[Optional[date]] = mapped_column(Date)
    processing_status: Mapped[str] = mapped_column(String(30), nullable=False, default="UPLOADED")

    patient: Mapped["PatientProfile"] = relationship()
    uploader: Mapped[Optional["User"]] = relationship()
    analyses: Mapped[list["DocumentAnalysis"]] = relationship(viewonly=True, lazy="selectin")

    @property
    def translated_languages(self) -> list[str]:
        """Languages with a finished AI explanation/translation, most recent first."""
        done = [a for a in self.analyses if a.status == "COMPLETED"]
        done.sort(key=lambda a: a.completed_at or a.updated_at, reverse=True)
        return [a.language_code for a in done]
