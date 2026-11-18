"""Multilingual knowledge base: search published content and create AI translations of articles."""
import re
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import HealthcareContent, User
from app.models.enums import ContentStatus
from app.services import ai_service

STOPWORDS = {"have", "with", "from", "that", "this", "since", "days", "after", "about", "feel", "feeling", "very",
             "also", "some", "when", "what", "there", "been", "and", "the", "for", "my", "since", "having"}


def keywords(text: str, limit: int = 8) -> list[str]:
    words = [w.lower() for w in re.findall(r"\w+", text, flags=re.UNICODE) if len(w) >= 4]
    out: list[str] = []
    for w in words:
        if w not in STOPWORDS and w not in out:
            out.append(w)
    return out[:limit]


def find_related(db: Session, text: str, language: str, limit: int = 4) -> list[HealthcareContent]:
    """Published items in the user's language (or English) whose title or body mentions a keyword."""
    terms = keywords(text)
    if not terms:
        return []
    conditions = [c for t in terms for c in (HealthcareContent.title.ilike(f"%{t}%"), HealthcareContent.body.ilike(f"%{t}%"))]
    rows = (db.query(HealthcareContent)
            .filter(HealthcareContent.status == ContentStatus.PUBLISHED.value,
                    HealthcareContent.language_code.in_({language, "en"}),
                    or_(*conditions))
            .limit(40).all())

    def score(item: HealthcareContent) -> tuple:
        hay_title, hay_body = item.title.lower(), item.body.lower()
        hits = sum(3 * (t in hay_title) + (t in hay_body) for t in terms)
        return (hits, item.language_code == language)

    return sorted(rows, key=score, reverse=True)[:limit]


def translate_item(db: Session, item: HealthcareContent, languages: list[str], admin: User) -> list[HealthcareContent]:
    """Create DRAFT translations of `item` in each requested language that does not already have one."""
    group = item.translation_group_id or item.id
    if item.translation_group_id is None:
        item.translation_group_id = group
    existing = {row.language_code for row in db.query(HealthcareContent)
                .filter(HealthcareContent.translation_group_id == group)}
    existing.add(item.language_code)
    targets = [lang for lang in languages if lang not in existing]
    if not targets:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Translations already exist for every selected language")
    ai_service.enforce_daily_limit(db, admin)

    with ThreadPoolExecutor(max_workers=min(4, len(targets))) as pool:  # languages translated in parallel
        results = list(pool.map(lambda lang: ai_service.translate_content(item.title, item.body, lang), targets))

    created = []
    for lang, tr in zip(targets, results):
        copy = HealthcareContent(
            id=uuid.uuid4(), title=tr.title[:255], body=tr.body, category=item.category, content_type=item.content_type,
            language_code=lang, status=ContentStatus.DRAFT.value, created_by=admin.id, translation_group_id=group,
        )
        db.add(copy)
        created.append(copy)
    db.commit()
    for c in created:
        db.refresh(c)
    return created
