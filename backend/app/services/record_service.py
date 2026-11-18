import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models import HealthcareRecord, MedicalDocument, PatientProfile, User
from app.schemas.document import DocumentOut
from app.schemas.healthcare_record import HistoryEntry, PatientHistory, RecordCreate, RecordOut


def to_record_out(record: HealthcareRecord) -> RecordOut:
    out = RecordOut.model_validate(record)
    out.created_by_name = record.creator.full_name if record.creator else None
    return out


def create_record(db: Session, patient: PatientProfile, author: User, data: RecordCreate) -> HealthcareRecord:
    if data.document_id is not None:
        doc = db.get(MedicalDocument, data.document_id)
        if doc is None or doc.patient_id != patient.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Linked document does not belong to this patient",
            )
    record = HealthcareRecord(
        patient_id=patient.id,
        created_by=author.id,
        record_type=data.record_type.value,
        title=data.title.strip(),
        description=data.description,
        record_date=data.record_date,
        document_id=data.document_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_records(db: Session, patient_id: uuid.UUID) -> list[HealthcareRecord]:
    """Chronological order: newest record_date first, then newest created."""
    return (
        db.query(HealthcareRecord)
        .options(joinedload(HealthcareRecord.creator))
        .filter(HealthcareRecord.patient_id == patient_id)
        .order_by(HealthcareRecord.record_date.desc(), HealthcareRecord.created_at.desc())
        .all()
    )


def build_history(db: Session, patient: PatientProfile) -> PatientHistory:
    """Merge records and documents into one chronological timeline (newest first)."""
    entries: list[HistoryEntry] = []
    for record in list_records(db, patient.id):
        entries.append(
            HistoryEntry(
                entry_type="RECORD",
                date=record.record_date,
                timestamp=record.created_at,
                title=record.title,
                category=record.record_type,
                description=record.description,
                record=to_record_out(record),
            )
        )
    docs = db.query(MedicalDocument).filter(MedicalDocument.patient_id == patient.id).all()
    for doc in docs:
        entries.append(
            HistoryEntry(
                entry_type="DOCUMENT",
                date=doc.document_date or doc.created_at.date(),
                timestamp=doc.created_at,
                title=doc.document_name,
                category=doc.document_type,
                status=doc.processing_status,
                document=DocumentOut.model_validate(doc),
            )
        )
    entries.sort(key=lambda e: (e.date, e.timestamp.replace(tzinfo=None)), reverse=True)
    return PatientHistory(patient_id=patient.id, patient_name=patient.user.full_name, entries=entries)
