"""Background AI analysis of uploaded medical documents (one analysis per document per language)."""
import logging
import uuid
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import DocumentAnalysis, MedicalDocument, User
from app.models.enums import AnalysisStatus, ProcessingStatus
from app.models.mixins import utcnow
from app.services import ai_service
from app.services.storage_service import StorageError, get_storage

logger = logging.getLogger("analysis")

STALE_AFTER = timedelta(minutes=15)  # a PROCESSING row older than this is assumed to have crashed


def _aware(dt):
    from datetime import timezone
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_analysis(db: Session, document_id: uuid.UUID, language: str) -> DocumentAnalysis | None:
    return (db.query(DocumentAnalysis)
            .filter(DocumentAnalysis.document_id == document_id, DocumentAnalysis.language_code == language).first())


def request_analysis(db: Session, doc: MedicalDocument, language: str, user: User, force: bool) -> tuple[DocumentAnalysis, bool]:
    """Create or reuse an analysis row. Returns (row, needs_run)."""
    if not ai_service.ai_enabled():
        raise HTTPException(status_code=503, detail=ai_service.NOT_CONFIGURED)
    row = get_analysis(db, doc.id, language)
    if row is not None:
        busy = row.status in (AnalysisStatus.PENDING.value, AnalysisStatus.PROCESSING.value)
        if busy and utcnow() - _aware(row.updated_at) < STALE_AFTER:
            return row, False
        if row.status == AnalysisStatus.COMPLETED.value and not force:
            return row, False
    else:
        row = DocumentAnalysis(document_id=doc.id, language_code=language)
        db.add(row)
    ai_service.enforce_daily_limit(db, user)
    row.status = AnalysisStatus.PENDING.value
    row.error = None
    row.requested_by = user.id
    row.updated_at = utcnow()
    doc.processing_status = ProcessingStatus.QUEUED.value
    db.commit()
    db.refresh(row)
    return row, True


def run_analysis(analysis_id: uuid.UUID) -> None:
    """Runs after the HTTP response is sent (FastAPI BackgroundTasks), with its own DB session."""
    with SessionLocal() as db:
        row = db.get(DocumentAnalysis, analysis_id)
        if row is None:
            return
        doc = db.get(MedicalDocument, row.document_id)
        if doc is None:
            return
        row.status = AnalysisStatus.PROCESSING.value
        doc.processing_status = ProcessingStatus.PROCESSING.value
        db.commit()
        try:
            content = get_storage().open_path(doc.storage_key).read_bytes()
            insight = ai_service.analyze_document_file(content, doc.mime_type, doc.document_type, row.language_code)
            row.result_json = insight.model_dump_json()
            row.status = AnalysisStatus.COMPLETED.value
            row.model = settings.AI_MODEL
            row.completed_at = utcnow()
            doc.processing_status = ProcessingStatus.PROCESSED.value
        except (HTTPException, StorageError, Exception) as exc:  # noqa: BLE001 - every failure is recorded on the row
            detail = exc.detail if isinstance(exc, HTTPException) else (
                "The document file is missing." if isinstance(exc, StorageError) else "Unexpected error while analysing.")
            if not isinstance(exc, HTTPException):
                logger.exception("Analysis %s failed", analysis_id)
            row.status = AnalysisStatus.FAILED.value
            row.error = str(detail)[:500]
            doc.processing_status = ProcessingStatus.FAILED.value
        db.commit()
