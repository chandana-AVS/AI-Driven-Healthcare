from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.user import UserSummary
from app.utils.validators import normalize_phone, validate_language, validate_password_strength


class _RegisterBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=150)
    email: Optional[EmailStr] = None  # optional
    phone: str  # mandatory — verified by SMS before the account can log in
    password: str
    preferred_language: str = "en"

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: str) -> str:
        return v.strip()

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        return v.lower() if v else None

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        phone = normalize_phone(v)
        if not phone:
            raise ValueError("Phone number is required")
        return phone

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        return validate_password_strength(v)

    @field_validator("preferred_language")
    @classmethod
    def _lang(cls, v: str) -> str:
        return validate_language(v)


class PatientRegister(_RegisterBase):
    pass


class HealthcareWorkerRegister(_RegisterBase):
    designation: str = Field(min_length=2, max_length=100)
    organization: str = Field(min_length=2, max_length=150)


class AdminRegister(_RegisterBase):
    """Self-registration for administrators. The account stays PENDING until an existing admin approves it."""
    employee_id: str = Field(min_length=2, max_length=50)
    hospital_name: str = Field(min_length=2, max_length=150)

    @field_validator("employee_id")
    @classmethod
    def _emp(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("hospital_name")
    @classmethod
    def _hospital(cls, v: str) -> str:
        return " ".join(v.split())


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255, description="Email address or phone number")
    password: str = Field(min_length=1, max_length=128)


class PhoneOTPRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255, description="Phone number or email of the account")


class PhoneVerifyRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255, description="Phone number or email of the account")
    code: str = Field(pattern=r"^[0-9]{4,8}$", description="The code received by SMS")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserSummary
