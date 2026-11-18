import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import RecordType
from app.schemas.document import DocumentOut


class RecordCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_type: RecordType
    title: str = Field(min_length=2, max_length=255)
    description: Optional[str] = Field(default=None, max_length=10000)
    record_date: date
    document_id: Optional[uuid.UUID] = None

    @field_validator("record_date")
    @classmethod
    def _not_future(cls, v: date) -> date:
        if v > date.today():
            raise ValueError("Record date cannot be in the future")
        return v


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    created_by: Optional[uuid.UUID] = None
    created_by_name: Optional[str] = None
    record_type: str
    title: str
    description: Optional[str] = None
    record_date: date
    document_id: Optional[uuid.UUID] = None
    created_at: datetime


class HistoryEntry(BaseModel):
    """Unified chronological timeline entry combining records and documents."""
    entry_type: Literal["RECORD", "DOCUMENT"]
    date: date
    timestamp: datetime
    title: str
    category: str
    status: Optional[str] = None
    description: Optional[str] = None
    record: Optional[RecordOut] = None
    document: Optional[DocumentOut] = None


class PatientHistory(BaseModel):
    patient_id: uuid.UUID
    patient_name: str
    entries: list[HistoryEntry]
