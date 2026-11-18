import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import HealthcareRecord, User
from app.schemas.healthcare_record import RecordOut
from app.services import access_service, record_service
from app.services.audit_service import log_event

router = APIRouter(prefix="/records", tags=["Healthcare Records"])


@router.get("/{record_id}", response_model=RecordOut)
def get_record(
    record_id: uuid.UUID, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    record = db.get(HealthcareRecord, record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    try:
        access_service.authorize_patient_access(db, user, record.patient_id)
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    log_event(db, action="RECORD_VIEW", resource_type="HEALTHCARE_RECORD", actor=user,
              resource_id=record.id, patient_id=record.patient_id, request=request)
    return record_service.to_record_out(record)
