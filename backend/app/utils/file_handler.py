"""Upload validation: extension, declared MIME type, magic bytes and size."""
from dataclasses import dataclass
from pathlib import PurePath

from fastapi import HTTPException, UploadFile, status

from app.config import settings

ALLOWED_EXTENSIONS: dict[str, str] = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}

# File signatures used to verify actual content regardless of what the browser claims.
MAGIC_BYTES: dict[str, tuple[bytes, ...]] = {
    "application/pdf": (b"%PDF-",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}

CHUNK_SIZE = 1024 * 1024


@dataclass
class ValidatedFile:
    content: bytes
    mime_type: str
    extension: str
    display_name: str


def sanitize_display_name(filename: str | None) -> str:
    """Keep only the base name for display; it is never used as a filesystem path."""
    name = PurePath((filename or "document").replace("\\", "/")).name
    name = "".join(ch for ch in name if ch.isprintable() and ch not in '<>:"|?*').strip()
    return (name or "document")[:255]


async def read_and_validate_upload(file: UploadFile) -> ValidatedFile:
    display_name = sanitize_display_name(file.filename)
    extension = PurePath(display_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Allowed: PDF, JPG, JPEG, PNG",
        )
    expected_mime = ALLOWED_EXTENSIONS[extension]
    declared = (file.content_type or "").lower()
    if declared and declared not in (expected_mime, "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content type does not match its extension",
        )

    max_bytes = settings.max_upload_bytes
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(CHUNK_SIZE):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB} MB",
            )
        chunks.append(chunk)
    content = b"".join(chunks)

    if total == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")
    if not any(content.startswith(sig) for sig in MAGIC_BYTES[expected_mime]):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File content does not match a valid PDF, JPEG or PNG",
        )
    return ValidatedFile(content=content, mime_type=expected_mime, extension=extension, display_name=display_name)
