import uuid
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.ai import AnalysisOut, AnalysisRequest, AnalysisSummary
from app.schemas.document import DocumentOut
from app.services import analysis_service, document_service
from app.services.audit_service import log_event
from app.services.storage_service import StorageError, get_storage
from app.utils.validators import validate_language

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/{document_id}", response_model=DocumentOut)
def get_document_metadata(
    document_id: uuid.UUID, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    doc = document_service.get_authorized_document(db, user, document_id)
    log_event(db, action="DOCUMENT_VIEW", resource_type="DOCUMENT", actor=user,
              resource_id=doc.id, patient_id=doc.patient_id, request=request)
    return doc


@router.get("/{document_id}/download")
def download_document(
    document_id: uuid.UUID, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    doc = document_service.get_authorized_document(db, user, document_id)
    try:
        path = get_storage().open_path(doc.storage_key)
    except StorageError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document file is unavailable")
    log_event(db, action="DOCUMENT_DOWNLOAD", resource_type="DOCUMENT", actor=user,
              resource_id=doc.id, patient_id=doc.patient_id, request=request)
    safe_name = quote(doc.document_name)
    return FileResponse(
        path,
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post("/{document_id}/analysis", response_model=AnalysisOut, status_code=status.HTTP_202_ACCEPTED)
def analyze_document(
    document_id: uuid.UUID,
    data: AnalysisRequest,
    background: BackgroundTasks,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start (or reuse) the AI reading of a document in one language. Poll GET .../analysis until COMPLETED."""
    doc = document_service.get_authorized_document(db, user, document_id)
    row, needs_run = analysis_service.request_analysis(db, doc, data.language, user, data.force)
    if needs_run:
        log_event(db, action="AI_DOCUMENT_ANALYSIS", resource_type="DOCUMENT", actor=user, resource_id=doc.id,
                  patient_id=doc.patient_id, request=request, details=data.language)
        background.add_task(analysis_service.run_analysis, row.id)
    return AnalysisOut.from_row(row)


@router.get("/{document_id}/analyses", response_model=list[AnalysisSummary])
def list_document_analyses(
    document_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Every saved AI explanation/translation of this document (one per language), most recent first."""
    doc = document_service.get_authorized_document(db, user, document_id)
    return sorted(doc.analyses, key=lambda a: a.completed_at or a.updated_at, reverse=True)


@router.get("/{document_id}/analysis", response_model=AnalysisOut)
def get_document_analysis(
    document_id: uuid.UUID,
    language: str = Query(..., max_length=10),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = document_service.get_authorized_document(db, user, document_id)
    try:
        language = validate_language(language)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    row = analysis_service.get_analysis(db, doc.id, language)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No analysis in this language yet")
    return AnalysisOut.from_row(row)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    doc = document_service.get_authorized_document(db, user, document_id)
    patient_id, doc_id = doc.patient_id, doc.id
    document_service.delete_document(db, user, doc)
    log_event(db, action="DOCUMENT_DELETE", resource_type="DOCUMENT", actor=user,
              resource_id=doc_id, patient_id=patient_id, request=request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
