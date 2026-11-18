import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.utils.validators import normalize_phone, validate_language


class UserPublic(BaseModel):
    """Safe user representation — never includes password_hash."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    role: str
    preferred_language: str
    is_active: bool
    is_verified: bool
    phone_verified: bool
    created_at: datetime
    updated_at: datetime


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    role: str
    preferred_language: str


class UserUpdate(BaseModel):
    """Fields a user may change on themselves. role / is_active / is_verified are deliberately absent."""
    model_config = ConfigDict(extra="forbid")

    full_name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    preferred_language: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        return normalize_phone(v)

    @field_validator("preferred_language")
    @classmethod
    def _lang(cls, v):
        return validate_language(v) if v is not None else v

    @field_validator("full_name")
    @classmethod
    def _name(cls, v):
        return v.strip() if v else v


class LanguageUpdate(BaseModel):
    preferred_language: str

    @field_validator("preferred_language")
    @classmethod
    def _lang(cls, v):
        return validate_language(v)


class LanguageInfo(BaseModel):
    code: str
    name: str
    native: str


class PatientProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    created_at: datetime


class WorkerProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    designation: Optional[str] = None
    organization: Optional[str] = None
    verification_status: str
    created_at: datetime


class WorkerProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    designation: Optional[str] = Field(default=None, max_length=100)
    organization: Optional[str] = Field(default=None, max_length=150)


class PatientMe(BaseModel):
    user: UserPublic
    profile: PatientProfileOut


class WorkerMe(BaseModel):
    user: UserPublic
    profile: WorkerProfileOut


class AdminProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    employee_id: str
    hospital_name: str
    verification_status: str
    created_at: datetime


class AdminMe(BaseModel):
    user: UserPublic
    profile: Optional[AdminProfileOut] = None  # None for the bootstrap admin created via script
    verification_status: str


class AdminUserOut(UserPublic):
    worker_profile: Optional[WorkerProfileOut] = None
    admin_profile: Optional[AdminProfileOut] = None
    patient_profile_id: Optional[uuid.UUID] = None


class AdminUserStatusUpdate(BaseModel):
    is_active: bool
