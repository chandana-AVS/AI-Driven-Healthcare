from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_worker, get_verified_worker
from app.models import HealthcareRecord, HealthcareWorkerProfile, MedicalDocument, PatientAccess, PatientProfile
from app.models.enums import AccessStatus
from app.schemas.patient import AuthorizedPatientOut
from app.schemas.user import WorkerMe, WorkerProfileUpdate

router = APIRouter(prefix="/healthcare-workers", tags=["Healthcare Workers"])


@router.get("/me", response_model=WorkerMe)
def get_my_worker_profile(worker: HealthcareWorkerProfile = Depends(get_current_worker)):
    return {"user": worker.user, "profile": worker}


@router.patch("/me", response_model=WorkerMe)
def update_my_worker_profile(
    data: WorkerProfileUpdate,
    worker: HealthcareWorkerProfile = Depends(get_current_worker),
    db: Session = Depends(get_db),
):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(worker, field, value)
    db.commit()
    db.refresh(worker)
    return {"user": worker.user, "profile": worker}


@router.get("/me/patients", response_model=list[AuthorizedPatientOut])
def list_authorized_patients(
    worker: HealthcareWorkerProfile = Depends(get_verified_worker), db: Session = Depends(get_db)
):
    grants = (
        db.query(PatientAccess)
        .filter(
            PatientAccess.healthcare_worker_id == worker.id,
            PatientAccess.access_status == AccessStatus.ACTIVE.value,
        )
        .order_by(PatientAccess.created_at.desc())
        .all()
    )
    patient_ids = [g.patient_id for g in grants]
    doc_counts = dict(
        db.query(MedicalDocument.patient_id, func.count(MedicalDocument.id))
        .filter(MedicalDocument.patient_id.in_(patient_ids))
        .group_by(MedicalDocument.patient_id)
        .all()
    ) if patient_ids else {}
    rec_counts = dict(
        db.query(HealthcareRecord.patient_id, func.count(HealthcareRecord.id))
        .filter(HealthcareRecord.patient_id.in_(patient_ids))
        .group_by(HealthcareRecord.patient_id)
        .all()
    ) if patient_ids else {}

    result = []
    for g in grants:
        p: PatientProfile = g.patient
        result.append(
            AuthorizedPatientOut(
                patient_id=p.id,
                full_name=p.user.full_name,
                email=p.user.email,
                phone=p.user.phone,
                preferred_language=p.user.preferred_language,
                date_of_birth=p.date_of_birth,
                gender=p.gender,
                access_granted_at=g.created_at,
                document_count=doc_counts.get(p.id, 0),
                record_count=rec_counts.get(p.id, 0),
            )
        )
    return result
