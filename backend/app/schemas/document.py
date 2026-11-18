import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentType


class DocumentOut(BaseModel):
    """Document metadata. storage_key (the private path) is intentionally never exposed."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    uploaded_by: Optional[uuid.UUID] = None
    document_name: str
    document_type: DocumentType
    mime_type: str
    file_size: int
    document_date: Optional[date] = None
    processing_status: str
    created_at: datetime
    translated_languages: list[str] = []  # languages with a saved AI translation, most recent first


class DocumentList(BaseModel):
    items: list[DocumentOut]
    total: int
