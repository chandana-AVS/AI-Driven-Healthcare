import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import HealthcareContent
from app.models.enums import ContentCategory, ContentStatus, ContentType
from app.schemas.healthcare_content import ContentOut
from app.utils.validators import validate_language

router = APIRouter(prefix="/content", tags=["Healthcare Content"])


@router.get("/categories", response_model=list[str])
def content_categories():
    return [c.value for c in ContentCategory]


@router.get("/types", response_model=list[str])
def content_types():
    return [t.value for t in ContentType]


@router.get("", response_model=list[ContentOut])
def list_published_content(
    category: Optional[ContentCategory] = Query(None),
    content_type: Optional[ContentType] = Query(None),
    language: Optional[str] = Query(None, max_length=10),
    search: Optional[str] = Query(None, max_length=100),
    db: Session = Depends(get_db),
):
    """Public list of PUBLISHED educational content."""
    query = db.query(HealthcareContent).filter(HealthcareContent.status == ContentStatus.PUBLISHED.value)
    if category:
        query = query.filter(HealthcareContent.category == category.value)
    if content_type:
        query = query.filter(HealthcareContent.content_type == content_type.value)
    if language:
        try:
            query = query.filter(HealthcareContent.language_code == validate_language(language))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(HealthcareContent.title.ilike(term), HealthcareContent.body.ilike(term)))
    return query.order_by(HealthcareContent.created_at.desc()).all()


@router.get("/{content_id}", response_model=ContentOut)
def get_published_content(content_id: uuid.UUID, db: Session = Depends(get_db)):
    item = db.get(HealthcareContent, content_id)
    if item is None or item.status != ContentStatus.PUBLISHED.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    return item


@router.get("/{content_id}/translations", response_model=list[ContentOut])
def list_translations(content_id: uuid.UUID, db: Session = Depends(get_db)):
    """Published versions of the same item in every language."""
    item = db.get(HealthcareContent, content_id)
    if item is None or item.status != ContentStatus.PUBLISHED.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content not found")
    if item.translation_group_id is None:
        return [item]
    return (db.query(HealthcareContent)
            .filter(HealthcareContent.translation_group_id == item.translation_group_id,
                    HealthcareContent.status == ContentStatus.PUBLISHED.value)
            .order_by(HealthcareContent.language_code).all())
