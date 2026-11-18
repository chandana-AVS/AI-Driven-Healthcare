"""Central authorization rules for patient data.

- A patient may access only their own data.
- A healthcare worker may access a patient's data only when the worker is VERIFIED and an
  ACTIVE PatientAccess grant exists.
- Administrators manage users, grants and content, but do not read patient medical data.
"""
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import HealthcareWorkerProfile, PatientAccess, PatientProfile, User
from app.models.enums import AccessStatus, UserRole, VerificationStatus

_FORBIDDEN = HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this patient")


def get_patient_or_404(db: Session, patient_id: uuid.UUID) -> PatientProfile:
    patient = db.get(PatientProfile, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


def has_active_grant(db: Session, patient_id: uuid.UUID, worker_id: uuid.UUID) -> bool:
    return (
        db.query(PatientAccess.id)
        .filter(
            PatientAccess.patient_id == patient_id,
            PatientAccess.healthcare_worker_id == worker_id,
            PatientAccess.access_status == AccessStatus.ACTIVE.value,
        )
        .first()
        is not None
    )


def authorize_patient_access(db: Session, user: User, patient_id: uuid.UUID) -> PatientProfile:
    """Return the patient profile if `user` may access it, otherwise raise 403/404."""
    if user.role == UserRole.PATIENT.value:
        own = db.query(PatientProfile).filter(PatientProfile.user_id == user.id).first()
        if own is None or own.id != patient_id:
            raise _FORBIDDEN
        return own

    if user.role == UserRole.HEALTHCARE_WORKER.value:
        worker = db.query(HealthcareWorkerProfile).filter(HealthcareWorkerProfile.user_id == user.id).first()
        if worker is None or worker.verification_status != VerificationStatus.VERIFIED.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your healthcare worker account has not been verified by an administrator yet",
            )
        if not has_active_grant(db, patient_id, worker.id):
            raise _FORBIDDEN
        return get_patient_or_404(db, patient_id)

    raise _FORBIDDEN


def grant_access(
    db: Session, patient: PatientProfile, worker: HealthcareWorkerProfile, granted_by: User
) -> PatientAccess:
    if worker.verification_status != VerificationStatus.VERIFIED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Access can only be granted to verified healthcare workers"
        )
    existing = (
        db.query(PatientAccess)
        .filter(
            PatientAccess.patient_id == patient.id,
            PatientAccess.healthcare_worker_id == worker.id,
            PatientAccess.access_status == AccessStatus.ACTIVE.value,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This healthcare worker already has access")
    grant = PatientAccess(
        patient_id=patient.id,
        healthcare_worker_id=worker.id,
        access_status=AccessStatus.ACTIVE.value,
        granted_by=granted_by.id,
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    return grant


def revoke_access(db: Session, grant: PatientAccess) -> PatientAccess:
    if grant.access_status != AccessStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Access is already revoked")
    grant.access_status = AccessStatus.REVOKED.value
    grant.revoked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(grant)
    return grant


def serialize_grant(grant: PatientAccess) -> dict:
    return {
        "id": grant.id,
        "patient_id": grant.patient_id,
        "patient_name": grant.patient.user.full_name,
        "healthcare_worker_id": grant.healthcare_worker_id,
        "worker_name": grant.worker.user.full_name,
        "worker_designation": grant.worker.designation,
        "worker_organization": grant.worker.organization,
        "access_status": grant.access_status,
        "granted_by": grant.granted_by,
        "created_at": grant.created_at,
        "revoked_at": grant.revoked_at,
    }
