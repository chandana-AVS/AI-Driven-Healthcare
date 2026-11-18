"""Milestone 2 AI endpoints: translation, simplification, entity extraction and symptom guidance."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas.ai import (
    AIStatus,
    ExtractionResult,
    ExtractRequest,
    RelatedContent,
    SimplificationResult,
    SimplifyRequest,
    SymptomRequest,
    SymptomResponse,
    TranslateRequest,
    TranslationResult,
)
from app.services import ai_service, knowledge_service
from app.services.audit_service import log_event

router = APIRouter(prefix="/ai", tags=["AI Language Engine"])

DISCLAIMER = ("This is general health information, not a diagnosis or treatment plan. Please consult a doctor or "
              "health worker. In an emergency call 108 or go to the nearest hospital.")


def _guard(db: Session, user: User) -> None:
    ai_service.enforce_daily_limit(db, user)


@router.get("/status", response_model=AIStatus)
def ai_status(_: User = Depends(get_current_user)):
    return AIStatus(enabled=ai_service.ai_enabled(), model=settings.AI_MODEL, daily_limit=settings.AI_DAILY_LIMIT_PER_USER)


@router.post("/translate", response_model=TranslationResult)
def translate(data: TranslateRequest, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Translate a prescription, discharge summary or instructions into an Indian language, with a simple version."""
    _guard(db, user)
    result = ai_service.translate_text(data.text, data.target_language, data.text_type)
    log_event(db, action="AI_TRANSLATE", resource_type="AI", actor=user, request=request,
              details=f"{data.text_type.value}->{data.target_language}")
    return result


@router.post("/simplify", response_model=SimplificationResult)
def simplify(data: SimplifyRequest, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Rewrite medical text in simple words with practical guidance and a glossary."""
    _guard(db, user)
    result = ai_service.simplify_text(data.text, data.language)
    log_event(db, action="AI_SIMPLIFY", resource_type="AI", actor=user, request=request, details=data.language)
    return result


@router.post("/extract", response_model=ExtractionResult)
def extract(data: ExtractRequest, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Find diseases, medicines, tests and treatment instructions in medical text."""
    _guard(db, user)
    result = ai_service.extract_entities(data.text, data.language)
    log_event(db, action="AI_EXTRACT", resource_type="AI", actor=user, request=request, details=data.language)
    return result


@router.post("/symptoms", response_model=SymptomResponse)
def symptoms(data: SymptomRequest, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Symptom awareness: urgency, possible causes, self-care, prevention, plus related knowledge-base articles."""
    _guard(db, user)
    related = knowledge_service.find_related(db, data.symptoms, data.language)
    guidance = ai_service.symptom_guidance(
        data.symptoms, data.language, data.age, data.gender, data.duration,
        knowledge=[(item.title, item.body) for item in related],
    )
    log_event(db, action="AI_SYMPTOMS", resource_type="AI", actor=user, request=request,
              details=f"{data.language} urgency={guidance.urgency}")
    return SymptomResponse(
        **guidance.model_dump(),
        related_content=[RelatedContent(id=i.id, title=i.title, content_type=i.content_type, language_code=i.language_code)
                         for i in related],
        disclaimer=DISCLAIMER,
    )
