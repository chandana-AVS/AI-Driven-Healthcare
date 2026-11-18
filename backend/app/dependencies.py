"""Authentication / authorization dependencies shared by routers."""
import uuid
from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import HealthcareWorkerProfile, PatientProfile, User
from app.models.enums import UserRole, VerificationStatus
from app.utils.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False, description="Paste the access_token returned by /auth/login")

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _CREDENTIALS_EXC
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise _CREDENTIALS_EXC

    user = db.get(User, user_id)
    if user is None:
        raise _CREDENTIALS_EXC
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
    return user


def require_roles(*roles: UserRole) -> Callable[..., User]:
    allowed = {r.value for r in roles}

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker


def require_admin(user: User = Depends(require_roles(UserRole.ADMIN))) -> User:
    """Admin role AND approved. Self-registered admins stay blocked until a verified admin approves them."""
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your administrator account is awaiting approval by an existing administrator",
        )
    return user


def get_current_patient(
    user: User = Depends(require_roles(UserRole.PATIENT)), db: Session = Depends(get_db)
) -> PatientProfile:
    profile = db.query(PatientProfile).filter(PatientProfile.user_id == user.id).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient profile not found")
    return profile


def get_current_worker(
    user: User = Depends(require_roles(UserRole.HEALTHCARE_WORKER)), db: Session = Depends(get_db)
) -> HealthcareWorkerProfile:
    profile = db.query(HealthcareWorkerProfile).filter(HealthcareWorkerProfile.user_id == user.id).first()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Healthcare worker profile not found")
    return profile


def get_verified_worker(worker: HealthcareWorkerProfile = Depends(get_current_worker)) -> HealthcareWorkerProfile:
    if worker.verification_status != VerificationStatus.VERIFIED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your healthcare worker account has not been verified by an administrator yet",
        )
    return worker
