import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import CreatedAt, UUIDPrimaryKey, utcnow


class DocumentAnalysis(UUIDPrimaryKey, CreatedAt, Base):
    """AI reading of one medical document in one language: extracted text, entities, simple explanation, translation."""

    __tablename__ = "document_analyses"
    __table_args__ = (UniqueConstraint("document_id", "language_code", name="uq_analysis_document_language"),)

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("medical_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language_code: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    result_json: Mapped[Optional[str]] = mapped_column(Text)  # DocumentInsight as JSON
    error: Mapped[Optional[str]] = mapped_column(String(500))
    model: Mapped[Optional[str]] = mapped_column(String(60))
    requested_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
