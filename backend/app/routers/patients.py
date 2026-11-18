import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_patient, get_current_user
from app.models import HealthcareWorkerProfile, PatientAccess, PatientProfile, User
from app.models.enums import AccessStatus, DocumentType, UserRole, VerificationStatus
from app.schemas.document import DocumentList, DocumentOut
from app.schemas.healthcare_record import PatientHistory, RecordCreate, RecordOut
from app.schemas.patient import AccessGrantCreate, AccessGrantOut, PatientProfileUpdate, WorkerDirectoryEntry
from app.schemas.user import PatientMe
from app.services import access_service, document_service, record_service
from app.services.audit_service import log_event
from app.utils.validators import normalize_phone

router = APIRouter(prefix="/patients", tags=["Patients"])


# ----------------------------------------------------------------------------- own profile (/me)
@router.get("/me", response_model=PatientMe)
def get_my_patient_profile(patient: PatientProfile = Depends(get_current_patient)):
    return {"user": patient.user, "profile": patient}


@router.patch("/me", response_model=PatientMe)
def update_my_patient_profile(
    data: PatientProfileUpdate, patient: PatientProfile = Depends(get_current_patient), db: Session = Depends(get_db)
):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return {"user": patient.user, "profile": patient}


# ----------------------------------------------------------------------------- own documents
@router.post("/me/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_my_document(
    request: Request,
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    document_date: Optional[date] = Form(None),
    document_name: Optional[str] = Form(None, max_length=255),
    patient: PatientProfile = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    doc = await document_service.upload_document(
        db,
        patient=patient,
        uploader=patient.user,
        file=file,
        document_type=document_type,
        document_date=document_date,
        document_name=document_name,
    )
    log_event(db, action="DOCUMENT_UPLOAD", resource_type="DOCUMENT", actor=patient.user,
              resource_id=doc.id, patient_id=patient.id, request=request)
    return doc


@router.get("/me/documents", response_model=DocumentList)
def list_my_documents(
    document_type: Optional[DocumentType] = Query(None),
    patient: PatientProfile = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    items = document_service.list_documents(db, patient.id, document_type)
    return {"items": items, "total": len(items)}


# ----------------------------------------------------------------------------- own records / history
@router.get("/me/records", response_model=list[RecordOut])
def list_my_records(patient: PatientProfile = Depends(get_current_patient), db: Session = Depends(get_db)):
    return [record_service.to_record_out(r) for r in record_service.list_records(db, patient.id)]


@router.get("/me/history", response_model=PatientHistory)
def my_history(patient: PatientProfile = Depends(get_current_patient), db: Session = Depends(get_db)):
    return record_service.build_history(db, patient)


# ----------------------------------------------------------------------------- access grants (patient-controlled)
@router.get("/me/workers", response_model=list[WorkerDirectoryEntry])
def verified_worker_directory(
    search: Optional[str] = Query(None, max_length=100),
    _: PatientProfile = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    """Verified healthcare workers a patient can choose to grant access to."""
    query = (
        db.query(HealthcareWorkerProfile)
        .join(User, HealthcareWorkerProfile.user_id == User.id)
        .filter(
            HealthcareWorkerProfile.verification_status == VerificationStatus.VERIFIED.value,
            User.is_active.is_(True),
        )
    )
    if search:
        like = f"%{search.strip()}%"
        query = query.filter(or_(User.full_name.ilike(like), HealthcareWorkerProfile.organization.ilike(like)))
    workers = query.order_by(User.full_name).limit(50).all()
    return [
        WorkerDirectoryEntry(
            healthcare_worker_id=w.id, full_name=w.user.full_name, designation=w.designation, organization=w.organization
        )
        for w in workers
    ]


@router.get("/me/access", response_model=list[AccessGrantOut])
def list_my_access_grants(patient: PatientProfile = Depends(get_current_patient), db: Session = Depends(get_db)):
    grants = (
        db.query(PatientAccess)
        .filter(PatientAccess.patient_id == patient.id)
        .order_by(PatientAccess.created_at.desc())
        .all()
    )
    return [access_service.serialize_grant(g) for g in grants]


@router.post("/me/access", response_model=AccessGrantOut, status_code=status.HTTP_201_CREATED)
def grant_worker_access(
    data: AccessGrantCreate,
    request: Request,
    patient: PatientProfile = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    worker: HealthcareWorkerProfile | None = None
    if data.healthcare_worker_id:
        worker = db.get(HealthcareWorkerProfile, data.healthcare_worker_id)
    elif data.worker_identifier:
        ident = data.worker_identifier.strip()
        if "@" in ident:
            cond = User.email == ident.lower()
        else:
            try:
                cond = User.phone == normalize_phone(ident)
            except ValueError:
                cond = None
        if cond is not None:
            worker = (
                db.query(HealthcareWorkerProfile)
                .join(User, HealthcareWorkerProfile.user_id == User.id)
                .filter(cond, User.role == UserRole.HEALTHCARE_WORKER.value)
                .first()
            )
    else:
        raise HTTPException(status_code=422, detail="Provide healthcare_worker_id or worker_identifier")

    if worker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Healthcare worker not found")
    grant = access_service.grant_access(db, patient, worker, patient.user)
    log_event(db, action="ACCESS_GRANT", resource_type="PATIENT_ACCESS", actor=patient.user,
              resource_id=grant.id, patient_id=patient.id, request=request)
    return access_service.serialize_grant(grant)


@router.delete("/me/access/{grant_id}", response_model=AccessGrantOut)
def revoke_worker_access(
    grant_id: uuid.UUID,
    request: Request,
    patient: PatientProfile = Depends(get_current_patient),
    db: Session = Depends(get_db),
):
    grant = db.get(PatientAccess, grant_id)
    if grant is None or grant.patient_id != patient.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access grant not found")
    grant = access_service.revoke_access(db, grant)
    log_event(db, action="ACCESS_REVOKE", resource_type="PATIENT_ACCESS", actor=patient.user,
              resource_id=grant.id, patient_id=patient.id, request=request)
    return access_service.serialize_grant(grant)


# ----------------------------------------------------------------------------- patient-specific routes (authorized)
@router.get("/{patient_id}/documents", response_model=DocumentList)
def list_patient_documents(
    patient_id: uuid.UUID,
    request: Request,
    document_type: Optional[DocumentType] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patient = access_service.authorize_patient_access(db, user, patient_id)
    items = document_service.list_documents(db, patient.id, document_type)
    log_event(db, action="DOCUMENT_LIST", resource_type="DOCUMENT", actor=user, patient_id=patient.id, request=request)
    return {"items": items, "total": len(items)}


@router.post("/{patient_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_patient_document(
    patient_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    document_date: Optional[date] = Form(None),
    document_name: Optional[str] = Form(None, max_length=255),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patient = access_service.authorize_patient_access(db, user, patient_id)
    doc = await document_service.upload_document(
        db, patient=patient, uploader=user, file=file, document_type=document_type,
        document_date=document_date, document_name=document_name,
    )
    log_event(db, action="DOCUMENT_UPLOAD", resource_type="DOCUMENT", actor=user,
              resource_id=doc.id, patient_id=patient.id, request=request)
    return doc


@router.get("/{patient_id}/records", response_model=list[RecordOut])
def list_patient_records(
    patient_id: uuid.UUID, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    patient = access_service.authorize_patient_access(db, user, patient_id)
    log_event(db, action="RECORD_LIST", resource_type="HEALTHCARE_RECORD", actor=user,
              patient_id=patient.id, request=request)
    return [record_service.to_record_out(r) for r in record_service.list_records(db, patient.id)]


@router.post("/{patient_id}/records", response_model=RecordOut, status_code=status.HTTP_201_CREATED)
def create_patient_record(
    patient_id: uuid.UUID,
    data: RecordCreate,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    patient = access_service.authorize_patient_access(db, user, patient_id)
    record = record_service.create_record(db, patient, user, data)
    log_event(db, action="RECORD_CREATE", resource_type="HEALTHCARE_RECORD", actor=user,
              resource_id=record.id, patient_id=patient.id, request=request)
    return record_service.to_record_out(record)


@router.get("/{patient_id}/history", response_model=PatientHistory)
def patient_history(
    patient_id: uuid.UUID, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    patient = access_service.authorize_patient_access(db, user, patient_id)
    log_event(db, action="HISTORY_VIEW", resource_type="PATIENT", actor=user, patient_id=patient.id, request=request)
    return record_service.build_history(db, patient)
