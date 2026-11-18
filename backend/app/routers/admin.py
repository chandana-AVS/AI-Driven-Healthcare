import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.dependencies import require_admin, require_roles
from app.models import (
    AdminProfile,
    AuditLog,
    HealthcareContent,
    HealthcareWorkerProfile,
    MedicalDocument,
    PatientAccess,
    PatientProfile,
    User,
)
from app.models.enums import ContentStatus, UserRole, VerificationStatus
from app.schemas.ai import ContentTranslateRequest
from app.schemas.healthcare_content import ContentCreate, ContentOut, ContentUpdate
from app.schemas.patient import AccessGrantOut, AdminAccessGrantCreate
from app.schemas.user import AdminMe, AdminProfileOut, AdminUserOut, AdminUserStatusUpdate, WorkerProfileOut
from app.services import access_service, knowledge_service
from app.services.audit_service import log_event

router = APIRouter(prefix="/admin", tags=["Administration"])


class AdminStats(BaseModel):
    total_patients: int
    total_healthcare_workers: int
    pending_verifications: int
    pending_admin_verifications: int
    verified_workers: int
    total_documents: int
    active_access_grants: int
    published_content: int
    total_content: int


class VerificationUpdate(BaseModel):
    verification_status: VerificationStatus


class AuditLogOut(BaseModel):
    id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    actor_name: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    patient_id: Optional[uuid.UUID] = None
    ip_address: Optional[str] = None
    created_at: str


def _admin_user_out(user: User) -> AdminUserOut:
    out = AdminUserOut.model_validate(user)
    if user.worker_profile:
        out.worker_profile = WorkerProfileOut.model_validate(user.worker_profile)
    if user.admin_profile:
        out.admin_profile = AdminProfileOut.model_validate(user.admin_profile)
    if user.patient_profile:
        out.patient_profile_id = user.patient_profile.id
    return out


# ----------------------------------------------------------------------------- own status (pending admins allowed)
@router.get("/me", response_model=AdminMe)
def admin_me(user: User = Depends(require_roles(UserRole.ADMIN))):
    """Lets a self-registered admin see whether they have been approved yet."""
    if user.admin_profile is None:  # bootstrap admin created with scripts/create_admin.py
        vs = VerificationStatus.VERIFIED.value if user.is_verified else VerificationStatus.PENDING.value
    else:
        vs = user.admin_profile.verification_status
    return AdminMe(user=user, profile=user.admin_profile, verification_status=vs)


# ----------------------------------------------------------------------------- dashboard
@router.get("/stats", response_model=AdminStats)
def stats(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    def count_users(role: UserRole) -> int:
        return db.query(func.count(User.id)).filter(User.role == role.value).scalar() or 0

    def count_workers(vs: VerificationStatus) -> int:
        return (
            db.query(func.count(HealthcareWorkerProfile.id))
            .filter(HealthcareWorkerProfile.verification_status == vs.value)
            .scalar()
            or 0
        )

    return AdminStats(
        total_patients=count_users(UserRole.PATIENT),
        total_healthcare_workers=count_users(UserRole.HEALTHCARE_WORKER),
        pending_verifications=count_workers(VerificationStatus.PENDING),
        pending_admin_verifications=db.query(func.count(AdminProfile.id))
        .filter(AdminProfile.verification_status == VerificationStatus.PENDING.value).scalar() or 0,
        verified_workers=count_workers(VerificationStatus.VERIFIED),
        total_documents=db.query(func.count(MedicalDocument.id)).scalar() or 0,
        active_access_grants=db.query(func.count(PatientAccess.id)).filter(PatientAccess.access_status == "ACTIVE").scalar() or 0,
        published_content=db.query(func.count(HealthcareContent.id))
        .filter(HealthcareContent.status == ContentStatus.PUBLISHED.value).scalar() or 0,
        total_content=db.query(func.count(HealthcareContent.id)).scalar() or 0,
    )


# ----------------------------------------------------------------------------- user management
@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    role: Optional[UserRole] = Query(None),
    verification_status: Optional[VerificationStatus] = Query(None),
    search: Optional[str] = Query(None, max_length=100),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(User).options(
        selectinload(User.worker_profile), selectinload(User.patient_profile), selectinload(User.admin_profile)
    )
    if role:
        query = query.filter(User.role == role.value)
    if verification_status:
        # Matches healthcare workers AND self-registered admins with this verification status.
        query = (
            query.outerjoin(HealthcareWorkerProfile, HealthcareWorkerProfile.user_id == User.id)
            .outerjoin(AdminProfile, AdminProfile.user_id == User.id)
            .filter(
                (HealthcareWorkerProfile.verification_status == verification_status.value)
                | (AdminProfile.verification_status == verification_status.value)
            )
        )
    if search:
        like = f"%{search.strip()}%"
        query = query.filter((User.full_name.ilike(like)) | (User.email.ilike(like)) | (User.phone.ilike(like)))
    return [_admin_user_out(u) for u in query.order_by(User.created_at.desc()).limit(500).all()]


@router.patch("/users/{user_id}/status", response_model=AdminUserOut)
def set_user_status(
    user_id: uuid.UUID,
    data: AdminUserStatusUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id and not data.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate your own account")
    user.is_active = data.is_active
    db.commit()
    db.refresh(user)
    log_event(db, action="USER_ACTIVATE" if data.is_active else "USER_DEACTIVATE", resource_type="USER",
              actor=admin, resource_id=user.id, request=request)
    return _admin_user_out(user)


@router.patch("/healthcare-workers/{worker_id}/verification", response_model=AdminUserOut)
def set_worker_verification(
    worker_id: uuid.UUID,
    data: VerificationUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    worker = db.get(HealthcareWorkerProfile, worker_id)
    if worker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Healthcare worker not found")
    worker.verification_status = data.verification_status.value
    worker.user.is_verified = data.verification_status == VerificationStatus.VERIFIED
    db.commit()
    db.refresh(worker)
    log_event(db, action=f"WORKER_{data.verification_status.value}", resource_type="HEALTHCARE_WORKER",
              actor=admin, resource_id=worker.id, request=request)
    return _admin_user_out(worker.user)


@router.patch("/admins/{admin_profile_id}/verification", response_model=AdminUserOut)
def set_admin_verification(
    admin_profile_id: uuid.UUID,
    data: VerificationUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Approve or reject a self-registered administrator (checks employee ID + hospital offline)."""
    profile = db.get(AdminProfile, admin_profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator registration not found")
    if profile.user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot change your own verification")
    profile.verification_status = data.verification_status.value
    profile.user.is_verified = data.verification_status == VerificationStatus.VERIFIED
    db.commit()
    db.refresh(profile)
    log_event(db, action=f"ADMIN_{data.verification_status.value}", resource_type="ADMIN",
              actor=admin, resource_id=profile.id, request=request)
    return _admin_user_out(profile.user)


# ----------------------------------------------------------------------------- access grants
@router.get("/access",response_model=list[AccessGrantOut])
def list_access_grants(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    grants = db.query(PatientAccess).order_by(PatientAccess.created_at.desc()).limit(500).all()
    return [access_service.serialize_grant(g) for g in grants]


@router.post("/access", response_model=AccessGrantOut, status_code=status.HTTP_201_CREATED)
def admin_grant_access(
    data: AdminAccessGrantCreate, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    patient = access_service.get_patient_or_404(db, data.patient_id)
    worker = db.get(HealthcareWorkerProfile, data.healthcare_worker_id)
    if worker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Healthcare worker not found")
    grant = access_service.grant_access(db, patient, worker, admin)
    log_event(db, action="ACCESS_GRANT", resource_type="PATIENT_ACCESS", actor=admin,
              resource_id=grant.id, patient_id=patient.id, request=request)
    return access_service.serialize_grant(grant)


@router.delete("/access/{grant_id}", response_model=AccessGrantOut)
def admin_revoke_access(
    grant_id: uuid.UUID, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    grant = db.get(PatientAccess, grant_id)
    if grant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access grant not found")
    grant = access_service.revoke_access(db, grant)
    log_event(db, action="ACCESS_REVOKE", resource_type="PATIENT_ACCESS", actor=admin,
              resource_id=grant.id, patient_id=grant.patient_id, request=request)
    return access_service.serialize_grant(grant)


# ----------------------------------------------------------------------------- content management
@router.get("/content", response_model=list[ContentOut])
def admin_list_content(
    status_filter: Optional[ContentStatus] = Query(None, alias="status"),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(HealthcareContent)
    if status_filter:
        query = query.filter(HealthcareContent.status == status_filter.value)
    return query.order_by(HealthcareContent.created_at.desc()).all()


@router.post("/content", response_model=ContentOut, status_code=status.HTTP_201_CREATED)
def create_content(
    data: ContentCreate, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    item = HealthcareContent(
        title=data.title.strip(),
        body=data.body,
        category=data.category.value,
        content_type=data.content_type.value,
        language_code=data.language_code,
        status=data.status.value,
        created_by=admin.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    log_event(db, action="CONTENT_CREATE", resource_type="CONTENT", actor=admin, resource_id=item.id, request=request)
    return item


@router.patch("/content/{content_id}", response_model=ContentOut)
def update_content(
    content_id: uuid.UUID,
    data: ContentUpdate,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = db.get(HealthcareContent, content_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        setattr(item, field, value.value if hasattr(value, "value") else value)
    db.commit()
    db.refresh(item)
    log_event(db, action="CONTENT_UPDATE", resource_type="CONTENT", actor=admin, resource_id=item.id, request=request)
    return item


@router.post("/content/{content_id}/translate", response_model=list[ContentOut], status_code=status.HTTP_201_CREATED)
def translate_content(
    content_id: uuid.UUID,
    data: ContentTranslateRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """AI-translate an item into other languages. Copies are created as DRAFT for review before publishing."""
    item = db.get(HealthcareContent, content_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    created = knowledge_service.translate_item(db, item, data.languages, admin)
    log_event(db, action="AI_CONTENT_TRANSLATE", resource_type="CONTENT", actor=admin, resource_id=item.id,
              request=request, details=",".join(c.language_code for c in created))
    return created


@router.delete("/content/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content(
    content_id: uuid.UUID, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    item = db.get(HealthcareContent, content_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    db.delete(item)
    db.commit()
    log_event(db, action="CONTENT_DELETE", resource_type="CONTENT", actor=admin, resource_id=content_id, request=request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----------------------------------------------------------------------------- audit
@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(
    limit: int = Query(100, ge=1, le=500),
    action: Optional[str] = Query(None, max_length=60),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog, User.full_name).outerjoin(User, AuditLog.actor_id == User.id)
    if action:
        query = query.filter(AuditLog.action == action.upper())
    rows = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    return [
        AuditLogOut(
            id=log.id,
            actor_id=log.actor_id,
            actor_name=name,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            patient_id=log.patient_id,
            ip_address=log.ip_address,
            created_at=log.created_at.isoformat(),
        )
        for log, name in rows
    ]
