import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ContentCategory, ContentStatus, ContentType
from app.utils.validators import validate_language


class ContentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=255)
    body: str = Field(min_length=10, max_length=50000)
    category: ContentCategory
    content_type: ContentType = ContentType.ARTICLE
    language_code: str = "en"
    status: ContentStatus = ContentStatus.DRAFT

    @field_validator("language_code")
    @classmethod
    def _lang(cls, v):
        return validate_language(v)


class ContentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    body: Optional[str] = Field(default=None, min_length=10, max_length=50000)
    category: Optional[ContentCategory] = None
    content_type: Optional[ContentType] = None
    language_code: Optional[str] = None
    status: Optional[ContentStatus] = None

    @field_validator("language_code")
    @classmethod
    def _lang(cls, v):
        return validate_language(v) if v is not None else v


class ContentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    body: str
    category: str
    content_type: str
    language_code: str
    status: str
    translation_group_id: Optional[uuid.UUID] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
