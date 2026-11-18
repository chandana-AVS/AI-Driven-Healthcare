"""Reusable field validators."""
import re

from app.models.enums import LanguageCode

PHONE_RE = re.compile(r"^\+?[0-9]{7,15}$")

SUPPORTED_LANGUAGES = {lang.value for lang in LanguageCode}


def normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = re.sub(r"[\s\-()]", "", value)
    if cleaned == "":
        return None
    if not PHONE_RE.match(cleaned):
        raise ValueError("Phone number must contain 7-15 digits, optionally starting with +")
    return cleaned


def validate_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if len(value) > 128:
        raise ValueError("Password must be at most 128 characters long")
    if not re.search(r"[A-Za-z]", value) or not re.search(r"[0-9]", value):
        raise ValueError("Password must contain at least one letter and one number")
    return value


def validate_language(value: str) -> str:
    value = value.strip().lower()
    if value not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language. Supported: {', '.join(sorted(SUPPORTED_LANGUAGES))}")
    return value
