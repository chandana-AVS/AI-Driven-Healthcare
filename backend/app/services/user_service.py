from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.user import UserUpdate
from app.services.auth_service import ensure_unique_contact
from app.services.otp_service import try_issue_otp


def update_user(db: Session, user: User, data: UserUpdate) -> User:
    changes = data.model_dump(exclude_unset=True)
    if "email" in changes and changes["email"]:
        changes["email"] = changes["email"].lower()

    new_phone = changes.get("phone", user.phone)
    new_email = changes.get("email", user.email)
    if not new_phone and (user.phone or "phone" in changes or not new_email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A phone number is required on the account",
        )
    if "full_name" in changes and not changes["full_name"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Full name cannot be empty")

    ensure_unique_contact(
        db,
        changes.get("email") if "email" in changes else None,
        changes.get("phone") if "phone" in changes else None,
        exclude_user_id=user.id,
    )
    phone_changed = "phone" in changes and changes["phone"] != user.phone
    for field, value in changes.items():
        setattr(user, field, value)
    if phone_changed:
        user.phone_verified = False  # the new number must be verified by SMS before the next login
    db.commit()
    if phone_changed:
        try_issue_otp(db, user)
    db.refresh(user)
    return user


def update_language(db: Session, user: User, language: str) -> User:
    user.preferred_language = language
    db.commit()
    db.refresh(user)
    return user
