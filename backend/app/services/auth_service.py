from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models import AdminProfile, HealthcareWorkerProfile, PatientProfile, User
from app.models.enums import UserRole, VerificationStatus
from app.schemas.auth import AdminRegister, HealthcareWorkerRegister, PatientRegister
from app.services.otp_service import try_issue_otp
from app.utils.security import DUMMY_HASH, hash_password, verify_password
from app.utils.validators import normalize_phone

# The frontend matches on this exact string to send the user to the verification page.
PHONE_NOT_VERIFIED = "Phone number not verified"


def ensure_unique_contact(db: Session, email: str | None, phone: str | None, exclude_user_id=None) -> None:
    conditions = []
    if email:
        conditions.append(User.email == email.lower())
    if phone:
        conditions.append(User.phone == phone)
    if not conditions:
        return
    query = db.query(User).filter(or_(*conditions))
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    if query.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email or phone number already exists",
        )


def _new_user(data: PatientRegister | HealthcareWorkerRegister | AdminRegister, role: UserRole) -> User:
    return User(
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        password_hash=hash_password(data.password),
        role=role.value,
        preferred_language=data.preferred_language,
        is_active=True,
        is_verified=False,
    )


def register_patient(db: Session, data: PatientRegister) -> User:
    ensure_unique_contact(db, data.email, data.phone)
    user = _new_user(data, UserRole.PATIENT)
    user.patient_profile = PatientProfile()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def register_healthcare_worker(db: Session, data: HealthcareWorkerRegister) -> User:
    ensure_unique_contact(db, data.email, data.phone)
    user = _new_user(data, UserRole.HEALTHCARE_WORKER)
    user.worker_profile = HealthcareWorkerProfile(
        designation=data.designation,
        organization=data.organization,
        verification_status=VerificationStatus.PENDING.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def register_admin(db: Session, data: AdminRegister) -> User:
    ensure_unique_contact(db, data.email, data.phone)
    duplicate = (
        db.query(AdminProfile)
        .filter(
            func.lower(AdminProfile.hospital_name) == data.hospital_name.lower(),
            AdminProfile.employee_id == data.employee_id,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An administrator with this employee ID is already registered for this hospital",
        )
    user = _new_user(data, UserRole.ADMIN)  # is_verified=False → no admin powers until approved
    user.admin_profile = AdminProfile(
        employee_id=data.employee_id,
        hospital_name=data.hospital_name,
        verification_status=VerificationStatus.PENDING.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def find_user_by_identifier(db: Session, identifier: str) -> User | None:
    identifier = identifier.strip()
    if "@" in identifier:
        return db.query(User).filter(User.email == identifier.lower()).first()
    try:
        phone = normalize_phone(identifier)
    except ValueError:
        return None
    return db.query(User).filter(User.phone == phone).first() if phone else None


def authenticate(db: Session, identifier: str, password: str) -> User:
    user = find_user_by_identifier(db, identifier)
    if user is None:
        verify_password(password, DUMMY_HASH)  # equalise timing
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
    if user.phone and not user.phone_verified:
        # The password was correct, so send a fresh code (skipped silently while in the resend cooldown).
        try_issue_otp(db, user)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=PHONE_NOT_VERIFIED)
    return user
