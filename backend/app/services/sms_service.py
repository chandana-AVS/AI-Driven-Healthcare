"""Pluggable SMS sender. Add another provider (MSG91, Fast2SMS, AWS SNS...) by subclassing SMSProvider."""
import logging
from collections import deque
from functools import lru_cache

import httpx

from app.config import settings

logger = logging.getLogger("sms")


class SMSError(Exception):
    """Raised when an SMS could not be handed to the provider."""


def to_e164(phone: str) -> str:
    """Stored numbers may lack a country code (e.g. 9876543210); providers need +<country><number>."""
    if phone.startswith("+"):
        return phone
    return f"{settings.SMS_DEFAULT_COUNTRY_CODE}{phone.lstrip('0')}"


class SMSProvider:
    def send(self, to: str, body: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class ConsoleSMSProvider(SMSProvider):
    """Development only: writes the message to the backend log instead of sending it."""

    def __init__(self) -> None:
        self.outbox: deque[tuple[str, str]] = deque(maxlen=100)  # read by the tests

    def send(self, to: str, body: str) -> None:
        self.outbox.append((to, body))
        logger.warning("[DEV SMS] to %s: %s", to, body)


class StaticSMSProvider(SMSProvider):
    """Temporary: nothing is sent; the user types the fixed OTP_STATIC_CODE."""

    def send(self, to: str, body: str) -> None:
        logger.info("[STATIC OTP] no SMS sent to %s; the code is %s", to, settings.OTP_STATIC_CODE)


class TwilioSMSProvider(SMSProvider):
    def __init__(self, account_sid: str, auth_token: str, from_number: str) -> None:
        if not (account_sid and auth_token and from_number):
            raise RuntimeError("SMS_PROVIDER=twilio needs TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER")
        self.account_sid, self.auth_token, self.from_number = account_sid, auth_token, from_number

    def send(self, to: str, body: str) -> None:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        try:
            res = httpx.post(url, data={"To": to, "From": self.from_number, "Body": body},
                             auth=(self.account_sid, self.auth_token), timeout=10)
        except httpx.HTTPError as exc:
            raise SMSError(f"Twilio request failed: {exc.__class__.__name__}") from exc
        if res.status_code >= 300:
            # Log Twilio's error text, never the message body (it contains the code).
            try:
                reason = res.json().get("message", "")
            except ValueError:
                reason = ""
            logger.error("Twilio rejected SMS (HTTP %s): %s", res.status_code, reason)
            raise SMSError(f"Twilio returned HTTP {res.status_code}")


@lru_cache
def get_sms_provider() -> SMSProvider:
    name = settings.SMS_PROVIDER.strip().lower()
    if name == "twilio":
        return TwilioSMSProvider(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_FROM_NUMBER)
    if name == "console":
        return ConsoleSMSProvider()
    if name == "static":
        return StaticSMSProvider()
    raise RuntimeError(f"Unknown SMS_PROVIDER '{settings.SMS_PROVIDER}' (use 'static', 'console' or 'twilio')")


def send_sms(phone: str, body: str) -> None:
    get_sms_provider().send(to_e164(phone), body)
