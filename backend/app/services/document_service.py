import uuid
from datetime import date

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models import MedicalDocument, PatientProfile, User
from app.models.enums import DocumentType, ProcessingStatus, UserRole
from app.services.access_service import authorize_patient_access
from app.services.storage_service import get_storage
from app.utils.file_handler import read_and_validate_upload


async def upload_document(
    db: Session,
    *,
    patient: PatientProfile,
    uploader: User,
    file: UploadFile,
    document_type: DocumentType,
    document_date: date | None,
    document_name: str | None,
) -> MedicalDocument:
    validated = await read_and_validate_upload(file)
    if document_date and document_date > date.today():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Document date cannot be in the future")

    storage = get_storage()
    storage_key = storage.save(patient.id, validated.extension, validated.content)
    doc = MedicalDocument(
        patient_id=patient.id,
        uploaded_by=uploader.id,
        document_name=(document_name.strip()[:255] if document_name and document_name.strip() else validated.display_name),
        document_type=document_type.value,
        storage_key=storage_key,
        mime_type=validated.mime_type,
        file_size=len(validated.content),
        document_date=document_date,
        processing_status=ProcessingStatus.UPLOADED.value,
    )
    db.add(doc)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(storage_key)
        raise
    db.refresh(doc)
    return doc


def list_documents(db: Session, patient_id: uuid.UUID, document_type: DocumentType | None = None) -> list[MedicalDocument]:
    query = db.query(MedicalDocument).filter(MedicalDocument.patient_id == patient_id)
    if document_type:
        query = query.filter(MedicalDocument.document_type == document_type.value)
    return query.order_by(MedicalDocument.created_at.desc()).all()


def get_authorized_document(db: Session, user: User, document_id: uuid.UUID) -> MedicalDocument:
    doc = db.get(MedicalDocument, document_id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    try:
        authorize_patient_access(db, user, doc.patient_id)
    except HTTPException:
        # Do not reveal whether the document exists to unauthorized users.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return doc


def delete_document(db: Session, user: User, doc: MedicalDocument) -> None:
    # Patients may delete their own documents; workers only documents they uploaded.
    if user.role == UserRole.HEALTHCARE_WORKER.value and doc.uploaded_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Healthcare workers can only delete documents they uploaded"
        )
    key = doc.storage_key
    db.delete(doc)
    db.commit()
    get_storage().delete(key)
