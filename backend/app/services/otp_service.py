"""SMS one-time codes for phone-number verification."""
import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models import PhoneOTP, User
from app.models.mixins import utcnow
from app.services.sms_service import SMSError, send_sms

logger = logging.getLogger("otp")

INVALID_CODE = "Invalid or expired verification code"
TOO_MANY = "Too many wrong attempts. Please request a new code."


def static_mode() -> bool:
    """Temporary mode: every code is OTP_STATIC_CODE and no SMS is sent."""
    return settings.SMS_PROVIDER.strip().lower() == "static"


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)  # SQLite returns naive datetimes


def _hash(user: User, phone: str, code: str) -> str:
    msg = f"{user.id}:{phone}:{code}".encode()
    return hmac.new(settings.JWT_SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()


def _latest(db: Session, user: User) -> PhoneOTP | None:
    return db.query(PhoneOTP).filter(PhoneOTP.user_id == user.id).order_by(PhoneOTP.created_at.desc()).first()


def issue_otp(db: Session, user: User) -> None:
    """Create a new code for the user's current phone number and send it by SMS.

    Raises 429 if the resend cooldown or hourly limit is hit, 503 if the SMS provider fails.
    """
    if not user.phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This account has no phone number")
    now = utcnow()
    last = _latest(db, user)
    if last is not None and last.phone == user.phone:  # a newly changed number gets its code straight away
        wait = settings.OTP_RESEND_COOLDOWN_SECONDS - int((now - _aware(last.created_at)).total_seconds())
        if wait > 0:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                                detail=f"Please wait {wait} seconds before requesting another code",
                                headers={"Retry-After": str(wait)})
    sent_last_hour = (db.query(PhoneOTP)
                      .filter(PhoneOTP.user_id == user.id, PhoneOTP.created_at >= now - timedelta(hours=1)).count())
    if sent_last_hour >= settings.OTP_MAX_PER_HOUR:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail="Too many codes requested. Please try again in an hour.")

    # Only the newest code is valid: expire any outstanding ones.
    db.query(PhoneOTP).filter(PhoneOTP.user_id == user.id, PhoneOTP.consumed_at.is_(None)).update(
        {PhoneOTP.expires_at: now}, synchronize_session=False)

    code = (settings.OTP_STATIC_CODE if static_mode()
            else f"{secrets.randbelow(10 ** settings.OTP_LENGTH):0{settings.OTP_LENGTH}d}")
    db.add(PhoneOTP(user_id=user.id, phone=user.phone, code_hash=_hash(user, user.phone, code),
                    expires_at=now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES), attempts=0))
    db.flush()
    try:
        send_sms(user.phone, f"{code} is your Rural Health Assistant verification code. "
                             f"It expires in {settings.OTP_EXPIRE_MINUTES} minutes. Do not share it with anyone.")
    except SMSError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Could not send the SMS right now. Please try again shortly.")
    db.commit()


def try_issue_otp(db: Session, user: User) -> bool:
    """Best-effort send used after registration, login or a phone change; never fails the calling request."""
    try:
        issue_otp(db, user)
        return True
    except HTTPException as exc:
        logger.info("OTP not sent for user %s: %s", user.id, exc.detail)
        return False


def verify_otp(db: Session, user: User | None, code: str) -> User:
    if user is None or not user.phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_CODE)
    if user.phone_verified:
        return user
    otp = _latest(db, user)
    if static_mode() and hmac.compare_digest(code, settings.OTP_STATIC_CODE):
        # Accepted even if no code was issued after the switch to static mode (e.g. accounts created earlier).
        if otp is not None and otp.consumed_at is None:
            otp.consumed_at = utcnow()
        user.phone_verified = True
        db.commit()
        db.refresh(user)
        return user
    if otp is None or otp.consumed_at is not None or otp.phone != user.phone or _aware(otp.expires_at) <= utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_CODE)
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=TOO_MANY)
    if not hmac.compare_digest(otp.code_hash, _hash(user, user.phone, code)):
        otp.attempts += 1
        db.commit()
        left = settings.OTP_MAX_ATTEMPTS - otp.attempts
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"{INVALID_CODE}. {left} attempt{'s' if left != 1 else ''} left." if left else TOO_MANY)
    otp.consumed_at = utcnow()
    user.phone_verified = True
    db.commit()
    db.refresh(user)
    return user
