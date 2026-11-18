import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import CreatedAt, UUIDPrimaryKey


class AuditLog(UUIDPrimaryKey, CreatedAt, Base):
    """Records sensitive access/modifications. Never stores medical content, only identifiers."""

    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_created", "created_at"),)

    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(60), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(64))
    patient_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, nullable=True, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    details: Mapped[Optional[str]] = mapped_column(Text)
