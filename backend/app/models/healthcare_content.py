import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import CreatedAt, UUIDPrimaryKey, utcnow


class HealthcareContent(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "healthcare_content"
    __table_args__ = (Index("ix_content_status_lang_cat", "status", "language_code", "category"),)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    language_code: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    content_type: Mapped[str] = mapped_column(String(30), nullable=False, default="ARTICLE", server_default="ARTICLE",
                                              index=True)
    # Items that are translations of each other share a group id (the id of the original item).
    translation_group_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True, index=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
