import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.utils.validators import normalize_phone


class PatientProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(default=None, max_length=30)
    address: Optional[str] = Field(default=None, max_length=1000)
    emergency_contact_name: Optional[str] = Field(default=None, max_length=150)
    emergency_contact_phone: Optional[str] = None

    @field_validator("emergency_contact_phone")
    @classmethod
    def _phone(cls, v):
        return normalize_phone(v)

    @field_validator("date_of_birth")
    @classmethod
    def _dob(cls, v):
        if v and v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return v


class AccessGrantCreate(BaseModel):
    """Patient grants a healthcare worker access, identified by email/phone or worker profile id."""
    worker_identifier: Optional[str] = Field(default=None, max_length=255)
    healthcare_worker_id: Optional[uuid.UUID] = None


class AdminAccessGrantCreate(BaseModel):
    patient_id: uuid.UUID
    healthcare_worker_id: uuid.UUID


class AccessGrantOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str
    healthcare_worker_id: uuid.UUID
    worker_name: str
    worker_designation: Optional[str] = None
    worker_organization: Optional[str] = None
    access_status: str
    granted_by: Optional[uuid.UUID] = None
    created_at: datetime
    revoked_at: Optional[datetime] = None


class AuthorizedPatientOut(BaseModel):
    patient_id: uuid.UUID
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    preferred_language: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    access_granted_at: datetime
    document_count: int = 0
    record_count: int = 0


class WorkerDirectoryEntry(BaseModel):
    """Minimal info about a verified worker so patients can choose whom to grant access."""
    healthcare_worker_id: uuid.UUID
    full_name: str
    designation: Optional[str] = None
    organization: Optional[str] = None
