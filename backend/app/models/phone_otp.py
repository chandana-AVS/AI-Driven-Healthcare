import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import CreatedAt, UUIDPrimaryKey


class PhoneOTP(UUIDPrimaryKey, CreatedAt, Base):
    """A one-time SMS code. Only an HMAC of the code is stored, never the code itself."""
    __tablename__ = "phone_otps"
    __table_args__ = (Index("ix_phone_otps_user_created", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)  # the number the code was sent to
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
