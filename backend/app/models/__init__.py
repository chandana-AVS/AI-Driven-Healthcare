"""ORM models. Importing this package registers every table on Base.metadata."""
from app.models.enums import (  # noqa: F401
    AccessStatus,
    ContentCategory,
    ContentStatus,
    DocumentType,
    LanguageCode,
    ProcessingStatus,
    RecordType,
    UserRole,
    VerificationStatus,
)
from app.models.user import User  # noqa: F401
from app.models.patient import PatientProfile  # noqa: F401
from app.models.healthcare_worker import HealthcareWorkerProfile  # noqa: F401
from app.models.admin_profile import AdminProfile  # noqa: F401
from app.models.document import MedicalDocument  # noqa: F401
from app.models.healthcare_record import HealthcareRecord  # noqa: F401
from app.models.healthcare_content import HealthcareContent  # noqa: F401
from app.models.patient_access import PatientAccess  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.phone_otp import PhoneOTP  # noqa: F401
from app.models.document_analysis import DocumentAnalysis  # noqa: F401
