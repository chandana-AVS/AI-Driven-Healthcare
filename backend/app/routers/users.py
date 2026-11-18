from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.models.enums import LANGUAGE_NAMES
from app.schemas.user import LanguageInfo, LanguageUpdate, UserPublic, UserUpdate
from app.services import user_service

router = APIRouter(tags=["Users"])


@router.get("/languages", response_model=list[LanguageInfo])
def supported_languages():
    """Supported language codes. Shared with future translation and voice modules."""
    return [LanguageInfo(code=code, **info) for code, info in LANGUAGE_NAMES.items()]


@router.get("/users/me", response_model=UserPublic)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.patch("/users/me", response_model=UserPublic)
def update_me(data: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service.update_user(db, user, data)


@router.patch("/users/me/language", response_model=UserPublic)
def update_my_language(data: LanguageUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_service.update_language(db, user, data.preferred_language)
