"""Audit logging for sensitive access and modifications. Stores identifiers only, never medical content."""
import logging
import uuid

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog, User

logger = logging.getLogger("audit")


def log_event(
    db: Session,
    *,
    action: str,
    resource_type: str,
    actor: User | None = None,
    resource_id: uuid.UUID | str | None = None,
    patient_id: uuid.UUID | None = None,
    request: Request | None = None,
    details: str | None = None,
    commit: bool = True,
) -> None:
    entry = AuditLog(
        actor_id=actor.id if actor else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        patient_id=patient_id,
        ip_address=request.client.host if request and request.client else None,
        details=details,
    )
    db.add(entry)
    if commit:
        db.commit()
    logger.info("audit action=%s resource=%s id=%s actor=%s", action, resource_type, resource_id, entry.actor_id)
