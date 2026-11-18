"""Shared enumerations. Stored as VARCHAR in the DB so new values never need an enum migration."""
from enum import Enum


class UserRole(str, Enum):
    PATIENT = "PATIENT"
    HEALTHCARE_WORKER = "HEALTHCARE_WORKER"
    ADMIN = "ADMIN"


class LanguageCode(str, Enum):
    """Supported languages. Reused by future translation / voice modules."""
    EN = "en"
    TE = "te"
    HI = "hi"
    TA = "ta"
    KN = "kn"
    ML = "ml"


LANGUAGE_NAMES: dict[str, dict[str, str]] = {
    "en": {"name": "English", "native": "English"},
    "te": {"name": "Telugu", "native": "తెలుగు"},
    "hi": {"name": "Hindi", "native": "हिन्दी"},
    "ta": {"name": "Tamil", "native": "தமிழ்"},
    "kn": {"name": "Kannada", "native": "ಕನ್ನಡ"},
    "ml": {"name": "Malayalam", "native": "മലയാളം"},
}


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"


class DocumentType(str, Enum):
    PRESCRIPTION = "PRESCRIPTION"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    DIAGNOSTIC_REPORT = "DIAGNOSTIC_REPORT"
    LAB_REPORT = "LAB_REPORT"
    OTHER = "OTHER"


class ProcessingStatus(str, Enum):
    """UPLOADED in Milestone 1; later milestones move documents through OCR/NLP/translation."""
    UPLOADED = "UPLOADED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class RecordType(str, Enum):
    CONSULTATION = "CONSULTATION"
    DIAGNOSIS = "DIAGNOSIS"
    PRESCRIPTION = "PRESCRIPTION"
    DISCHARGE = "DISCHARGE"
    LAB_RESULT = "LAB_RESULT"
    IMMUNIZATION = "IMMUNIZATION"
    DOCUMENT_UPLOAD = "DOCUMENT_UPLOAD"
    NOTE = "NOTE"
    OTHER = "OTHER"


class ContentCategory(str, Enum):
    GENERAL_HEALTH = "GENERAL_HEALTH"
    MATERNAL_HEALTH = "MATERNAL_HEALTH"
    CHILD_HEALTHCARE = "CHILD_HEALTHCARE"
    ELDERLY_CARE = "ELDERLY_CARE"
    PREVENTIVE_HEALTHCARE = "PREVENTIVE_HEALTHCARE"
    COMMON_DISEASES = "COMMON_DISEASES"


class ContentStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    INACTIVE = "INACTIVE"


class ContentType(str, Enum):
    """Knowledge-base entry kind (Milestone 2)."""
    ARTICLE = "ARTICLE"
    FAQ = "FAQ"
    DISEASE_INFO = "DISEASE_INFO"


class AnalysisStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TextType(str, Enum):
    """What kind of medical text is being translated, so the AI keeps the right structure."""
    PRESCRIPTION = "PRESCRIPTION"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    INSTRUCTIONS = "INSTRUCTIONS"
    GENERAL = "GENERAL"


class AccessStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
