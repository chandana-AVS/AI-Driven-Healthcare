from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.auth import (
    AdminRegister,
    HealthcareWorkerRegister,
    LoginRequest,
    PatientRegister,
    PhoneOTPRequest,
    PhoneVerifyRequest,
    TokenResponse,
)
from app.schemas.user import UserPublic, UserSummary
from app.services import auth_service, otp_service
from app.services.audit_service import log_event
from app.utils.security import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _after_register(db: Session, user, request: Request, action: str):
    log_event(db, action=action, resource_type="USER", actor=user, resource_id=user.id, request=request)
    otp_service.try_issue_otp(db, user)  # SMS code; if sending fails the user can press "Resend"
    db.refresh(user)
    return user


@router.post("/register/patient", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register_patient(data: PatientRegister, request: Request, db: Session = Depends(get_db)):
    """Creates the account and sends an SMS code. Login is blocked until `/auth/phone/verify` succeeds."""
    return _after_register(db, auth_service.register_patient(db, data), request, "REGISTER")


@router.post("/register/healthcare-worker", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register_healthcare_worker(data: HealthcareWorkerRegister, request: Request, db: Session = Depends(get_db)):
    return _after_register(db, auth_service.register_healthcare_worker(db, data), request, "REGISTER")


@router.post("/register/admin", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register_admin(data: AdminRegister, request: Request, db: Session = Depends(get_db)):
    """Creates a PENDING admin. It has no admin permissions until an existing verified admin approves it."""
    return _after_register(db, auth_service.register_admin(db, data), request, "REGISTER_ADMIN")


@router.post("/phone/send-otp", status_code=status.HTTP_202_ACCEPTED)
def send_phone_otp(data: PhoneOTPRequest, db: Session = Depends(get_db)):
    """(Re)send the SMS verification code. The reply is the same whether or not the account exists."""
    user = auth_service.find_user_by_identifier(db, data.identifier)
    if user is not None and user.is_active and user.phone and not user.phone_verified:
        otp_service.issue_otp(db, user)  # may raise 429 (cooldown / hourly limit) or 503 (SMS provider down)
    return {
        "detail": "If this account needs verification, a code has been sent to its phone number.",
        "resend_after": settings.OTP_RESEND_COOLDOWN_SECONDS,
        "expires_in": settings.OTP_EXPIRE_MINUTES * 60,
    }


@router.post("/phone/verify")
def verify_phone(data: PhoneVerifyRequest, request: Request, db: Session = Depends(get_db)):
    user = auth_service.find_user_by_identifier(db, data.identifier)
    already = bool(user and user.phone_verified)
    user = otp_service.verify_otp(db, user, data.code)
    if not already:
        log_event(db, action="PHONE_VERIFIED", resource_type="USER", actor=user, resource_id=user.id, request=request)
    return {"detail": "Phone number verified", "phone_verified": True}


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    try:
        user = auth_service.authenticate(db, data.identifier, data.password)
    except Exception:
        log_event(db, action="LOGIN_FAILED", resource_type="AUTH", request=request)
        raise
    token = create_access_token(str(user.id), user.role)
    log_event(db, action="LOGIN", resource_type="AUTH", actor=user, resource_id=user.id, request=request)
    return TokenResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserSummary.model_validate(user),
    )
